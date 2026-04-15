import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Loader2, Eye, Check, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CategoryPicker, flattenCategories } from '@/components/category-picker';
import { apiClient } from '@/lib/api-client';
import { showError, showSuccess } from '@/lib/toast';
import type { Category } from '@/types/api';

interface SampleItem {
  id: string;
  internal_code: string;
  name: string;
}

interface BulkResponse {
  matched: number;
  updated: number;
  sample: SampleItem[];
}

function extractError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { error?: string } | undefined;
    if (data?.error) return data.error;
  }
  return 'Сталася помилка';
}

export function BulkUpdateTool() {
  const [bufCategoryId, setBufCategoryId] = useState('');
  const [includeDescendants, setIncludeDescendants] = useState(true);
  const [customBrand, setCustomBrand] = useState('');
  const [customCategoryId, setCustomCategoryId] = useState('');
  const [preview, setPreview] = useState<BulkResponse | null>(null);

  const { data: categories } = useQuery({
    queryKey: ['categories', 'tree-for-bulk'],
    queryFn: async () => {
      const r = await apiClient.get<{ data: Category[] }>('/api/categories?tree=true');
      return flattenCategories(r.data.data);
    },
  });

  const buildPayload = (dryRun: boolean) => {
    const set: Record<string, string> = {};
    if (customBrand.trim()) set.custom_brand = customBrand.trim();
    if (customCategoryId) set.custom_category_id = customCategoryId;
    return {
      filter: { buf_category_id: bufCategoryId, include_descendants: includeDescendants },
      set,
      dry_run: dryRun,
    };
  };

  const previewMutation = useMutation({
    mutationFn: async () => {
      const r = await apiClient.post<BulkResponse>(
        '/api/products/bulk-update',
        buildPayload(true),
      );
      return r.data;
    },
    onSuccess: (data) => setPreview(data),
    onError: (err) => showError(extractError(err)),
  });

  const applyMutation = useMutation({
    mutationFn: async () => {
      const r = await apiClient.post<BulkResponse>(
        '/api/products/bulk-update',
        buildPayload(false),
      );
      return r.data;
    },
    onSuccess: (data) => {
      showSuccess(`Оновлено ${data.updated} товарів`);
      setPreview(null);
      setCustomBrand('');
      setCustomCategoryId('');
    },
    onError: (err) => showError(extractError(err)),
  });

  const canRun = bufCategoryId.length > 0 && (customBrand.trim().length > 0 || customCategoryId.length > 0);
  const items = categories ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AlertTriangle className="h-4 w-4 text-warning" />
          Bulk Update — масова зміна товарів
        </CardTitle>
        <CardDescription>
          Виберіть BUF категорію (часто це бренд) → задайте новий бренд або
          цільову категорію → Preview → Apply.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          {/* Source */}
          <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Звідки (BUF)
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Категорія</Label>
              <CategoryPicker
                items={items}
                value={bufCategoryId}
                onChange={(id) => {
                  setBufCategoryId(id);
                  setPreview(null);
                }}
                placeholder="Оберіть BUF категорію"
              />
            </div>
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={includeDescendants}
                onChange={(e) => {
                  setIncludeDescendants(e.target.checked);
                  setPreview(null);
                }}
              />
              Включати підкатегорії
            </label>
          </div>

          {/* Target */}
          <div className="space-y-2 rounded-lg border bg-muted/20 p-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Що змінюємо
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Новий бренд (custom_brand)</Label>
              <Input
                placeholder="напр. JET"
                value={customBrand}
                onChange={(e) => {
                  setCustomBrand(e.target.value);
                  setPreview(null);
                }}
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Перенести в категорію (опціонально)</Label>
              <CategoryPicker
                items={items}
                value={customCategoryId}
                onChange={(id) => {
                  setCustomCategoryId(id);
                  setPreview(null);
                }}
                placeholder="Без зміни"
                showCount={false}
              />
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!canRun || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
          >
            {previewMutation.isPending ? (
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Eye className="mr-2 h-3.5 w-3.5" />
            )}
            Preview
          </Button>
          <Button
            size="sm"
            disabled={!preview || preview.matched === 0 || applyMutation.isPending}
            onClick={() => applyMutation.mutate()}
          >
            {applyMutation.isPending ? (
              <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Check className="mr-2 h-3.5 w-3.5" />
            )}
            Apply{preview ? ` (${preview.matched})` : ''}
          </Button>
          {preview && (
            <span className="text-xs text-muted-foreground">
              знайдено <strong className="text-foreground">{preview.matched}</strong> товарів
            </span>
          )}
        </div>

        {preview && preview.sample.length > 0 && (
          <div className="rounded-lg border bg-muted/30 p-3">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Приклади (перші 5):</p>
            <ul className="space-y-0.5">
              {preview.sample.map((s) => (
                <li key={s.id} className="truncate font-mono text-xs">
                  <span className="text-muted-foreground">{s.internal_code}</span>{' '}
                  — {s.name}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
