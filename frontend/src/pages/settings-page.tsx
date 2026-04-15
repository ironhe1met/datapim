import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { BulkUpdateTool } from '@/components/bulk-update-tool';
import { PageHeader } from '@/components/page-header';
import { apiClient } from '@/lib/api-client';
import { env } from '@/lib/env';
import { showSuccess } from '@/lib/toast';
import { useAuthStore } from '@/stores/auth-store';

function absoluteUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${env.VITE_API_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}

type TextProvider = 'anthropic' | 'openai' | 'google';
type ImageProvider = 'flux_pro' | 'dall_e_3' | 'imagen_3';

const TEXT_PROVIDERS: { value: TextProvider; label: string }[] = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'google', label: 'Google' },
];

const IMAGE_PROVIDERS: { value: ImageProvider; label: string }[] = [
  { value: 'flux_pro', label: 'Flux Pro' },
  { value: 'dall_e_3', label: 'DALL-E 3' },
  { value: 'imagen_3', label: 'Imagen 3' },
];

interface ExportSettings {
  products_url: string;
  categories_url: string;
  products_count: number;
  categories_count: number;
}

const profileSchema = z
  .object({
    name: z.string().min(1),
    new_password: z.string().optional(),
    current_password: z.string().optional(),
  })
  .refine(
    (data) => {
      if (data.new_password && !data.current_password) return false;
      return true;
    },
    {
      path: ['current_password'],
      message: 'Required when changing password',
    },
  );

type ProfileValues = z.infer<typeof profileSchema>;

export function SettingsPage() {
  const { t } = useTranslation();
  const { user, hasRole } = useAuthStore();
  const isAdmin = hasRole(['admin']);

  // AI Providers state
  const [textProvider, setTextProvider] = useState<TextProvider>('anthropic');
  const [imageProvider, setImageProvider] = useState<ImageProvider>('flux_pro');

  // Export settings
  const { data: exportSettings } = useQuery({
    queryKey: ['export-settings'],
    queryFn: async () => {
      const response = await apiClient.get<ExportSettings>(
        '/api/export/settings',
      );
      return response.data;
    },
  });

  // Profile form
  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: user?.name ?? '',
      new_password: '',
      current_password: '',
    },
  });

  const profileMutation = useMutation({
    mutationFn: async (values: ProfileValues) => {
      const body: Record<string, string> = { name: values.name };
      if (values.new_password) {
        body.password = values.new_password;
        body.current_password = values.current_password ?? '';
      }
      const response = await apiClient.patch('/api/auth/me', body);
      return response.data;
    },
    onSuccess: () => {
      showSuccess(t('settings.profile.save'));
      profileForm.reset({
        name: profileForm.getValues('name'),
        new_password: '',
        current_password: '',
      });
    },
  });

  const handleSaveAi = () => {
    // In a real app, this would save to the backend
    showSuccess(t('settings.ai.save'));
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    showSuccess(t('settings.export.copied'));
  };

  const onProfileSubmit = (values: ProfileValues) => {
    profileMutation.mutate(values);
  };

  const textProviderLabel =
    TEXT_PROVIDERS.find((p) => p.value === textProvider)?.label ?? textProvider;
  const imageProviderLabel =
    IMAGE_PROVIDERS.find((p) => p.value === imageProvider)?.label ??
    imageProvider;

  return (
    <div>
      <PageHeader title={t('settings.title')} />

      <div className="space-y-6">
        {/* AI Providers */}
        <Card>
          <CardHeader>
            <CardTitle>{t('settings.ai.title')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('settings.ai.text_provider')}</Label>
              <Select
                value={textProvider}
                onValueChange={(val) =>
                  setTextProvider((val ?? 'anthropic') as TextProvider)
                }
              >
                <SelectTrigger className="w-64">
                  <SelectValue>{textProviderLabel}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {TEXT_PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>{t('settings.ai.image_provider')}</Label>
              <Select
                value={imageProvider}
                onValueChange={(val) =>
                  setImageProvider((val ?? 'flux_pro') as ImageProvider)
                }
              >
                <SelectTrigger className="w-64">
                  <SelectValue>{imageProviderLabel}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {IMAGE_PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <p className="text-sm text-muted-foreground">
              {t('settings.ai.fallback_info')}
            </p>
            <Button onClick={handleSaveAi}>{t('settings.ai.save')}</Button>
          </CardContent>
        </Card>

        {/* XML Export */}
        <Card>
          <CardHeader>
            <CardTitle>{t('settings.export.title')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label>{t('settings.export.products_url')}</Label>
              <div className="flex items-center gap-2">
                <Input
                  value={absoluteUrl(exportSettings?.products_url ?? '/export/products.xml')}
                  readOnly
                  disabled
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() =>
                    handleCopy(
                      absoluteUrl(exportSettings?.products_url ?? '/export/products.xml'),
                    )
                  }
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>{t('settings.export.categories_url')}</Label>
              <div className="flex items-center gap-2">
                <Input
                  value={absoluteUrl(
                    exportSettings?.categories_url ?? '/export/categories.xml',
                  )}
                  readOnly
                  disabled
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() =>
                    handleCopy(
                      absoluteUrl(
                        exportSettings?.categories_url ?? '/export/categories.xml',
                      ),
                    )
                  }
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            {exportSettings && (
              <p className="text-sm text-muted-foreground">
                {t('settings.export.stats', {
                  products: exportSettings.products_count.toLocaleString(
                    'uk-UA',
                  ),
                  categories: exportSettings.categories_count.toLocaleString(
                    'uk-UA',
                  ),
                })}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Bulk Update — admin only, hidden from non-admins */}
        {isAdmin && <BulkUpdateTool />}

        {/* Profile */}
        <Card>
          <CardHeader>
            <CardTitle>{t('settings.profile.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={profileForm.handleSubmit(onProfileSubmit)}
              className="space-y-4"
            >
              <div className="space-y-1.5">
                <Label>{t('settings.profile.name')}</Label>
                <Input
                  {...profileForm.register('name')}
                  aria-invalid={!!profileForm.formState.errors.name}
                />
                {profileForm.formState.errors.name && (
                  <p className="text-sm text-destructive">
                    {profileForm.formState.errors.name.message}
                  </p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label>{t('settings.profile.email')}</Label>
                <Input value={user?.email ?? ''} readOnly disabled />
              </div>
              <div className="space-y-1.5">
                <Label>{t('settings.profile.new_password')}</Label>
                <Input
                  type="password"
                  {...profileForm.register('new_password')}
                />
              </div>
              <div className="space-y-1.5">
                <Label>{t('settings.profile.current_password')}</Label>
                <Input
                  type="password"
                  {...profileForm.register('current_password')}
                  aria-invalid={
                    !!profileForm.formState.errors.current_password
                  }
                />
                {profileForm.formState.errors.current_password && (
                  <p className="text-sm text-destructive">
                    {profileForm.formState.errors.current_password.message}
                  </p>
                )}
              </div>
              <Button
                type="submit"
                disabled={profileMutation.isPending}
              >
                {t('settings.profile.save')}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
