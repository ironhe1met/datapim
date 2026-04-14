import { http, HttpResponse, delay } from 'msw';

export const settingsHandlers = [
  http.get('*/api/export/settings', async () => {
    await delay(200);
    return HttpResponse.json({
      products_url: '/export/products.xml',
      categories_url: '/export/categories.xml',
      products_count: 11620,
      categories_count: 781,
    });
  }),

  http.patch('*/api/auth/me', async ({ request }) => {
    await delay(300);
    const body = (await request.json()) as {
      name?: string;
      password?: string;
      current_password?: string;
    };

    if (body.password && !body.current_password) {
      return HttpResponse.json(
        {
          error: 'Current password is required',
          code: 'VALIDATION_ERROR',
          request_id: crypto.randomUUID(),
        },
        { status: 422 },
      );
    }

    return HttpResponse.json({
      id: 1,
      email: 'admin@ironhelmet.com.ua',
      name: body.name ?? 'Eugene',
      role: 'admin',
      is_active: true,
      theme: 'light',
      created_at: '2024-01-15T10:00:00Z',
    });
  }),
];
