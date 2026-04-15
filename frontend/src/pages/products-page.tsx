import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Package, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { PageHeader } from '@/components/page-header';
import { EmptyState } from '@/components/empty-state';
import { apiClient } from '@/lib/api-client';
import { resolveImageUrl } from '@/lib/utils';
import type {
  PaginatedResponse,
  ProductListItem,
  Category,
} from '@/types/api';

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

export function ProductsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const search = searchParams.get('search') ?? '';
  const categoryId = searchParams.get('category_id') ?? '';
  const inStock = searchParams.get('in_stock') ?? '';
  const enrichmentStatus = searchParams.get('enrichment_status') ?? '';
  const page = Number(searchParams.get('page') ?? '1');
  const perPage = Number(searchParams.get('per_page') ?? '20');

  const [searchInput, setSearchInput] = useState(search);
  const isUserTyping = useRef(false);

  const hasActiveFilters = search || categoryId || inStock || enrichmentStatus;

  // Debounced search — only when user types, not on URL changes
  useEffect(() => {
    if (!isUserTyping.current) return;
    const timer = setTimeout(() => {
      isUserTyping.current = false;
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (searchInput) {
          next.set('search', searchInput);
        } else {
          next.delete('search');
        }
        next.set('page', '1');
        return next;
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, setSearchParams]);

  const handleSearchChange = (value: string) => {
    isUserTyping.current = true;
    setSearchInput(value);
  };

  const updateFilter = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        next.set('page', '1');
        return next;
      });
    },
    [setSearchParams],
  );

  const resetFilters = useCallback(() => {
    setSearchInput('');
    setSearchParams({});
  }, [setSearchParams]);

  const setPage = useCallback(
    (newPage: number) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set('page', String(newPage));
        return next;
      });
    },
    [setSearchParams],
  );

  const { data: categoriesTree } = useQuery({
    queryKey: ['categories', 'tree'],
    queryFn: async () => {
      const response = await apiClient.get<{ data: Category[] }>(
        '/api/categories?tree=true',
      );
      return response.data.data;
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: [
      'products',
      { search, category_id: categoryId, in_stock: inStock, enrichment_status: enrichmentStatus, page, perPage },
    ],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('per_page', String(perPage));
      if (search) params.set('search', search);
      if (categoryId) params.set('category_id', categoryId);
      if (inStock) params.set('in_stock', inStock);
      if (enrichmentStatus) params.set('enrichment_status', enrichmentStatus);
      const response = await apiClient.get<PaginatedResponse<ProductListItem>>(
        `/api/products?${params.toString()}`,
      );
      return response.data;
    },
  });

  const setPerPage = (val: number) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('per_page', String(val));
      next.set('page', '1');
      return next;
    });
  };

  function renderEnrichmentBadge(status: string) {
    switch (status) {
      case 'none':
        return <Badge variant="destructive">{t('products.filters.enrichment_none')}</Badge>;
      case 'partial':
        return <Badge variant="secondary">{t('products.filters.enrichment_partial')}</Badge>;
      case 'full':
        return <Badge variant="default">{t('products.filters.enrichment_full')}</Badge>;
      default:
        return null;
    }
  }

  function renderStockBadge(inStockValue: boolean) {
    return inStockValue ? (
      <Badge variant="default">{t('products.filters.in_stock_yes')}</Badge>
    ) : (
      <Badge variant="secondary">{t('products.filters.in_stock_no')}</Badge>
    );
  }

  return (
    <div>
      <PageHeader title={t('products.title')} />

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative w-64">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t('products.search')}
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-8"
          />
        </div>

        <Select
          value={categoryId || '__all__'}
          onValueChange={(val) => updateFilter('category_id', val === '__all__' ? '' : (val ?? ''))}
        >
          <SelectTrigger className="w-48">
            <SelectValue>
              {categoryId
                ? (() => {
                    const allCats = categoriesTree?.flatMap((c) => [c, ...(c.children ?? [])]) ?? [];
                    return allCats.find((c) => String(c.id) === categoryId)?.name ?? t('products.filters.category');
                  })()
                : t('products.filters.category')}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('products.filters.all')}</SelectItem>
            {categoriesTree?.map((cat) => [
              <SelectItem key={cat.id} value={String(cat.id)}>
                {cat.name}
              </SelectItem>,
              ...(cat.children?.map((child) => (
                <SelectItem key={child.id} value={String(child.id)}>
                  {'  '}{child.name}
                </SelectItem>
              )) ?? []),
            ])}
          </SelectContent>
        </Select>

        <Select
          value={inStock || '__all__'}
          onValueChange={(val) => updateFilter('in_stock', val === '__all__' ? '' : (val ?? ''))}
        >
          <SelectTrigger className="w-40">
            <SelectValue>
              {inStock === 'true'
                ? t('products.filters.in_stock_yes')
                : inStock === 'false'
                  ? t('products.filters.in_stock_no')
                  : t('products.filters.in_stock')}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('products.filters.all')}</SelectItem>
            <SelectItem value="true">{t('products.filters.in_stock_yes')}</SelectItem>
            <SelectItem value="false">{t('products.filters.in_stock_no')}</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={enrichmentStatus || '__all__'}
          onValueChange={(val) => updateFilter('enrichment_status', val === '__all__' ? '' : (val ?? ''))}
        >
          <SelectTrigger className="w-40">
            <SelectValue>
              {enrichmentStatus === 'none'
                ? t('products.filters.enrichment_none')
                : enrichmentStatus === 'partial'
                  ? t('products.filters.enrichment_partial')
                  : enrichmentStatus === 'full'
                    ? t('products.filters.enrichment_full')
                    : t('products.filters.enrichment')}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('products.filters.all')}</SelectItem>
            <SelectItem value="none">{t('products.filters.enrichment_none')}</SelectItem>
            <SelectItem value="partial">{t('products.filters.enrichment_partial')}</SelectItem>
            <SelectItem value="full">{t('products.filters.enrichment_full')}</SelectItem>
          </SelectContent>
        </Select>

        {hasActiveFilters && (
          <Button variant="ghost" onClick={resetFilters}>
            {t('products.filters.reset')}
          </Button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : data && data.data.length > 0 ? (
        <>
          <Table className="w-full table-fixed">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[28%]">{t('products.table.name')}</TableHead>
                <TableHead className="w-[12%]">Код</TableHead>
                <TableHead className="w-[12%]">Бренд</TableHead>
                <TableHead className="w-[18%]">{t('products.table.category')}</TableHead>
                <TableHead className="w-[7%] text-right">Кількість</TableHead>
                <TableHead className="w-[10%] text-right">{t('products.table.price')}</TableHead>
                <TableHead className="w-[8%]">{t('products.table.in_stock')}</TableHead>
                <TableHead className="w-[5%]">{t('products.table.enrichment')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((product) => (
                <TableRow
                  key={product.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/products/${product.id}`)}
                >
                  <TableCell className="overflow-hidden">
                    <div className="flex items-center gap-3">
                      {product.primary_image ? (
                        <div className="h-8 w-8 flex-shrink-0 overflow-hidden rounded bg-muted">
                          <img
                            src={resolveImageUrl(product.primary_image.file_path)}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        </div>
                      ) : (
                        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded bg-muted">
                          <Package className="h-4 w-4 text-muted-foreground" />
                        </div>
                      )}
                      <span className="truncate font-medium" title={product.name}>
                        {product.name}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="truncate font-mono text-xs" title={product.internal_code}>
                    {product.internal_code}
                  </TableCell>
                  <TableCell className="truncate" title={product.brand ?? ''}>
                    {product.brand ?? '—'}
                  </TableCell>
                  <TableCell className="truncate" title={product.category?.name ?? ''}>
                    {product.category?.name ?? '—'}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {product.quantity ?? 0}
                  </TableCell>
                  <TableCell className="text-right tabular-nums whitespace-nowrap">
                    {formatPrice(product.price, product.currency)}
                  </TableCell>
                  <TableCell>{renderStockBadge(product.in_stock)}</TableCell>
                  <TableCell>
                    {renderEnrichmentBadge(product.enrichment_status)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              Всього: {data.meta.total}
            </p>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">На сторінці:</span>
                <Select
                  value={String(perPage)}
                  onValueChange={(v) => setPerPage(Number(v ?? '20'))}
                >
                  <SelectTrigger className="h-8 w-20">
                    <SelectValue>{perPage}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon-sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm">
                  {page} / {data.meta.last_page}
                </span>
                <Button
                  variant="outline"
                  size="icon-sm"
                  disabled={page >= data.meta.last_page}
                  onClick={() => setPage(page + 1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </>
      ) : hasActiveFilters ? (
        <EmptyState
          icon={Search}
          title={t('products.empty.filtered_title')}
          action={{
            label: t('products.empty.filtered_action'),
            onClick: resetFilters,
          }}
        />
      ) : (
        <EmptyState
          icon={Package}
          title={t('products.empty.title')}
          description={t('products.empty.description')}
        />
      )}
    </div>
  );
}
