import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { apiClient } from '@/lib/api-client';
import { showSuccess } from '@/lib/toast';
import { useAuthStore } from '@/stores/auth-store';
import type { ReviewDetail, ReviewStatus } from '@/types/api';

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('uk-UA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateStr));
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function formatCost(usd: number): string {
  return `$${usd.toFixed(2)}`;
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

const FIELD_LABELS: Record<string, string> = {
  description: 'Опис',
  seo_title: 'SEO заголовок',
  seo_description: 'SEO опис',
  custom_name: 'Назва',
  attributes: 'Характеристики',
};

export function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuthStore();

  const canAction = hasRole(['admin', 'operator']);

  const { data: review, isLoading } = useQuery({
    queryKey: ['review', id],
    queryFn: async () => {
      const response = await apiClient.get<ReviewDetail>(
        `/api/reviews/${id}`,
      );
      return response.data;
    },
    enabled: !!id,
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<ReviewDetail>(
        `/api/reviews/${id}/approve`,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      showSuccess(t('reviews.status.approved'));
      navigate('/reviews');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<ReviewDetail>(
        `/api/reviews/${id}/reject`,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['review', id] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      showSuccess(t('reviews.status.rejected'));
      navigate('/reviews');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-10 w-96" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!review) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        {t('common.no_results')}
      </div>
    );
  }

  const isPending = review.status === 'pending';

  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb className="mb-4">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink render={<Link to="/reviews" />}>
              {t('review.breadcrumb')}
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{review.product.name}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => navigate('/reviews')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">{review.product.name}</h1>
        <Badge variant="secondary">
          {t(`reviews.type.${review.type}`)}
        </Badge>
        <Badge variant="outline" className="capitalize">
          {review.provider}
        </Badge>
        <Badge variant={getStatusBadgeVariant(review.status)}>
          {t(`reviews.status.${review.status}`)}
        </Badge>
      </div>

      {/* Diff View */}
      {review.type === 'text' && review.diff.length > 0 ? (
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          {/* Current */}
          <Card className="bg-muted/30">
            <CardHeader>
              <CardTitle className="text-base">{t('review.current')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {review.diff.map((d) => (
                <div key={d.field}>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    {FIELD_LABELS[d.field] ?? d.field}
                  </p>
                  <p className="text-sm">
                    {d.current ?? '—'}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Proposed */}
          <Card className="border-primary">
            <CardHeader>
              <CardTitle className="text-base">
                {t('review.proposed')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {review.diff.map((d) => (
                <div key={d.field}>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">
                    {FIELD_LABELS[d.field] ?? d.field}
                  </p>
                  <p className="rounded bg-green-100 px-1 text-sm dark:bg-green-900/30">
                    {d.proposed}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : review.type === 'text' ? (
        <Card className="mb-6">
          <CardContent className="py-8 text-center text-muted-foreground">
            {t('review.diff.no_changes')}
          </CardContent>
        </Card>
      ) : null}

      {/* Image preview for type=image */}
      {review.type === 'image' && review.image_url && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">
              {t('review.image_preview')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-lg border bg-muted">
              <img
                src={review.image_url}
                alt={t('review.image_preview')}
                className="mx-auto max-h-[500px] object-contain"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action buttons */}
      {canAction && isPending && (
        <div className="mb-6 flex gap-3">
          <Button
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending || rejectMutation.isPending}
          >
            {t('review.approve_all')}
          </Button>
          <Button
            variant="destructive"
            onClick={() => rejectMutation.mutate()}
            disabled={approveMutation.isPending || rejectMutation.isPending}
          >
            {t('review.reject')}
          </Button>
        </div>
      )}

      <Separator className="mb-6" />

      {/* Info section */}
      <Card>
        <CardContent className="pt-6">
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground">
                {t('review.info.provider')}
              </dt>
              <dd className="text-sm capitalize">{review.provider}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">
                {t('review.info.cost')}
              </dt>
              <dd className="text-sm">{formatCost(review.cost_usd)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">
                {t('review.info.duration')}
              </dt>
              <dd className="text-sm">
                {formatDuration(review.duration_ms)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">
                {t('review.info.date')}
              </dt>
              <dd className="text-sm">{formatDate(review.created_at)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
