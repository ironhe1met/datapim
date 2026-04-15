import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Users, Plus, Pencil, UserMinus, UserCheck, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
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
import type { PaginatedResponse, User, UserRole } from '@/types/api';

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('uk-UA', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(dateStr));
}

const createUserSchema = z.object({
  email: z.email({ message: 'Некоректний email' }),
  name: z.string().min(1, 'Вкажіть ім’я'),
  password: z.string().min(8, 'Пароль має бути не менше 8 символів'),
  role: z.enum(['admin', 'operator', 'manager', 'viewer']),
});

type CreateUserValues = z.infer<typeof createUserSchema>;

const editUserSchema = z.object({
  email: z.email({ message: 'Некоректний email' }),
  name: z.string().min(1, 'Вкажіть ім’я'),
  password: z
    .string()
    .optional()
    .refine((v) => !v || v.length >= 8, 'Пароль має бути не менше 8 символів'),
  role: z.enum(['admin', 'operator', 'manager', 'viewer']),
});

type EditUserValues = z.infer<typeof editUserSchema>;

const ROLES: UserRole[] = ['admin', 'operator', 'manager', 'viewer'];

function extractApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { error?: string; details?: Array<{ msg?: string; loc?: string }> }
      | undefined;
    if (data?.details?.length) {
      return data.details.map((d) => d.msg).filter(Boolean).join('; ');
    }
    if (data?.error) return data.error;
  }
  return 'Сталася помилка';
}

