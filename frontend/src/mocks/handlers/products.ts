import { http, HttpResponse, delay } from 'msw';
import productsData from '@/mocks/data/products.json';
import categoriesData from '@/mocks/data/categories.json';
import type {
  Category,
  ProductListItem,
  Product,
  EnrichmentStatus,
  PaginatedResponse,
} from '@/types/api';

interface MockProduct {
  id: number;
  internal_code: string;
  sku: string;
  buf_name: string | null;
  custom_name: string | null;
  buf_brand: string | null;
  custom_brand: string | null;
  buf_price: number | null;
  buf_currency: string | null;
  buf_in_stock: boolean;
  buf_quantity: number | null;
  buf_country: string | null;
  custom_country: string | null;
  uktzed: string;
  is_active: boolean;
  description: string | null;
  seo_title: string | null;
  seo_description: string | null;
  enrichment_status: EnrichmentStatus;
  has_pending_review: boolean;
  category_id: number;
  primary_image: { id: number; file_path: string } | null;
  created_at: string;
  updated_at: string;
}

const products: MockProduct[] = productsData as MockProduct[];
const categories: Category[] = categoriesData as Category[];

function findCategory(id: number): Category | undefined {
  return categories.find((c) => c.id === id);
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

function resolveName(p: MockProduct): string {
  return p.custom_name ?? p.buf_name ?? '';
}

function resolveBrand(p: MockProduct): string | null {
  return p.custom_brand ?? p.buf_brand;
}

function toListItem(p: MockProduct): ProductListItem {
  const cat = findCategory(p.category_id);
  return {
    id: p.id,
    internal_code: p.internal_code,
    sku: p.sku,
    name: resolveName(p),
    brand: resolveBrand(p),
    price: p.buf_price,
    currency: p.buf_currency,
    in_stock: p.buf_in_stock,
    category: cat ? { id: cat.id, name: cat.name } : null,
    primary_image: p.primary_image,
    enrichment_status: p.enrichment_status,
    has_pending_review: p.has_pending_review,
  };
}

// In-memory attributes storage per product
const productAttributes: Map<number, Array<{ id: number; key: string; value: string; source: 'manual' | 'ai'; sort_order: number }>> = new Map();
let nextAttributeId = 1000;

function seedAttributesIfNeeded(p: MockProduct) {
  if (productAttributes.has(p.id)) return;
  const attrs: Array<{ id: number; key: string; value: string; source: 'manual' | 'ai'; sort_order: number }> = [];
  if (p.enrichment_status !== 'none') {
    const pairs: Array<[string, string]> =
      p.category_id <= 5 ? [['Потужність', '780 Вт'], ['Напруга', '220 В'], ['Вага', '2.4 кг']] :
      p.category_id <= 9 ? [['Об\'єм двигуна', '50.2 см³'], ['Вага', '5.6 кг']] :
      p.category_id <= 12 ? [['Діапазон струму', '10-250 А'], ['ККД', '85%']] :
      p.category_id <= 15 ? [['Продуктивність', '170 л/хв'], ['Тиск', '8 бар']] :
      [];
    for (const [key, value] of pairs) {
      attrs.push({ id: nextAttributeId++, key, value, source: 'manual', sort_order: attrs.length });
    }
  }
  productAttributes.set(p.id, attrs);
}

function toDetail(p: MockProduct): Product {
  const cat = findCategory(p.category_id);
  const breadcrumb = buildBreadcrumb(p.category_id);
  seedAttributesIfNeeded(p);
  const mockAttributes = productAttributes.get(p.id) ?? [];

  return {
    id: p.id,
    internal_code: p.internal_code,
    sku: p.sku,
    buf_name: p.buf_name,
    custom_name: p.custom_name,
    buf_brand: p.buf_brand,
    custom_brand: p.custom_brand,
    buf_country: p.buf_country,
    custom_country: p.custom_country,
    buf_price: p.buf_price,
    buf_currency: p.buf_currency,
    buf_in_stock: p.buf_in_stock,
    buf_quantity: p.buf_quantity,
    uktzed: p.uktzed,
    category: cat
      ? { ...cat, children: [], breadcrumb } as Category & { breadcrumb: Category[] }
      : null,
    primary_image: p.primary_image,
    enrichment_status: p.enrichment_status,
    has_pending_review: p.has_pending_review,
    name: resolveName(p),
    brand: resolveBrand(p),
    description: p.description,
    seo_title: p.seo_title,
    seo_description: p.seo_description,
    images: p.primary_image ? [p.primary_image] : [],
    attributes: mockAttributes,
    created_at: p.created_at,
    updated_at: p.updated_at,
  };
}

function getCategoryDescendantIds(parentId: number): number[] {
  const ids = [parentId];
  const children = categories.filter((c) => c.parent_id === parentId);
  for (const child of children) {
    ids.push(...getCategoryDescendantIds(child.id));
  }
  return ids;
}

export const productHandlers = [
  http.get('*/api/products', async ({ request }) => {
    await delay(300);
    const url = new URL(request.url);
    const search = url.searchParams.get('search')?.toLowerCase() ?? '';
    const categoryId = url.searchParams.get('category_id');
    const inStock = url.searchParams.get('in_stock');
    const enrichmentStatus = url.searchParams.get('enrichment_status');
    const hasPendingReview = url.searchParams.get('has_pending_review');
    const sortBy = url.searchParams.get('sort_by') ?? 'created_at';
    const sortOrder = url.searchParams.get('sort_order') ?? 'desc';
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1'));
    const perPage = Math.min(
      100,
      Math.max(1, Number(url.searchParams.get('per_page') ?? '10')),
    );

    let filtered = [...products];

    if (search) {
      filtered = filtered.filter(
        (p) =>
          resolveName(p).toLowerCase().includes(search) ||
          p.sku.toLowerCase().includes(search) ||
          p.internal_code.toLowerCase().includes(search),
      );
    }

    if (categoryId) {
      const catId = Number(categoryId);
      const descendantIds = getCategoryDescendantIds(catId);
      filtered = filtered.filter((p) => descendantIds.includes(p.category_id));
    }

    if (inStock === 'true') {
      filtered = filtered.filter((p) => p.buf_in_stock);
    } else if (inStock === 'false') {
      filtered = filtered.filter((p) => !p.buf_in_stock);
    }

    if (
      enrichmentStatus &&
      ['none', 'partial', 'full'].includes(enrichmentStatus)
    ) {
      filtered = filtered.filter(
        (p) => p.enrichment_status === enrichmentStatus,
      );
    }

    if (hasPendingReview === 'true') {
      filtered = filtered.filter((p) => p.has_pending_review);
    }

    filtered.sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case 'name':
          cmp = resolveName(a).localeCompare(resolveName(b), 'uk');
          break;
        case 'price':
          cmp = (a.buf_price ?? 0) - (b.buf_price ?? 0);
          break;
        case 'sku':
          cmp = a.sku.localeCompare(b.sku);
          break;
        default:
          cmp =
            new Date(a.created_at).getTime() -
            new Date(b.created_at).getTime();
      }
      return sortOrder === 'asc' ? cmp : -cmp;
    });

    const total = filtered.length;
    const lastPage = Math.max(1, Math.ceil(total / perPage));
    const start = (page - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);

    const response: PaginatedResponse<ProductListItem> = {
      data: pageItems.map(toListItem),
      meta: {
        total,
        page,
        per_page: perPage,
        last_page: lastPage,
      },
    };

    return HttpResponse.json(response);
  }),

  http.get('*/api/products/:id', async ({ params }) => {
    await delay(250);
    const id = Number(params.id);
    const product = products.find((p) => p.id === id);

    if (!product) {
      return HttpResponse.json(
        {
          error: 'Product not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    return HttpResponse.json(toDetail(product));
  }),

  http.patch('*/api/products/:id', async ({ params, request }) => {
    await delay(300);
    const id = Number(params.id);
    const productIndex = products.findIndex((p) => p.id === id);

    if (productIndex === -1) {
      return HttpResponse.json(
        {
          error: 'Product not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    const body = (await request.json()) as Record<string, unknown>;
    const product = products[productIndex];

    if (body.custom_name !== undefined)
      product.custom_name = body.custom_name as string | null;
    if (body.custom_brand !== undefined)
      product.custom_brand = body.custom_brand as string | null;
    if (body.custom_country !== undefined)
      product.custom_country = body.custom_country as string | null;
    if (body.custom_category_id !== undefined && body.custom_category_id !== null) {
      product.category_id = Number(body.custom_category_id);
    }
    if (body.description !== undefined)
      product.description = body.description as string | null;
    if (body.seo_title !== undefined)
      product.seo_title = body.seo_title as string | null;
    if (body.seo_description !== undefined)
      product.seo_description = body.seo_description as string | null;

    product.updated_at = new Date().toISOString();

    return HttpResponse.json(toDetail(product));
  }),

  http.post('*/api/products/:id/reset-field', async ({ params, request }) => {
    await delay(200);
    const id = Number(params.id);
    const productIndex = products.findIndex((p) => p.id === id);

    if (productIndex === -1) {
      return HttpResponse.json(
        {
          error: 'Product not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    const body = (await request.json()) as { field: string };
    const product = products[productIndex];

    switch (body.field) {
      case 'custom_name':
        product.custom_name = null;
        break;
      case 'custom_brand':
        product.custom_brand = null;
        break;
      case 'custom_country':
        product.custom_country = null;
        break;
      case 'description':
        product.description = null;
        break;
      case 'seo_title':
        product.seo_title = null;
        break;
      case 'seo_description':
        product.seo_description = null;
        break;
    }

    product.updated_at = new Date().toISOString();

    return HttpResponse.json(toDetail(product));
  }),

  // --- Attributes CRUD ---

  http.get('*/api/products/:id/attributes', async ({ params }) => {
    await delay(150);
    const id = Number(params.id);
    const product = products.find((p) => p.id === id);
    if (!product) {
      return HttpResponse.json({ error: 'Not found', code: 'NOT_FOUND', request_id: crypto.randomUUID() }, { status: 404 });
    }
    seedAttributesIfNeeded(product);
    return HttpResponse.json({ data: productAttributes.get(id) ?? [] });
  }),

  http.post('*/api/products/:id/attributes', async ({ params, request }) => {
    await delay(200);
    const id = Number(params.id);
    const product = products.find((p) => p.id === id);
    if (!product) {
      return HttpResponse.json({ error: 'Not found', code: 'NOT_FOUND', request_id: crypto.randomUUID() }, { status: 404 });
    }
    seedAttributesIfNeeded(product);
    const attrs = productAttributes.get(id)!;
    const body = (await request.json()) as { key: string; value: string };

    if (attrs.some((a) => a.key.toLowerCase() === body.key.toLowerCase())) {
      return HttpResponse.json(
        { error: 'Атрибут з таким ключем вже існує', code: 'DUPLICATE_KEY', request_id: crypto.randomUUID() },
        { status: 409 },
      );
    }

    const newAttr = {
      id: nextAttributeId++,
      key: body.key,
      value: body.value,
      source: 'manual' as const,
      sort_order: attrs.length,
    };
    attrs.push(newAttr);
    return HttpResponse.json(newAttr, { status: 201 });
  }),

  http.patch('*/api/products/:productId/attributes/:attrId', async ({ params, request }) => {
    await delay(200);
    const productId = Number(params.productId);
    const attrId = Number(params.attrId);
    const attrs = productAttributes.get(productId);
    const attr = attrs?.find((a) => a.id === attrId);
    if (!attrs || !attr) {
      return HttpResponse.json({ error: 'Not found', code: 'NOT_FOUND', request_id: crypto.randomUUID() }, { status: 404 });
    }
    const body = (await request.json()) as { key?: string; value?: string };
    if (body.key !== undefined) attr.key = body.key;
    if (body.value !== undefined) attr.value = body.value;
    return HttpResponse.json(attr);
  }),

  http.delete('*/api/products/:productId/attributes/:attrId', async ({ params }) => {
    await delay(150);
    const productId = Number(params.productId);
    const attrId = Number(params.attrId);
    const attrs = productAttributes.get(productId);
    if (!attrs) {
      return HttpResponse.json({ error: 'Not found', code: 'NOT_FOUND', request_id: crypto.randomUUID() }, { status: 404 });
    }
    const idx = attrs.findIndex((a) => a.id === attrId);
    if (idx === -1) {
      return HttpResponse.json({ error: 'Not found', code: 'NOT_FOUND', request_id: crypto.randomUUID() }, { status: 404 });
    }
    attrs.splice(idx, 1);
    return HttpResponse.json({ message: 'Deleted' });
  }),
];
