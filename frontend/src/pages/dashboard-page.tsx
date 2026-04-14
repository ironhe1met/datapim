import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Package, ShoppingCart, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient } from '@/lib/api-client';
import type { DashboardStats } from '@/types/api';

export function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const response = await apiClient.get<DashboardStats>(
        '/api/dashboard/stats',
      );
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <div>
        <h1 className="mb-6 text-2xl font-bold">{t('dashboard.title')}</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const statCards = [
    {
      label: t('dashboard.stats.total'),
      value: stats?.products_total ?? 0,
      icon: Package,
      color: 'text-primary',
      onClick: () => navigate('/products'),
    },
    {
      label: t('dashboard.stats.in_stock'),
      value: stats?.products_in_stock ?? 0,
      icon: ShoppingCart,
      color: 'text-success',
      onClick: () => navigate('/products?in_stock=true'),
    },
    {
      label: t('dashboard.stats.enriched'),
      value: stats?.products_enriched ?? 0,
      icon: Sparkles,
      color: 'text-warning',
      onClick: () => navigate('/products?enrichment_status=full'),
    },
  ];

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">{t('dashboard.title')}</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card
            key={card.label}
            className="cursor-pointer transition-shadow hover:shadow-md"
            onClick={card.onClick}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <card.icon className={`h-4 w-4 ${card.color}`} />
                {card.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">
                {card.value.toLocaleString('uk-UA')}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
