import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { apiClient } from '@/lib/api-client';
import { showSuccess, showError } from '@/lib/toast';
import type { ProductAttribute } from '@/types/api';

interface Props {
  productId: string;
  canEdit: boolean;
}

export function AttributesSection({ productId, canEdit }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ProductAttribute | null>(null);
  const [keyInput, setKeyInput] = useState('');
  const [valueInput, setValueInput] = useState('');

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingAttr, setDeletingAttr] = useState<ProductAttribute | null>(null);

  const { data } = useQuery({
    queryKey: ['attributes', productId],
    queryFn: async () => {
      const response = await apiClient.get<{ data: ProductAttribute[] }>(
        `/api/products/${productId}/attributes`,
      );
      return response.data.data;
    },
  });

  const attributes = data ?? [];

  const createMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      const response = await apiClient.post(
        `/api/products/${productId}/attributes`,
        { key, value },
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attributes', productId] });
      showSuccess(t('product.attributes.created'));
      setDialogOpen(false);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error;
      showError(msg || t('product.attributes.error_duplicate'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, key, value }: { id: string; key: string; value: string }) => {
      const response = await apiClient.patch(
        `/api/products/${productId}/attributes/${id}`,
        { key, value },
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attributes', productId] });
      showSuccess(t('common.save') + ' ✓');
      setDialogOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/products/${productId}/attributes/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attributes', productId] });
      showSuccess(t('product.attributes.deleted'));
      setDeleteDialogOpen(false);
    },
  });

  const openCreate = (e: React.MouseEvent) => {
    e.preventDefault();
    setEditing(null);
    setKeyInput('');
    setValueInput('');
    setDialogOpen(true);
  };

  const openEdit = (e: React.MouseEvent, attr: ProductAttribute) => {
    e.preventDefault();
    setEditing(attr);
    setKeyInput(attr.key);
    setValueInput(attr.value);
    setDialogOpen(true);
  };

  const openDelete = (e: React.MouseEvent, attr: ProductAttribute) => {
    e.preventDefault();
    setDeletingAttr(attr);
    setDeleteDialogOpen(true);
  };

  const handleSave = () => {
    if (!keyInput.trim() || !valueInput.trim()) return;
    if (editing) {
      updateMutation.mutate({
        id: editing.id,
        key: keyInput.trim(),
        value: valueInput.trim(),
      });
    } else {
      createMutation.mutate({
        key: keyInput.trim(),
        value: valueInput.trim(),
      });
    }
  };

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold">{t('product.attributes.title')}</h3>
      {attributes.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('product.attributes.key')}</TableHead>
              <TableHead>{t('product.attributes.value')}</TableHead>
              <TableHead className="w-24">{t('product.attributes.source')}</TableHead>
              {canEdit && <TableHead className="w-24 text-right">{t('common.actions')}</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {attributes.map((attr) => (
              <TableRow key={attr.id}>
                <TableCell className="font-medium">{attr.key}</TableCell>
                <TableCell>{attr.value}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{attr.source}</Badge>
                </TableCell>
                {canEdit && (
                  <TableCell className="text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={(e) => openEdit(e, attr)}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive"
                      onClick={(e) => openDelete(e, attr)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-muted-foreground">{t('product.attributes.empty')}</p>
      )}
      {canEdit && (
        <Button type="button" variant="outline" size="sm" className="mt-3" onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          {t('product.attributes.add')}
        </Button>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? t('product.attributes.edit_title') : t('product.attributes.add_title')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('product.attributes.key')}</Label>
              <Input
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder={t('product.attributes.key_placeholder')}
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t('product.attributes.value')}</Label>
              <Input
                value={valueInput}
                onChange={(e) => setValueInput(e.target.value)}
                placeholder={t('product.attributes.value_placeholder')}
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button type="button" variant="outline" />}>
              {t('common.cancel')}
            </DialogClose>
            <Button
              type="button"
              onClick={handleSave}
              disabled={!keyInput.trim() || !valueInput.trim() || createMutation.isPending || updateMutation.isPending}
            >
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete AlertDialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('product.attributes.delete_title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {deletingAttr ? `${deletingAttr.key}: ${deletingAttr.value}` : ''}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingAttr && deleteMutation.mutate(deletingAttr.id)}
              className="bg-destructive text-destructive-foreground"
            >
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
