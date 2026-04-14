import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronRight,
  ChevronDown,
  Search,
  FolderTree,
  Pencil,
  Sparkles,
  Plus,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { PageHeader } from '@/components/page-header';
import { EmptyState } from '@/components/empty-state';
import axios from 'axios';
import { apiClient } from '@/lib/api-client';
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
import type { Category } from '@/types/api';

/** Flatten a category tree into a flat list for parent Select */
function flattenCategories(cats: Category[], level = 0): Array<Category & { level: number }> {
  const result: Array<Category & { level: number }> = [];
  for (const cat of cats) {
    result.push({ ...cat, level });
    if (cat.children && cat.children.length > 0) {
      result.push(...flattenCategories(cat.children, level + 1));
    }
  }
  return result;
}

interface CategoryNodeProps {
  category: Category;
  level: number;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  searchQuery: string;
  canEdit: boolean;
  isAdmin: boolean;
  onNavigate: (categoryId: string) => void;
  onEdit: (category: Category) => void;
  t: (key: string) => string;
}

function CategoryNode({
  category,
  level,
  expandedIds,
  onToggle,
  searchQuery,
  canEdit,
  isAdmin,
  onNavigate,
  onEdit,
  t,
}: CategoryNodeProps) {
  const hasChildren = category.children && category.children.length > 0;
  const isExpanded = expandedIds.has(category.id);

  const matchesSearch =
    !searchQuery ||
    category.name.toLowerCase().includes(searchQuery.toLowerCase());

  const childrenMatchSearch =
    searchQuery &&
    category.children?.some((child) =>
      child.name.toLowerCase().includes(searchQuery.toLowerCase()),
    );

  if (!matchesSearch && !childrenMatchSearch) {
    return null;
  }

  return (
    <div>
      <div
        className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50"
        style={{ paddingLeft: `${level * 24 + 8}px` }}
      >
        <button
          type="button"
          className="flex h-5 w-5 shrink-0 items-center justify-center"
          onClick={() => hasChildren && onToggle(category.id)}
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )
          ) : (
            <span className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          className="flex-1 text-left text-sm font-medium hover:text-primary"
          onClick={() => onNavigate(category.id)}
        >
          {category.name}
        </button>

        <Badge variant="secondary" className="text-xs">
          {category.product_count} {t('categories.products_count')}
        </Badge>

        {canEdit && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onEdit(category)}
          >
            <Pencil className="h-3 w-3" />
          </Button>
        )}

        {isAdmin && (
          <Button variant="ghost" size="icon" className="h-6 w-6" title={t('categories.bulk_enrich')}>
            <Sparkles className="h-3 w-3" />
          </Button>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div>
          {category.children!.map((child) => (
            <CategoryNode
              key={child.id}
              category={child}
              level={level + 1}
              expandedIds={expandedIds}
              onToggle={onToggle}
              searchQuery={searchQuery}
              canEdit={canEdit}
              isAdmin={isAdmin}
              onNavigate={onNavigate}
              onEdit={onEdit}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function CategoriesPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasRole } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [dialogName, setDialogName] = useState('');
  const [dialogParentId, setDialogParentId] = useState<string>('__none__');

  const canEdit = hasRole(['admin', 'operator']);
  const isAdmin = hasRole(['admin']);

  const { data: categories, isLoading } = useQuery({
    queryKey: ['categories', 'tree'],
    queryFn: async () => {
      const response = await apiClient.get<{ data: Category[] }>('/api/categories?tree=true');
      // Hide empty root subtrees (no products + no children — e.g. "Удалённые" after BUF filter).
      return response.data.data.filter(
        (r) => r.product_count > 0 || (r.children && r.children.length > 0),
      );
    },
  });

  const flatCats = useMemo(() => {
    if (!categories) return [];
    return flattenCategories(categories);
  }, [categories]);

  const createMutation = useMutation({
    mutationFn: async (data: { name: string; parent_id: string | null }) => {
      const response = await apiClient.post('/api/categories', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      showSuccess(t('categories.created'));
      setCreateDialogOpen(false);
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const updateMutation = useMutation({
    mutationFn: async (data: { id: string; name: string; parent_id: string | null }) => {
      const response = await apiClient.patch(`/api/categories/${data.id}`, {
        name: data.name,
        parent_id: data.parent_id,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      showSuccess(t('common.save') + ' ✓');
      setEditDialogOpen(false);
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleNavigate = (categoryId: string) => {
    navigate(`/products?category_id=${categoryId}`);
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setDialogName(category.name);
    setDialogParentId(category.parent_id ?? '__none__');
    setEditDialogOpen(true);
  };

  const handleCreate = () => {
    setDialogName('');
    setDialogParentId('__none__');
    setCreateDialogOpen(true);
  };

  const handleSaveEdit = () => {
    if (!editingCategory || !dialogName.trim()) return;
    updateMutation.mutate({
      id: editingCategory.id,
      name: dialogName.trim(),
      parent_id: dialogParentId === '__none__' ? null : dialogParentId,
    });
  };

  const handleSaveCreate = () => {
    if (!dialogName.trim()) return;
    createMutation.mutate({
      name: dialogName.trim(),
      parent_id: dialogParentId === '__none__' ? null : dialogParentId,
    });
  };

  // Auto-expand parents when searching
  const effectiveExpandedIds = useMemo(() => {
    if (!searchQuery || !categories) return expandedIds;
    const expanded = new Set(expandedIds);
    for (const cat of categories) {
      if (cat.children?.some((child) =>
        child.name.toLowerCase().includes(searchQuery.toLowerCase()),
      )) {
        expanded.add(cat.id);
      }
    }
    return expanded;
  }, [searchQuery, categories, expandedIds]);

  const parentSelectContent = (excludeId?: string) => (
    <SelectContent>
      <SelectItem value="__none__">{t('categories.no_parent')}</SelectItem>
      {flatCats
        .filter((c) => c.id !== excludeId)
        .map((cat) => (
          <SelectItem key={cat.id} value={cat.id}>
            {'—'.repeat(cat.level)} {cat.name}
          </SelectItem>
        ))}
    </SelectContent>
  );

  return (
    <div>
      <PageHeader title={t('categories.title')}>
        {canEdit && (
          <Button onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" />
            {t('categories.add')}
          </Button>
        )}
      </PageHeader>

      <div className="mb-4">
        <div className="relative w-64">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={t('categories.search')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      ) : categories && categories.length > 0 ? (
        <div className="rounded-lg border">
          {categories.map((cat) => (
            <CategoryNode
              key={cat.id}
              category={cat}
              level={0}
              expandedIds={effectiveExpandedIds}
              onToggle={toggleExpanded}
              searchQuery={searchQuery}
              canEdit={canEdit}
              isAdmin={isAdmin}
              onNavigate={handleNavigate}
              onEdit={handleEdit}
              t={t}
            />
          ))}
        </div>
      ) : (
        <EmptyState icon={FolderTree} title={t('categories.empty')} />
      )}

      {/* Edit Category Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('categories.edit_title')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('categories.name')}</Label>
              <Input
                value={dialogName}
                onChange={(e) => setDialogName(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t('categories.parent')}</Label>
              <Select value={dialogParentId} onValueChange={(val) => setDialogParentId(val ?? '__none__')}>
                <SelectTrigger>
                  <SelectValue>
                    {dialogParentId === '__none__'
                      ? t('categories.no_parent')
                      : flatCats.find((c) => c.id === dialogParentId)?.name ?? t('categories.parent')}
                  </SelectValue>
                </SelectTrigger>
                {parentSelectContent(editingCategory?.id)}
              </Select>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              {t('common.cancel')}
            </DialogClose>
            <Button onClick={handleSaveEdit} disabled={updateMutation.isPending}>
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Category Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('categories.add')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('categories.name')}</Label>
              <Input
                value={dialogName}
                onChange={(e) => setDialogName(e.target.value)}
                placeholder={t('categories.name_placeholder')}
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t('categories.parent')}</Label>
              <Select value={dialogParentId} onValueChange={(val) => setDialogParentId(val ?? '__none__')}>
                <SelectTrigger>
                  <SelectValue>
                    {dialogParentId === '__none__'
                      ? t('categories.no_parent')
                      : flatCats.find((c) => c.id === dialogParentId)?.name ?? t('categories.parent')}
                  </SelectValue>
                </SelectTrigger>
                {parentSelectContent()}
              </Select>
              <p className="text-xs text-muted-foreground">{t('categories.parent_hint')}</p>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              {t('common.cancel')}
            </DialogClose>
            <Button onClick={handleSaveCreate} disabled={createMutation.isPending || !dialogName.trim()}>
              {t('categories.add')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
