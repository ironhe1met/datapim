import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { useEffect } from 'react';
import {
  Sparkles,
  ImagePlus,
  Upload,
  ArrowLeft,
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
import { apiClient } from '@/lib/api-client';
import { showSuccess } from '@/lib/toast';
import { useAuthStore } from '@/stores/auth-store';
import type { Product, Category } from '@/types/api';

function formatPrice(price: number | null, currency: string | null): string {
  if (price === null) return '—';
  const formatted = new Intl.NumberFormat('uk-UA', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(price);
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

  // Fetch categories for the select
  const { data: categoriesData } = useQuery({
    queryKey: ['categories-flat'],
    queryFn: async () => {
      const response = await apiClient.get<Category[]>('/api/categories');
      return response.data;
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
        custom_category_id: '',
        description: product.description ?? '',
        seo_title: product.seo_title ?? '',
        seo_description: product.seo_description ?? '',
      });
    }
  }, [product, form]);

  const updateMutation = useMutation({
    mutationFn: async (data: EnrichedFormData) => {
      const response = await apiClient.patch<Product>(`/api/products/${id}`, {
        custom_name: data.custom_name || null,
        custom_brand: data.custom_brand || null,
        custom_country: data.custom_country || null,
        custom_category_id: data.custom_category_id || null,
        description: data.description || null,
        seo_title: data.seo_title || null,
        seo_description: data.seo_description || null,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', id] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      showSuccess(t('common.save') + ' ✓');
    },
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
      {/* Breadcrumb */}
      <Breadcrumb className="mb-4">
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
            <BreadcrumbPage>{product.name}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="icon-sm" onClick={() => navigate('/products')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">{product.name}</h1>
        {product.buf_in_stock ? (
          <Badge variant="default">{t('product.badges.in_stock')}</Badge>
        ) : (
          <Badge variant="secondary">{t('product.badges.out_of_stock')}</Badge>
        )}
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

      {/* Tabs: 3 tabs */}
      <Tabs defaultValue="main" className="flex flex-col">
        <TabsList variant="line" className="mb-6">
          <TabsTrigger value="main">{t('product.tabs.main')}</TabsTrigger>
          <TabsTrigger value="images">{t('product.tabs.images')}</TabsTrigger>
        </TabsList>

        {/* Tab: Основне — BUF + Enriched + Attributes */}
        <TabsContent value="main">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Left column (2/3) */}
            <div className="space-y-6 lg:col-span-2">
              {/* BUF Data — all fields from BUF */}
              <Card className="bg-muted/30">
                <CardHeader>
                  <CardTitle>{t('product.buf.title')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.name')}</dt>
                      <dd className="text-sm">{product.buf_name ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.brand')}</dt>
                      <dd className="text-sm">{product.buf_brand ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.country')}</dt>
                      <dd className="text-sm">{ext.buf_country ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.code')}</dt>
                      <dd className="font-mono text-sm">{product.internal_code}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.sku')}</dt>
                      <dd className="font-mono text-sm">{product.sku}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.uktzed')}</dt>
                      <dd className="font-mono text-sm">{ext.uktzed ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.quantity')}</dt>
                      <dd className="text-sm">{product.buf_quantity ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.price')}</dt>
                      <dd className="text-sm">{formatPrice(product.buf_price, product.buf_currency)}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.info.in_stock')}</dt>
                      <dd>
                        {product.buf_in_stock ? (
                          <Badge variant="default">{t('product.badges.in_stock')}</Badge>
                        ) : (
                          <Badge variant="secondary">{t('product.badges.out_of_stock')}</Badge>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.info.category')}</dt>
                      <dd className="text-sm">
                        {product.category ? (
                          <Link to={`/products?category_id=${product.category.id}`} className="text-primary hover:underline">
                            {product.category.name}
                          </Link>
                        ) : '—'}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>

              {/* Enriched Data + Attributes — editable */}
            {canEdit ? (
              <Card>
                <CardHeader>
                  <CardTitle>{t('product.enriched.title')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <div className="space-y-1.5">
                      <Label>{t('product.buf.name')}</Label>
                      <Input
                        placeholder={product.buf_name ?? t('product.enriched.name_placeholder')}
                        {...form.register('custom_name')}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>{t('product.buf.brand')}</Label>
                      <Input
                        placeholder={product.buf_brand ?? t('product.enriched.brand_placeholder')}
                        {...form.register('custom_brand')}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>{t('product.buf.country')}</Label>
                      <Input
                        placeholder={t('product.enriched.country_placeholder')}
                        {...form.register('custom_country')}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>{t('product.info.category')}</Label>
                      <Controller
                        control={form.control}
                        name="custom_category_id"
                        render={({ field }) => {
                          const selectedCat = (categoriesData ?? []).find((c) => String(c.id) === field.value);
                          return (
                            <Select value={field.value || '__none__'} onValueChange={(val) => field.onChange(val === '__none__' ? '' : (val ?? ''))}>
                              <SelectTrigger>
                                <SelectValue>
                                  {selectedCat
                                    ? selectedCat.name
                                    : product.category?.name ?? t('product.enriched.category_placeholder')}
                                </SelectValue>
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="__none__">
                                  {product.category ? `${product.category.name} (оригінал)` : t('product.enriched.category_placeholder')}
                                </SelectItem>
                                {(categoriesData ?? []).map((cat) => (
                                  <SelectItem key={String(cat.id)} value={String(cat.id)}>
                                    {cat.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          );
                        }}
                      />
                      <p className="text-xs text-muted-foreground">
                        {t('product.enriched.category_hint')}
                      </p>
                    </div>
                    <div className="space-y-1.5">
                      <Label>{t('product.enriched.description')}</Label>
                      <Textarea rows={4} {...form.register('description')} />
                    </div>
                    <div className="space-y-1.5">
                      <Label>{t('product.enriched.seo_title')}</Label>
                      <Input {...form.register('seo_title')} />
                    </div>
                    <div className="space-y-1.5">
                      <Label>{t('product.enriched.seo_description')}</Label>
                      <Textarea rows={3} {...form.register('seo_description')} />
                    </div>

                    {/* Attributes inside enriched card */}
                    <Separator className="my-4" />
                    <AttributesSection productId={Number(id)} canEdit={canEdit} />

                    <Separator className="my-4" />

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
              /* Read-only view for manager/viewer */
              <Card>
                <CardHeader>
                  <CardTitle>{t('product.enriched.title')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <dl className="grid gap-4 sm:grid-cols-2">
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
                  <Separator className="my-4" />
                  <AttributesSection productId={Number(id)} canEdit={false} />
                </CardContent>
              </Card>
            )}
            </div>

            {/* Right column (1/3) — summary */}
            <div>
              <Card>
                <CardContent className="pt-6">
                  <dl className="space-y-5">
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.info.category')}</dt>
                      <dd className="mt-1 text-base font-semibold">
                        {product.category ? (
                          <Link
                            to={`/products?category_id=${product.category.id}`}
                            className="text-primary hover:underline"
                          >
                            {product.category.name}
                          </Link>
                        ) : '—'}
                      </dd>
                    </div>
                    <Separator />
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.code')}</dt>
                      <dd className="font-mono text-sm">{product.internal_code}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.quantity')}</dt>
                      <dd className="text-sm">{product.buf_quantity ?? '—'}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.buf.price')}</dt>
                      <dd className="text-lg font-bold">
                        {formatPrice(product.buf_price, product.buf_currency)}
                      </dd>
                    </div>
                    <Separator />
                    <div>
                      <dt className="text-xs text-muted-foreground">{t('product.info.in_stock')}</dt>
                      <dd className="mt-1">
                        {product.buf_in_stock ? (
                          <Badge variant="default">{t('product.badges.in_stock')}</Badge>
                        ) : (
                          <Badge variant="secondary">{t('product.badges.out_of_stock')}</Badge>
                        )}
                      </dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Tab: Зображення */}
        <TabsContent value="images">
          <div>
            {product.images.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {product.images.map((img, idx) => (
                  <div
                    key={img.id}
                    className="relative overflow-hidden rounded-lg border bg-muted"
                  >
                    <img
                      src={img.file_path}
                      alt=""
                      className="aspect-square w-full object-cover"
                    />
                    {idx === 0 && (
                      <Badge className="absolute left-2 top-2" variant="default">
                        {t('product.images.primary')}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={ImagePlus}
                title={t('product.images.empty')}
              />
            )}
            {canEdit && (
              <div className="mt-4 flex gap-2">
                <Button variant="outline">
                  <Upload className="mr-2 h-4 w-4" />
                  {t('product.images.upload')}
                </Button>
                <Button variant="outline">
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
