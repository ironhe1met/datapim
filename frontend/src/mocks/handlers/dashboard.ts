import { http, HttpResponse, delay } from 'msw';
import dashboardData from '@/mocks/data/dashboard.json';

export const dashboardHandlers = [
  http.get('*/api/dashboard/stats', async () => {
    await delay(400);
    return HttpResponse.json(dashboardData);
  }),
];
