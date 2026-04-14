import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';

export function ErrorPage() {
  const { t } = useTranslation();

  const handleRetry = () => {
    window.location.reload();
  };

  const handleHome = () => {
    window.location.href = '/';
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
      <h1 className="text-8xl font-bold text-muted-foreground">
        {t('error.500.title')}
      </h1>
      <p className="text-xl text-muted-foreground">{t('error.500.text')}</p>
      <div className="flex gap-2">
        <Button onClick={handleRetry}>{t('common.retry')}</Button>
        <Button variant="ghost" onClick={handleHome}>
          {t('common.back_home')}
        </Button>
      </div>
    </div>
  );
}
