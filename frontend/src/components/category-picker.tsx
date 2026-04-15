import { useEffect, useRef, useState } from 'react';
import { ChevronDown, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import type { Category } from '@/types/api';

export interface PickerItem {
  id: string;
  label: string;
  count: number;
  depth: number;
}

export function flattenCategories(cats: Category[], depth = 0): PickerItem[] {
  const out: PickerItem[] = [];
  for (const c of cats) {
    out.push({ id: c.id, label: c.name, count: c.product_count, depth });
    if (c.children?.length) out.push(...flattenCategories(c.children, depth + 1));
  }
  return out;
}

interface CategoryPickerProps {
  items: PickerItem[];
  value: string;
  onChange: (id: string) => void;
  placeholder: string;
  showCount?: boolean;
  allowClear?: boolean;
}

export function CategoryPicker({
  items,
  value,
  onChange,
  placeholder,
  showCount = true,
  allowClear = true,
}: CategoryPickerProps) {
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
          {selected && allowClear && (
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
