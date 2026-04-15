import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Loader2, Eye, Check, AlertTriangle, ChevronDown, X } from 'lucide-react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';
import { showError, showSuccess } from '@/lib/toast';
import type { Category } from '@/types/api';

interface PickerItem {
  id: string;
  label: string;
  count: number;
  depth: number;
}

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

function flatten(cats: Category[], depth = 0): PickerItem[] {
  const out: PickerItem[] = [];
  for (const c of cats) {
    out.push({ id: c.id, label: c.name, count: c.product_count, depth });
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

interface CategoryPickerProps {
  items: PickerItem[];
  value: string;
  onChange: (id: string) => void;
  placeholder: string;
  showCount?: boolean;
}

function CategoryPicker({ items, value, onChange, placeholder, showCount = true }: CategoryPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const selected = items.find((i) => i.id === value);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const filtered = (
    !query
      ? items
      : items.filter((i) => i.label.toLowerCase().includes(query.toLowerCase()))
  ).slice(0, 100);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs hover:bg-muted/50"
        onClick={() => setOpen(!open)}
      >
        <span className={selected ? '' : 'text-muted-foreground'}>
          {selected?.label ?? placeholder}
          {selected && showCount && (
            <span className="ml-2 text-xs text-muted-foreground">({selected.count})</span>
          )}
        </span>
        <div className="flex items-center gap-1">
          {selected && (
            <X
              className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground"
              onClick={(e) => {
                e.stopPropagation();
                onChange('');
              }}
            />
          )}
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </div>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          <Input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Пошук..."
            className="rounded-b-none border-0 border-b focus-visible:ring-0"
          />
          <div className="max-h-64 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-sm text-muted-foreground">Нічого не знайдено</div>
            ) : (
              filtered.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm hover:bg-muted ${
                    item.id === value ? 'bg-muted' : ''
                  }`}
                  onClick={() => {
                    onChange(item.id);
                    setOpen(false);
                    setQuery('');
                  }}
                >
                  <span className="truncate">
                    {'\u00a0\u00a0'.repeat(item.depth)}
                    {item.label}
                  </span>
                  {showCount && (
                    <span className="shrink-0 text-xs text-muted-foreground">{item.count}</span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
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
