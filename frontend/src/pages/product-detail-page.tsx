import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { useEffect, useRef, useState } from 'react';
import {
  Sparkles,
  ImagePlus,
  Upload,
  ArrowLeft,
  Trash2,
  Star,
  Package,
  Copy,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { EmptyState } from '@/components/empty-state';
import { AttributesSection } from '@/components/attributes-section';
import axios from 'axios';
import { apiClient } from '@/lib/api-client';
import { resolveImageUrl } from '@/lib/utils';
import { showSuccess, showError } from '@/lib/toast';

function extractApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { error?: string; details?: Array<{ msg?: string }> }
      | undefined;
    if (data?.details?.length) {
      return data.details.map((d) => d.msg).filter(Boolean).join('; ');
    }
    if (data?.error) return data.error;
  }
  return 'Сталася помилка';
}
import { useAuthStore } from '@/stores/auth-store';
import type { Product, Category } from '@/types/api';

function formatPrice(price: number | string | null, currency: string | null): string {
  if (price === null || price === undefined) return '—';
  const num = typeof price === 'string' ? Number(price) : price;
  if (Number.isNaN(num)) return '—';
  const formatted = new Intl.NumberFormat('uk-UA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
  return `${formatted} ${currency === 'UAH' ? '₴' : (currency ?? '')}`;
}

interface EnrichedFormData {
  custom_name: string;
  custom_brand: string;
  custom_country: string;
  custom_category_id: string;
  description: string;
  seo_title: string;
  seo_description: string;
}

const RESETTABLE_FIELDS = [
  'custom_name',
  'custom_brand',
  'custom_country',
  'custom_category_id',
  'description',
  'seo_title',
  'seo_description',
] as const;

interface ProductExtended {
  buf_country: string | null;
  custom_country: string | null;
  uktzed: string | null;
}

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuthStore();

  const canEdit = hasRole(['admin', 'operator']);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch categories for the select
  const { data: categoriesData } = useQuery({
    queryKey: ['categories-flat'],
    queryFn: async () => {
      const response = await apiClient.get<{ data: Category[] }>(
        '/api/categories?per_page=500',
      );
      return response.data.data;
    },
  });

  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: async () => {
      const response = await apiClient.get<Product>(`/api/products/${id}`);
      return response.data;
    },
    enabled: !!id,
  });

  const form = useForm<EnrichedFormData>({
    defaultValues: {
      custom_name: '',
      custom_brand: '',
      custom_country: '',
      custom_category_id: '',
      description: '',
      seo_title: '',
      seo_description: '',
    },
  });

  useEffect(() => {
    if (product) {
      form.reset({
        custom_name: product.custom_name ?? '',
        custom_brand: product.custom_brand ?? '',
        custom_country: (product as unknown as ProductExtended).custom_country ?? '',
        custom_category_id: product.category?.id ?? '',
        description: product.description ?? '',
        seo_title: product.seo_title ?? '',
        seo_description: product.seo_description ?? '',
      });
    }
  }, [product, form]);

  const updateMutation = useMutation({
    mutationFn: async (data: EnrichedFormData) => {
      const payload: Record<string, string | null> = {
        custom_name: data.custom_name || null,
        custom_brand: data.custom_brand || null,
        custom_country: data.custom_country || null,
        description: data.description || null,
        seo_title: data.seo_title || null,
        seo_description: data.seo_description || null,
      };
      // Only include category if user picked a different one (backend rejects null)
      if (data.custom_category_id && data.custom_category_id !== product?.category?.id) {
        payload.custom_category_id = data.custom_category_id;
      }
      const response = await apiClient.patch<Product>(`/api/products/${id}`, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', id] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      showSuccess(t('common.save') + ' ✓');
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const resetFieldMutation = useMutation({
    mutationFn: async (field: string) => {
      const response = await apiClient.post<Product>(
        `/api/products/${id}/reset-field`,
        { field },
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', id] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      showSuccess(t('product.enriched.reset') + ' ✓');
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null);

  const uploadImagesMutation = useMutation({
    mutationFn: async (files: File[]) => {
      setUploadProgress({ done: 0, total: files.length });
      let ok = 0;
      const failures: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        try {
          const formData = new FormData();
          formData.append('file', f);
          await apiClient.post(`/api/products/${id}/images`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          ok += 1;
        } catch (err) {
          failures.push(`${f.name}: ${extractApiError(err)}`);
        }
        setUploadProgress({ done: i + 1, total: files.length });
      }
      return { ok, failures };
    },
    onSuccess: ({ ok, failures }) => {
      queryClient.invalidateQueries({ queryKey: ['product', id] });
      setUploadProgress(null);
      if (failures.length === 0) {
        showSuccess(`Завантажено ${ok} зображень`);
      } else {
        showError(`Завантажено ${ok}, помилки: ${failures.join('; ')}`);
      }
    },
    onError: (err) => {
      setUploadProgress(null);
      showError(extractApiError(err));
    },
  });

  const deleteImageMutation = useMutation({
    mutationFn: async (imageId: string) => {
      await apiClient.delete(`/api/products/${id}/images/${imageId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', id] });
      showSuccess('Зображення видалено');
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const setPrimaryMutation = useMutation({
    mutationFn: async (imageId: string) => {
      await apiClient.patch(`/api/products/${id}/images/${imageId}`, {
        is_primary: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', id] });
      showSuccess('Головне зображення оновлено');
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const onSubmit = (data: EnrichedFormData) => {
    updateMutation.mutate(data);
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-10 w-96" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        {t('common.no_results')}
      </div>
    );
  }

  const ext = product as unknown as ProductExtended;
  const categoryWithBreadcrumb = product.category as (Category & { breadcrumb?: Category[] }) | null;
  const breadcrumb = categoryWithBreadcrumb?.breadcrumb ?? (categoryWithBreadcrumb ? [categoryWithBreadcrumb] : []);

  return (
    <div>
      {/* Nav row: back + breadcrumb */}
      <div className="mb-4 flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => navigate('/products')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink render={<Link to="/products" />}>
                {t('products.title')}
              </BreadcrumbLink>
            </BreadcrumbItem>
            {breadcrumb.map((cat) => (
              <span key={cat.id} className="contents">
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbLink render={<Link to={`/products?category_id=${cat.id}`} />}>
                    {cat.name}
                  </BreadcrumbLink>
                </BreadcrumbItem>
              </span>
            ))}
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage className="max-w-[280px] truncate">
                {product.name}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* Hero — name + code (left) + enrichment status badges (right) */}
      <Card className="mb-6">
        <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-bold leading-tight tracking-tight">
              {product.name}
            </h1>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(product.internal_code);
                showSuccess('Код скопійовано');
              }}
              className="group mt-2 inline-flex w-fit items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
              title="Клікни щоб скопіювати"
            >
              <span>Код:</span>
              <span className="font-mono font-semibold">{product.internal_code}</span>
              <Copy className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2 sm:justify-end">
            {product.enrichment_status === 'none' && (
              <Badge variant="destructive">{t('product.badges.enrichment_none')}</Badge>
            )}
            {product.enrichment_status === 'partial' && (
              <Badge variant="secondary">{t('product.badges.enrichment_partial')}</Badge>
            )}
            {product.enrichment_status === 'full' && (
              <Badge variant="default">{t('product.badges.enrichment_full')}</Badge>
            )}
            {product.has_pending_review && (
              <Badge variant="destructive">{t('product.badges.pending_review')}</Badge>
            )}
          </div>
        </div>
      </Card>

      {/* Tabs: 3 tabs */}
      <Tabs defaultValue="main" className="flex flex-col">
        <TabsList variant="line" className="mb-6">
          <TabsTrigger value="main">{t('product.tabs.main')}</TabsTrigger>
          <TabsTrigger value="images">{t('product.tabs.images')}</TabsTrigger>
        </TabsList>

        {/* Tab: Основне — Image+Stats above BUF | Збагачення | Характеристики */}
        <TabsContent value="main">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* LEFT column: Image+Stats card → BUF card */}
            <div className="space-y-6 lg:col-span-1">
              {/* Image + price/quantity/in-stock */}
              <Card>
                <CardContent className="grid grid-cols-2 gap-4 p-4">
                  <div className="aspect-square overflow-hidden rounded-lg bg-muted ring-1 ring-border">
                    {product.images[0] ? (
                      <img
                        src={resolveImageUrl(product.images[0].file_path)}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center">
                        <Package className="h-12 w-12 text-muted-foreground/40" />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col justify-center gap-2">
                    <div>
                      <p className="text-xs text-muted-foreground">Ціна</p>
                      <p className="text-xl font-bold leading-tight">
                        {formatPrice(product.buf_price, product.buf_currency)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Залишок</p>
                      <p className="text-sm">
                        <strong>{product.buf_quantity ?? 0}</strong> шт
                      </p>
                    </div>
                    <div>
                      <p className="mb-1 text-xs text-muted-foreground">Наявність</p>
                      {product.buf_in_stock ? (
                        <Badge variant="default">{t('product.badges.in_stock')}</Badge>
                      ) : (
                        <Badge variant="secondary">{t('product.badges.out_of_stock')}</Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* BUF — read-only original */}
              <Card className="bg-muted/30">
                <CardHeader>
                  <CardTitle className="text-base">{t('product.buf.title')}</CardTitle>
                </CardHeader>
              <CardContent>
                <dl className="space-y-1.5 text-sm">
                  {(
                    [
                      ['Назва', product.buf_name ?? '—', false],
                      ['Бренд', product.buf_brand ?? '—', false],
                      ['Країна', ext.buf_country ?? '—', false],
                      [
                        'Категорія',
                        product.buf_category ? (
                          <Link
                            to={`/products?category_id=${product.buf_category.id}`}
                            className="text-primary hover:underline"
                          >
                            {product.buf_category.name}
                          </Link>
                        ) : (
                          '—'
                        ),
                        false,
                      ],
                      ['Код', product.internal_code, true],
                      ['SKU', product.sku, true],
                      ['UKTZED', ext.uktzed ?? '—', true],
                      ['Кількість', product.buf_quantity ?? '—', false],
                      ['Ціна', formatPrice(product.buf_price, product.buf_currency), false],
                      ['Валюта', product.buf_currency ?? '—', false],
                      [
                        'В наявності',
                        product.buf_in_stock ? (
                          <Badge variant="default">{t('product.badges.in_stock')}</Badge>
                        ) : (
                          <Badge variant="secondary">{t('product.badges.out_of_stock')}</Badge>
                        ),
                        false,
                      ],
                    ] as Array<[string, React.ReactNode, boolean]>
                  ).map(([label, value, mono]) => (
                    <div
                      key={label}
                      className="flex items-start justify-between gap-3 border-b border-border/40 pb-1.5 last:border-0 last:pb-0"
                    >
                      <dt className="text-xs text-muted-foreground">{label}</dt>
                      <dd className={`text-right ${mono ? 'font-mono text-xs' : 'text-sm'}`}>
                        {value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
              </Card>
            </div>

            {/* Збагачення — editable form (or read-only for manager/viewer), wider 2/3 */}
            {canEdit ? (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="text-base">{t('product.enriched.title')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-3">
                    <div className="space-y-1.5">
                      <Label className="text-xs">{t('product.buf.name')}</Label>
                      <Input
                        placeholder={product.buf_name ?? t('product.enriched.name_placeholder')}
                        {...form.register('custom_name')}
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label className="text-xs">{t('product.buf.brand')}</Label>
                        <Input
                          placeholder={product.buf_brand ?? t('product.enriched.brand_placeholder')}
                          {...form.register('custom_brand')}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs">{t('product.buf.country')}</Label>
                        <Input
                          placeholder={t('product.enriched.country_placeholder')}
                          {...form.register('custom_country')}
                        />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">{t('product.info.category')}</Label>
                      <Controller
                        control={form.control}
                        name="custom_category_id"
                        render={({ field }) => {
                          const selectedCat = (categoriesData ?? []).find((c) => c.id === field.value);
                          return (
                            <Select value={field.value || ''} onValueChange={(val) => field.onChange(val ?? '')}>
                              <SelectTrigger>
                                <SelectValue>
                                  {selectedCat
                                    ? selectedCat.name
                                    : product.category?.name ?? t('product.enriched.category_placeholder')}
                                </SelectValue>
                              </SelectTrigger>
                              <SelectContent>
                                {(categoriesData ?? []).map((cat) => (
                                  <SelectItem key={cat.id} value={cat.id}>
                                    {cat.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          );
                        }}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">{t('product.enriched.description')}</Label>
                      <Textarea rows={4} {...form.register('description')} />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">{t('product.enriched.seo_title')}</Label>
                      <Input {...form.register('seo_title')} />
                    </div>
                    <div className="space-y-1.5">
                      <Label className="text-xs">{t('product.enriched.seo_description')}</Label>
                      <Textarea rows={3} {...form.register('seo_description')} />
                    </div>

                    <Separator className="my-2" />

                    <div className="flex items-center gap-2">
                      <Button type="submit" disabled={updateMutation.isPending}>
                        {t('product.enriched.save')}
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={<Button variant="ghost" type="button" />}
                        >
                          {t('product.enriched.reset')}
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          {RESETTABLE_FIELDS.map((field) => (
                            <DropdownMenuItem
                              key={field}
                              onClick={() => resetFieldMutation.mutate(field)}
                            >
                              {t('product.enriched.reset_field')} — {field}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </form>
                </CardContent>
              </Card>
            ) : (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="text-base">{t('product.enriched.title')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.name')}</dt>
                      <dd className="text-sm">{product.custom_name || product.buf_name || '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.brand')}</dt>
                      <dd className="text-sm">{product.custom_brand || product.buf_brand || '—'}</dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="text-xs text-muted-foreground">{t('product.enriched.description')}</dt>
                      <dd className="text-sm">{product.description || '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.enriched.seo_title')}</dt>
                      <dd className="text-sm">{product.seo_title || '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.enriched.seo_description')}</dt>
                      <dd className="text-sm">{product.seo_description || '—'}</dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Attributes — full width */}
          <Card className="mt-6">
            <CardContent className="pt-6">
              <AttributesSection productId={id!} canEdit={canEdit} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab: Зображення */}
        <TabsContent value="images">
          <div>
            {product.images.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {product.images.map((img) => (
                  <div
                    key={img.id}
                    className="group relative overflow-hidden rounded-lg border bg-muted"
                  >
                    <img
                      src={resolveImageUrl(img.file_path)}
                      alt=""
                      className="aspect-square w-full object-cover"
                    />
                    {img.is_primary && (
                      <Badge className="absolute left-2 top-2" variant="default">
                        {t('product.images.primary')}
                      </Badge>
                    )}
                    {canEdit && (
                      <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                        {!img.is_primary && (
                          <Button
                            size="icon-sm"
                            variant="secondary"
                            title="Зробити головним"
                            onClick={() => setPrimaryMutation.mutate(img.id)}
                          >
                            <Star className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        <Button
                          size="icon-sm"
                          variant="destructive"
                          title="Видалити"
                          onClick={() => deleteImageMutation.mutate(img.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState icon={ImagePlus} title={t('product.images.empty')} />
            )}
            {canEdit && (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    if (files.length) uploadImagesMutation.mutate(files);
                    e.target.value = '';
                  }}
                />
                <Button
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadImagesMutation.isPending}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {t('product.images.upload')}
                </Button>
                {uploadProgress && (
                  <span className="text-sm text-muted-foreground">
                    Завантажую {uploadProgress.done} / {uploadProgress.total}…
                  </span>
                )}
                <Button variant="outline" disabled title="v1.2+">
                  <Sparkles className="mr-2 h-4 w-4" />
                  {t('product.images.generate_ai')}
                </Button>
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab: AI */}
      </Tabs>
    </div>
  );
}
