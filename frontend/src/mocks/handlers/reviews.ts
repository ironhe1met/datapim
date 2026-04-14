import { http, HttpResponse, delay } from 'msw';
import reviewsData from '@/mocks/data/reviews.json';
import productsData from '@/mocks/data/products.json';
import type {
  ReviewStatus,
  ReviewType,
  ReviewListItem,
  ReviewDetail,
  ReviewDiffField,
  PaginatedResponse,
} from '@/types/api';

interface MockReview {
  id: number;
  product_id: number;
  type: string;
  provider: string;
  status: string;
  output_data: Record<string, string>;
  cost_usd: number;
  duration_ms: number;
  created_at: string;
}

interface MockProduct {
  id: number;
  buf_name: string | null;
  custom_name: string | null;
  description: string | null;
  seo_title: string | null;
  seo_description: string | null;
}

const reviews: MockReview[] = reviewsData as unknown as MockReview[];
const products: MockProduct[] = productsData as unknown as MockProduct[];

function getProductName(productId: number): string {
  const p = products.find((pr) => pr.id === productId);
  if (!p) return `Product #${productId}`;
  return p.custom_name ?? p.buf_name ?? `Product #${productId}`;
}

function toListItem(r: MockReview): ReviewListItem {
  return {
    id: r.id,
    product: { id: r.product_id, name: getProductName(r.product_id) },
    type: r.type as ReviewType,
    provider: r.provider,
    status: r.status as ReviewStatus,
    created_at: r.created_at,
  };
}

function toDetail(r: MockReview): ReviewDetail {
  const p = products.find((pr) => pr.id === r.product_id);

  const currentData: Record<string, string | null> = {
    description: p?.description ?? null,
    seo_title: p?.seo_title ?? null,
    seo_description: p?.seo_description ?? null,
  };

  const diff: ReviewDiffField[] = [];
  for (const [field, proposed] of Object.entries(r.output_data)) {
    if (field === 'image_url') continue;
    if (field === 'attributes') continue;
    const current = currentData[field] ?? null;
    if (current !== proposed) {
      diff.push({ field, current, proposed });
    }
  }

  const imageUrl =
    r.type === 'image' ? (r.output_data.image_url ?? null) : null;

  return {
    id: r.id,
    product: { id: r.product_id, name: getProductName(r.product_id) },
    type: r.type as ReviewType,
    provider: r.provider,
    status: r.status as ReviewStatus,
    output_data: r.output_data,
    current_data: currentData,
    diff,
    image_url: imageUrl,
    cost_usd: r.cost_usd,
    duration_ms: r.duration_ms,
    created_at: r.created_at,
    ai_task_id: r.id * 10,
  };
}

export const reviewHandlers = [
  http.get('*/api/reviews', async ({ request }) => {
    await delay(300);
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1'));
    const perPage = Math.min(
      100,
      Math.max(1, Number(url.searchParams.get('per_page') ?? '10')),
    );

    let filtered = [...reviews];

    if (status && status !== 'all') {
      filtered = filtered.filter((r) => r.status === status);
    }

    filtered.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );

    const total = filtered.length;
    const lastPage = Math.max(1, Math.ceil(total / perPage));
    const start = (page - 1) * perPage;
    const pageItems = filtered.slice(start, start + perPage);

    const response: PaginatedResponse<ReviewListItem> = {
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

  http.get('*/api/reviews/:id', async ({ params }) => {
    await delay(250);
    const id = Number(params.id);
    const review = reviews.find((r) => r.id === id);

    if (!review) {
      return HttpResponse.json(
        {
          error: 'Review not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    return HttpResponse.json(toDetail(review));
  }),

  http.post('*/api/reviews/:id/approve', async ({ params }) => {
    await delay(300);
    const id = Number(params.id);
    const review = reviews.find((r) => r.id === id);

    if (!review) {
      return HttpResponse.json(
        {
          error: 'Review not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    review.status = 'approved';
    return HttpResponse.json(toDetail(review));
  }),

  http.post('*/api/reviews/:id/reject', async ({ params }) => {
    await delay(300);
    const id = Number(params.id);
    const review = reviews.find((r) => r.id === id);

    if (!review) {
      return HttpResponse.json(
        {
          error: 'Review not found',
          code: 'NOT_FOUND',
          request_id: crypto.randomUUID(),
        },
        { status: 404 },
      );
    }

    review.status = 'rejected';
    return HttpResponse.json(toDetail(review));
  }),
];
