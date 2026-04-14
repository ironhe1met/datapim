import { http, HttpResponse, delay } from 'msw';
import categoriesData from '@/mocks/data/categories.json';
import type { Category } from '@/types/api';

interface MockCategory {
  id: number;
  external_id: string;
  name: string;
  parent_id: number | null;
  is_active: boolean;
  product_count: number;
}

const categories = categoriesData as Category[];

function buildTree(): Category[] {
  const roots = categories.filter((c) => c.parent_id === null);
  return roots.map((root) => ({
    ...root,
    children: categories.filter((c) => c.parent_id === root.id),
  }));
}

function buildBreadcrumb(categoryId: number): Category[] {
  const trail: Category[] = [];
  let current = categories.find((c) => c.id === categoryId);
  while (current) {
    trail.unshift(current);
    current = current.parent_id
      ? categories.find((c) => c.id === current!.parent_id)
      : undefined;
  }
  return trail;
}

export const categoryHandlers = [
  http.get('*/api/categories', async ({ request }) => {
    await delay(200);
    const url = new URL(request.url);
    const tree = url.searchParams.get('tree');

    if (tree === 'true') {
      return HttpResponse.json(buildTree());
    }

    return HttpResponse.json(categories);
  }),

  http.post('*/api/categories', async ({ request }) => {
    await delay(200);
    const body = (await request.json()) as { name: string; parent_id: number | null };
    const newId = Math.max(...categories.map((c) => c.id as number)) + 1;
    const newCat: MockCategory = {
      id: newId,
      external_id: `NEW-${newId}`,
      name: body.name,
      parent_id: body.parent_id,
      is_active: true,
      product_count: 0,
    };
    categories.push(newCat as Category);
    return HttpResponse.json(newCat, { status: 201 });
  }),

  http.patch('*/api/categories/:id', async ({ params, request }) => {
    await delay(200);
    const id = Number(params.id);
    const body = (await request.json()) as { name?: string; parent_id?: number | null };
    const category = categories.find((c) => c.id === id);

    if (!category) {
      return HttpResponse.json(
        { error: 'Category not found', code: 'NOT_FOUND', request_id: crypto.randomUUID() },
        { status: 404 },
      );
    }

    if (body.name !== undefined) (category as MockCategory).name = body.name;
    if (body.parent_id !== undefined) (category as MockCategory).parent_id = body.parent_id;
    return HttpResponse.json(category);
  }),

  http.get('*/api/categories/:id', async ({ params }) => {
    await delay(200);
    const id = Number(params.id);
    const category = categories.find((c) => c.id === id);

    if (!category) {
      return HttpResponse.json(
        {
          error: 'Category not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    const children = categories.filter((c) => c.parent_id === id);
    const breadcrumb = buildBreadcrumb(id);

    return HttpResponse.json({
      ...category,
      children,
      breadcrumb,
    });
  }),
];
