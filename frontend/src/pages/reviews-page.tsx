import { useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle, ChevronLeft, ChevronRight } from 'lucide-react';
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
import type {
  PaginatedResponse,
  ReviewListItem,
  ReviewStatus,
} from '@/types/api';

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('uk-UA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateStr));
}

function getStatusBadgeVariant(
  status: ReviewStatus,
): 'secondary' | 'default' | 'destructive' | 'outline' {
  switch (status) {
    case 'pending':
      return 'outline';
    case 'approved':
      return 'default';
    case 'rejected':
      return 'destructive';
    case 'partial':
      return 'secondary';
    default:
      return 'secondary';
  }
}

export function ReviewsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const status = searchParams.get('status') ?? '';
  const page = Number(searchParams.get('page') ?? '1');

  const [statusFilter, setStatusFilter] = useState(status);

  const updateFilter = useCallback(
    (value: string) => {
      setStatusFilter(value);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value && value !== '__all__') {
          next.set('status', value);
        } else {
          next.delete('status');
        }
        next.set('page', '1');
        return next;
      });
    },
    [setSearchParams],
  );

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

  const { data, isLoading } = useQuery({
    queryKey: ['reviews', { status: statusFilter, page }],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('per_page', '10');
      if (statusFilter && statusFilter !== '__all__') {
        params.set('status', statusFilter);
      }
      const response = await apiClient.get<PaginatedResponse<ReviewListItem>>(
        `/api/reviews?${params.toString()}`,
      );
      return response.data;
    },
  });

  // Count pending for the header badge
  const { data: pendingData } = useQuery({
    queryKey: ['reviews', 'pending-count'],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<ReviewListItem>>(
        '/api/reviews?status=pending&per_page=1',
      );
      return response.data;
    },
  });

  const pendingCount = pendingData?.meta.total ?? 0;

  function getStatusLabel(s: ReviewStatus): string {
    return t(`reviews.status.${s}`);
  }

  function getTypeLabel(type: string): string {
    return t(`reviews.type.${type}`);
  }

  return (
    <div>
      <PageHeader title={t('reviews.title')}>
        {pendingCount > 0 && (
          <Badge variant="outline">{pendingCount}</Badge>
        )}
      </PageHeader>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select
          value={statusFilter || '__all__'}
          onValueChange={(val) => updateFilter(val === '__all__' ? '' : (val ?? ''))}
        >
          <SelectTrigger className="w-48">
            <SelectValue>
              {statusFilter === 'pending'
                ? t('reviews.filters.status_pending')
                : statusFilter === 'approved'
                  ? t('reviews.filters.status_approved')
                  : statusFilter === 'rejected'
                    ? t('reviews.filters.status_rejected')
                    : statusFilter === 'partial'
                      ? t('reviews.filters.status_partial')
                      : t('reviews.filters.all')}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{t('reviews.filters.all')}</SelectItem>
            <SelectItem value="pending">
              {t('reviews.filters.status_pending')}
            </SelectItem>
            <SelectItem value="approved">
              {t('reviews.filters.status_approved')}
            </SelectItem>
            <SelectItem value="rejected">
              {t('reviews.filters.status_rejected')}
            </SelectItem>
            <SelectItem value="partial">
              {t('reviews.filters.status_partial')}
            </SelectItem>
          </SelectContent>
        </Select>
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
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('reviews.table.product')}</TableHead>
                <TableHead>{t('reviews.table.type')}</TableHead>
                <TableHead>{t('reviews.table.provider')}</TableHead>
                <TableHead>{t('reviews.table.status')}</TableHead>
                <TableHead>{t('reviews.table.date')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((review) => (
                <TableRow
                  key={review.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/reviews/${review.id}`)}
                >
                  <TableCell className="font-medium">
                    {review.product.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">
                      {getTypeLabel(review.type)}
                    </Badge>
                  </TableCell>
                  <TableCell className="capitalize">
                    {review.provider}
                  </TableCell>
                  <TableCell>
                    <Badge variant={getStatusBadgeVariant(review.status)}>
                      {getStatusLabel(review.status)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(review.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {t('reviews.table.product')}: {data.meta.total}
            </p>
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
        </>
      ) : (
        <EmptyState
          icon={CheckCircle}
          title={t('reviews.empty.title')}
          description={t('reviews.empty.description')}
        />
      )}
    </div>
  );
}
