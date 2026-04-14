import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
      <h1 className="text-8xl font-bold text-muted-foreground">
        {t('error.404.title')}
      </h1>
      <p className="text-xl text-muted-foreground">{t('error.404.text')}</p>
      <Button onClick={() => navigate('/')}>{t('common.back_home')}</Button>
    </div>
  );
}