export function UsersPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { hasRole } = useAuthStore();
  const isAdmin = hasRole(['admin']);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [deactivatingUser, setDeactivatingUser] = useState<User | null>(null);
  const [hardDeleteDialogOpen, setHardDeleteDialogOpen] = useState(false);
  const [hardDeletingUser, setHardDeletingUser] = useState<User | null>(null);

  // Create form
  const createForm = useForm<CreateUserValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: {
      email: '',
      name: '',
      password: '',
      role: 'operator',
    },
  });

  // Edit form
  const editForm = useForm<EditUserValues>({
    resolver: zodResolver(editUserSchema),
    defaultValues: {
      email: '',
      name: '',
      password: '',
      role: 'operator',
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<User>>(
        '/api/users?per_page=50',
      );
      return response.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: CreateUserValues) => {
      const response = await apiClient.post('/api/users', values);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      showSuccess(t('users.form.create'));
      setCreateDialogOpen(false);
      createForm.reset();
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const editMutation = useMutation({
    mutationFn: async (values: EditUserValues & { id: string }) => {
      const { id, ...body } = values;
      const response = await apiClient.patch(`/api/users/${id}`, body);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      showSuccess(t('common.save'));
      setEditDialogOpen(false);
      setEditingUser(null);
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const deactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      const response = await apiClient.delete(`/api/users/${userId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      showSuccess(t('users.deactivate.confirm'));
      setDeactivateDialogOpen(false);
      setDeactivatingUser(null);
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const reactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      const response = await apiClient.post(`/api/users/${userId}/reactivate`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      showSuccess('Користувача активовано');
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const hardDeleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      const response = await apiClient.delete(`/api/users/${userId}/permanent`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      showSuccess('Користувача видалено назавжди');
      setHardDeleteDialogOpen(false);
      setHardDeletingUser(null);
    },
    onError: (err) => showError(extractApiError(err)),
  });

  const handleOpenCreate = () => {
    createForm.reset({
      email: '',
      name: '',
      password: '',
      role: 'operator',
    });
    setCreateDialogOpen(true);
  };

  const handleOpenEdit = (user: User) => {
    setEditingUser(user);
    editForm.reset({
      email: user.email,
      name: user.name,
      password: '',
      role: user.role,
    });
    setEditDialogOpen(true);
  };

  const handleOpenDeactivate = (user: User) => {
    setDeactivatingUser(user);
    setDeactivateDialogOpen(true);
  };

  const onCreateSubmit = (values: CreateUserValues) => {
    createMutation.mutate(values);
  };

  const onEditSubmit = (values: EditUserValues) => {
    if (!editingUser) return;
    editMutation.mutate({ ...values, id: editingUser.id });
  };

  const onDeactivateConfirm = () => {
    if (!deactivatingUser) return;
    deactivateMutation.mutate(deactivatingUser.id);
  };

  const createRoleValue = createForm.watch('role');
  const editRoleValue = editForm.watch('role');

  return (
    <div>
      <PageHeader title={t('users.title')}>
        {isAdmin && (
          <Button onClick={handleOpenCreate}>
            <Plus className="mr-2 h-4 w-4" />
            {t('users.invite')}
          </Button>
        )}
      </PageHeader>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : data && data.data.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('users.table.name')}</TableHead>
              <TableHead>{t('users.table.email')}</TableHead>
              <TableHead>{t('users.table.role')}</TableHead>
              <TableHead>{t('users.table.status')}</TableHead>
              <TableHead>{t('users.table.created')}</TableHead>
              {isAdmin && (
                <TableHead className="text-right">
                  {t('users.table.actions')}
                </TableHead>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.data.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <Badge variant="secondary">
                    {t(`users.roles.${user.role}`)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={user.is_active ? 'default' : 'destructive'}
                  >
                    {user.is_active
                      ? t('users.status.active')
                      : t('users.status.inactive')}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(user.created_at)}
                </TableCell>
                {isAdmin && (
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        title="Редагувати"
                        onClick={() => handleOpenEdit(user)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {user.is_active ? (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          title="Деактивувати"
                          onClick={() => handleOpenDeactivate(user)}
                        >
                          <UserMinus className="h-4 w-4" />
                        </Button>
                      ) : (
                        <>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            title="Активувати"
                            onClick={() => reactivateMutation.mutate(user.id)}
                          >
                            <UserCheck className="h-4 w-4 text-success" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            title="Видалити назавжди"
                            onClick={() => {
                              setHardDeletingUser(user);
                              setHardDeleteDialogOpen(true);
                            }}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyState
          icon={Users}
          title={t('users.empty.title')}
          action={
            isAdmin
              ? { label: t('users.empty.action'), onClick: handleOpenCreate }
              : undefined
          }
        />
      )}

      {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('users.form.create_title')}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={createForm.handleSubmit(onCreateSubmit)}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label>{t('users.form.email')}</Label>
              <Input
                type="email"
                {...createForm.register('email')}
                aria-invalid={!!createForm.formState.errors.email}
              />
              {createForm.formState.errors.email && (
                <p className="text-sm text-destructive">
                  {createForm.formState.errors.email.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('users.form.name')}</Label>
              <Input
                {...createForm.register('name')}
                aria-invalid={!!createForm.formState.errors.name}
              />
              {createForm.formState.errors.name && (
                <p className="text-sm text-destructive">
                  {createForm.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('users.form.password')}</Label>
              <Input
                type="password"
                {...createForm.register('password')}
                aria-invalid={!!createForm.formState.errors.password}
              />
              {createForm.formState.errors.password ? (
                <p className="text-sm text-destructive">
                  {createForm.formState.errors.password.message}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Мінімум 8 символів
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('users.form.role')}</Label>
              <Select
                value={createRoleValue}
                onValueChange={(val) =>
                  createForm.setValue(
                    'role',
                    (val ?? 'operator') as UserRole,
                  )
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue>
                    {t(`users.roles.${createRoleValue}`)}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {t(`users.roles.${role}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>
                {t('common.cancel')}
              </DialogClose>
              <Button type="submit" disabled={createMutation.isPending}>
                {t('users.form.create')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('users.form.edit_title')}</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={editForm.handleSubmit(onEditSubmit)}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <Label>{t('users.form.email')}</Label>
              <Input
                type="email"
                {...editForm.register('email')}
                aria-invalid={!!editForm.formState.errors.email}
              />
              {editForm.formState.errors.email && (
                <p className="text-sm text-destructive">
                  {editForm.formState.errors.email.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('users.form.name')}</Label>
              <Input
                {...editForm.register('name')}
                aria-invalid={!!editForm.formState.errors.name}
              />
              {editForm.formState.errors.name && (
                <p className="text-sm text-destructive">
                  {editForm.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('users.form.password')}</Label>
              <Input
                type="password"
                placeholder={t('users.form.password_placeholder')}
                {...editForm.register('password')}
                aria-invalid={!!editForm.formState.errors.password}
              />
              {editForm.formState.errors.password ? (
                <p className="text-sm text-destructive">
                  {editForm.formState.errors.password.message}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Залиш порожнім, щоб не змінювати. Мінімум 8 символів.
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label>{t('users.form.role')}</Label>
              <Select
                value={editRoleValue}
                onValueChange={(val) =>
                  editForm.setValue(
                    'role',
                    (val ?? 'operator') as UserRole,
                  )
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue>
                    {t(`users.roles.${editRoleValue}`)}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {t(`users.roles.${role}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>
                {t('common.cancel')}
              </DialogClose>
              <Button type="submit" disabled={editMutation.isPending}>
                {t('common.save')}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Deactivate Confirmation */}
      <AlertDialog
        open={deactivateDialogOpen}
        onOpenChange={setDeactivateDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('users.deactivate.title', { name: deactivatingUser?.name })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('users.deactivate.description')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={onDeactivateConfirm}
              disabled={deactivateMutation.isPending}
            >
              {t('users.deactivate.confirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Hard delete confirmation */}
      <AlertDialog
        open={hardDeleteDialogOpen}
        onOpenChange={setHardDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Видалити користувача {hardDeletingUser?.name} назавжди?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Це повне видалення з бази без можливості відновити. Якщо хочете
              лише тимчасово заблокувати — використайте Деактивацію.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() =>
                hardDeletingUser && hardDeleteMutation.mutate(hardDeletingUser.id)
              }
              disabled={hardDeleteMutation.isPending}
            >
              Видалити назавжди
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
