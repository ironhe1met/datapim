import { Fragment, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
  Upload,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
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
import axios from 'axios';
import { apiClient } from '@/lib/api-client';
import { showSuccess, showError } from '@/lib/toast';
import { useAuthStore } from '@/stores/auth-store';
import type { PaginatedResponse } from '@/types/api';

interface ImportLogEntry {
  id: string;
  file_name: string;
  status: 'completed' | 'failed' | 'running';
  started_at: string;
  finished_at: string | null;
  products_created: number;
  products_updated: number;
  products_stock_changed: number;
  categories_upserted: number;
  errors_count: number;
  error_details: Array<Record<string, unknown>> | null;
}

function formatErrorEntry(err: Record<string, unknown>): string {
  const type = err.type as string | undefined;
  const parts = Object.entries(err)
    .filter(([k]) => k !== 'type')
    .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
    .join(', ');
  return type ? `[${type}] ${parts}` : parts || JSON.stringify(err);
}

function extractApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { error?: string } | undefined;
    if (data?.error) return data.error;
  }
  return 'Сталася помилка';
}

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('uk-UA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateStr));
}

function getStatusVariant(
  status: string,
): 'default' | 'destructive' | 'secondary' {
  switch (status) {
    case 'completed':
      return 'default';
    case 'failed':
      return 'destructive';
    case 'running':
      return 'secondary';
    default:
      return 'secondary';
  }
}

export function ImportPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { hasRole } = useAuthStore();
  const isAdmin = hasRole(['admin']);
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Number(searchParams.get('page') ?? '1');

  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

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

  const toggleRow = (id: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const { data, isLoading } = useQuery({
    queryKey: ['import-logs', { page }],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('per_page', '10');
      const response = await apiClient.get<PaginatedResponse<ImportLogEntry>>(
        `/api/import/logs?${params.toString()}`,
      );
      return response.data;
    },
    refetchInterval: (query) => {
      const logs = query.state.data?.data ?? [];
      return logs.some((l) => l.status === 'running') ? 3000 : false;
    },
  });

  const triggerMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/import/trigger');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['import-logs'] });
      showSuccess(t('import.trigger.success'));
    },
    onError: (err) => showError(extractApiError(err)),
  });

  return (
    <div>
      <PageHeader title={t('import.title')} />

      {/* Trigger Card — admin only */}
      {isAdmin && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>{t('import.trigger.title')}</CardTitle>
            <CardDescription>{t('import.trigger.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => triggerMutation.mutate()}
              disabled={triggerMutation.isPending}
            >
              {triggerMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('import.trigger.loading')}
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  {t('import.trigger.button')}
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Import Logs */}
      <Card>
        <CardHeader>
          <CardTitle>{t('import.logs.title')}</CardTitle>
        </CardHeader>
        <CardContent>
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
                    <TableHead className="w-8" />
                    <TableHead>{t('import.logs.date')}</TableHead>
                    <TableHead>{t('import.logs.file')}</TableHead>
                    <TableHead>{t('import.logs.status')}</TableHead>
                    <TableHead>{t('import.logs.created')}</TableHead>
                    <TableHead>{t('import.logs.updated')}</TableHead>
                    <TableHead>{t('import.logs.errors')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.data.map((log) => {
                    const isExpanded = expandedRows.has(log.id);
                    const hasErrors = log.errors_count > 0;

                    return (
                      <Fragment key={log.id}>
                        <TableRow
                          className={hasErrors ? 'cursor-pointer' : ''}
                          onClick={() => hasErrors && toggleRow(log.id)}
                        >
                          <TableCell>
                            {hasErrors && (
                              <Button
                                variant="ghost"
                                size="icon-xs"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleRow(log.id);
                                }}
                              >
                                {isExpanded ? (
                                  <ChevronUp className="h-3 w-3" />
                                ) : (
                                  <ChevronDown className="h-3 w-3" />
                                )}
                              </Button>
                            )}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDate(log.started_at)}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {log.file_name}
                          </TableCell>
                          <TableCell>
                            <Badge variant={getStatusVariant(log.status)}>
                              {t(`import.status.${log.status}`)}
                            </Badge>
                          </TableCell>
                          <TableCell>{log.products_created}</TableCell>
                          <TableCell>{log.products_updated}</TableCell>
                          <TableCell>
                            {log.errors_count > 0 ? (
                              <Badge variant="destructive">
                                {log.errors_count}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground">0</span>
                            )}
                          </TableCell>
                        </TableRow>
                        {isExpanded && log.error_details && (
                          <TableRow>
                            <TableCell colSpan={7} className="bg-destructive/5 p-3">
                              <p className="mb-2 text-sm font-medium">
                                {t('import.logs.error_details')}
                              </p>
                              <ul className="space-y-1">
                                {log.error_details.map((err, i) => (
                                  <li
                                    key={i}
                                    className="break-all font-mono text-xs text-destructive"
                                  >
                                    {formatErrorEntry(err)}
                                  </li>
                                ))}
                              </ul>
                            </TableCell>
                          </TableRow>
                        )}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {t('import.logs.title')}: {data.meta.total}
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
              icon={Upload}
              title={t('import.empty.title')}
              action={
                isAdmin
                  ? {
                      label: t('import.empty.action'),
                      onClick: () => triggerMutation.mutate(),
                    }
                  : undefined
              }
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
