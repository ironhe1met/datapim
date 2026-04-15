import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Loader2, Eye, Check, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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

function flatten(cats: Category[], depth = 0): Array<Category & { depth: number }> {
  const out: Array<Category & { depth: number }> = [];
  for (const c of cats) {
    out.push({ ...c, depth });
    if (c.children?.length) out.push(...flatten(c.children, depth + 1));
  }
  return out;
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
      return flatten(r.data.data);
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
    },
    onError: (err) => showError(extractError(err)),
  });

  const canRun =
    bufCategoryId.length > 0 && (customBrand.trim().length > 0 || customCategoryId.length > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-warning" />
          Bulk Update — масова зміна товарів
        </CardTitle>
        <CardDescription>
          Вибери BUF категорію (часто це "бренд") і встав значення — застосується до всіх товарів
          включно з підкатегоріями. Спочатку Preview, потім Apply.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5">
          <Label>BUF категорія (звідки беремо товари)</Label>
          <Select
            value={bufCategoryId || ''}
            onValueChange={(v) => {
              setBufCategoryId(v ?? '');
              setPreview(null);
            }}
          >
            <SelectTrigger>
              <SelectValue>
                {bufCategoryId
                  ? categories?.find((c) => c.id === bufCategoryId)?.name ?? 'Виберіть...'
                  : 'Виберіть BUF категорію'}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(categories ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {'—'.repeat(c.depth)} {c.name} ({c.product_count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={includeDescendants}
              onChange={(e) => {
                setIncludeDescendants(e.target.checked);
                setPreview(null);
              }}
            />
            Включати товари з підкатегорій (рекурсивно)
          </label>
        </div>

        <div className="space-y-1.5">
          <Label>Новий бренд (custom_brand)</Label>
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
          <Label>Перенести в нашу категорію (опціонально)</Label>
          <Select
            value={customCategoryId || '__none__'}
            onValueChange={(v) => {
              setCustomCategoryId(v === '__none__' ? '' : v ?? '');
              setPreview(null);
            }}
          >
            <SelectTrigger>
              <SelectValue>
                {customCategoryId
                  ? categories?.find((c) => c.id === customCategoryId)?.name ?? 'Виберіть...'
                  : 'Не змінювати'}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Не змінювати</SelectItem>
              {(categories ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {'—'.repeat(c.depth)} {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={!canRun || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
          >
            {previewMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Eye className="mr-2 h-4 w-4" />
            )}
            Preview (без змін)
          </Button>
          <Button
            disabled={!preview || preview.matched === 0 || applyMutation.isPending}
            onClick={() => applyMutation.mutate()}
          >
            {applyMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-2 h-4 w-4" />
            )}
            Apply{preview ? ` (${preview.matched})` : ''}
          </Button>
        </div>

        {preview && (
          <div className="rounded-lg border bg-muted/30 p-3">
            <p className="mb-2 text-sm font-medium">
              Знайдено {preview.matched} товарів. Перші 5:
            </p>
            <ul className="space-y-1 text-xs">
              {preview.sample.map((s) => (
                <li key={s.id} className="font-mono">
                  {s.internal_code} — {s.name}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
