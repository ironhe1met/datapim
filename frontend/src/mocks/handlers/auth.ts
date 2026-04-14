import { http, HttpResponse, delay } from 'msw';
import usersData from '@/mocks/data/users.json';

interface MockUser {
  id: number;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  theme: string;
  created_at: string;
  password: string;
}

const users = usersData as MockUser[];

let currentUserId: number | null = null;

function generateToken(userId: number): string {
  return `mock-jwt-token-${userId}-${Date.now()}`;
}

export const authHandlers = [
  http.post('*/api/auth/login', async ({ request }) => {
    await delay(300);
    const body = (await request.json()) as { email: string; password: string };
    const user = users.find(
      (u) => u.email === body.email,
    );

    if (!user) {
      return HttpResponse.json(
        {
          error: 'Невірний email або пароль',
          code: 'INVALID_CREDENTIALS',
          request_id: crypto.randomUUID(),
        },
        { status: 401 },
      );
    }

    currentUserId = user.id;
    const { password: _, ...userWithoutPassword } = user;

    return HttpResponse.json({
      access_token: generateToken(user.id),
      refresh_token: generateToken(user.id),
      user: userWithoutPassword,
    });
  }),

  http.post('*/api/auth/refresh', async () => {
    await delay(100);
    if (currentUserId === null) {
      return HttpResponse.json(
        {
          error: 'Unauthorized',
          code: 'UNAUTHORIZED',
          request_id: crypto.randomUUID(),
        },
        { status: 401 },
      );
    }

    return HttpResponse.json({
      access_token: generateToken(currentUserId),
      refresh_token: generateToken(currentUserId),
    });
  }),

  http.get('*/api/auth/me', async () => {
    await delay(100);
    if (currentUserId === null) {
      return HttpResponse.json(
        {
          error: 'Unauthorized',
          code: 'UNAUTHORIZED',
          request_id: crypto.randomUUID(),
        },
        { status: 401 },
      );
    }

    const user = users.find((u) => u.id === currentUserId);
    if (!user) {
      return HttpResponse.json(
        {
          error: 'User not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    const { password: _, ...userWithoutPassword } = user;
    return HttpResponse.json(userWithoutPassword);
  }),

  http.post('*/api/auth/logout', async () => {
    await delay(100);
    currentUserId = null;
    return HttpResponse.json({ message: 'OK' });
  }),
];
