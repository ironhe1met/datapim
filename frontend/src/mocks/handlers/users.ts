import { http, HttpResponse, delay } from 'msw';
import usersData from '@/mocks/data/users.json';
import type { PaginatedResponse, User } from '@/types/api';

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

const users: MockUser[] = [...(usersData as MockUser[])];
let nextId = users.length + 1;

function toUser(u: MockUser): User {
  return {
    id: u.id,
    email: u.email,
    name: u.name,
    role: u.role as User['role'],
    is_active: u.is_active,
    theme: u.theme,
    created_at: u.created_at,
  };
}

export const userHandlers = [
  http.get('*/api/users', async ({ request }) => {
    await delay(300);
    const url = new URL(request.url);
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1'));
    const perPage = Math.min(
      100,
      Math.max(1, Number(url.searchParams.get('per_page') ?? '10')),
    );

    const sorted = [...users].sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

    const total = sorted.length;
    const lastPage = Math.max(1, Math.ceil(total / perPage));
    const start = (page - 1) * perPage;
    const pageItems = sorted.slice(start, start + perPage);

    const response: PaginatedResponse<User> = {
      data: pageItems.map(toUser),
      meta: {
        total,
        page,
        per_page: perPage,
        last_page: lastPage,
      },
    };

    return HttpResponse.json(response);
  }),

  http.post('*/api/users', async ({ request }) => {
    await delay(300);
    const body = (await request.json()) as {
      email: string;
      name: string;
      password: string;
      role: string;
    };

    const newUser: MockUser = {
      id: nextId++,
      email: body.email,
      name: body.name,
      role: body.role,
      is_active: true,
      theme: 'light',
      created_at: new Date().toISOString(),
      password: body.password,
    };

    users.push(newUser);

    return HttpResponse.json(toUser(newUser), { status: 201 });
  }),

  http.patch('*/api/users/:id', async ({ params, request }) => {
    await delay(300);
    const id = Number(params.id);
    const user = users.find((u) => u.id === id);

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

    const body = (await request.json()) as Partial<{
      email: string;
      name: string;
      password: string;
      role: string;
    }>;

    if (body.email !== undefined) user.email = body.email;
    if (body.name !== undefined) user.name = body.name;
    if (body.role !== undefined) user.role = body.role;
    if (body.password !== undefined && body.password) user.password = body.password;

    return HttpResponse.json(toUser(user));
  }),

  http.delete('*/api/users/:id', async ({ params }) => {
    await delay(300);
    const id = Number(params.id);
    const user = users.find((u) => u.id === id);

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

    user.is_active = false;

    return HttpResponse.json(toUser(user));
  }),
];
