export type UserRole = 'admin' | 'operator' | 'manager' | 'viewer';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  theme: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  user: User;
}

export type EnrichmentStatus = 'none' | 'partial' | 'full';

export interface Product {
  id: string;
  internal_code: string;
  sku: string;
  buf_name: string | null;
  custom_name: string | null;
  buf_brand: string | null;
  custom_brand: string | null;
  buf_country: string | null;
  custom_country: string | null;
  uktzed: string | null;
  buf_price: number | null;
  buf_currency: string | null;
  buf_in_stock: boolean;
  buf_quantity: number | null;
  category: Category | null;
  buf_category: Category | null;
  primary_image: ProductImage | null;
  enrichment_status: EnrichmentStatus;
  has_pending_review: boolean;
  name: string;
  brand: string | null;
  description: string | null;
  seo_title: string | null;
  seo_description: string | null;
  images: ProductImage[];
  attributes: ProductAttribute[];
  created_at: string;
  updated_at: string;
}

export interface ProductImage {
  id: string;
  file_path: string;
  is_primary?: boolean;
  sort_order?: number;
}

export interface ProductAttribute {
  id: string;
  key: string;
  value: string;
  source: 'manual' | 'ai';
  sort_order: number;
}

export interface ProductListItem {
  id: string;
  internal_code: string;
  sku: string;
  name: string;
  brand: string | null;
  price: number | null;
  currency: string | null;
  quantity: number | null;
  in_stock: boolean;
  category: { id: string; name: string } | null;
  primary_image: { id: string; file_path: string } | null;
  enrichment_status: EnrichmentStatus;
  has_pending_review: boolean;
}

export interface Category {
  id: string;
  external_id: string | null;
  name: string;
  parent_id: string | null;
  is_active: boolean;
  product_count: number;
  exclude_from_export: boolean;
  children?: Category[];
}

export interface AITask {
  id: number;
  product_id: number;
  task_type: string;
  status: string;
  result: string | null;
  created_at: string;
  completed_at: string | null;
}

export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'partial';
export type ReviewType = 'text' | 'image';

export interface AIReview {
  id: number;
  product_id: number;
  field: string;
  old_value: string | null;
  new_value: string;
  status: string;
  reviewed_by: number | null;
  created_at: string;
}

export interface ReviewListItem {
  id: number;
  product: { id: number; name: string };
  type: ReviewType;
  provider: string;
  status: ReviewStatus;
  created_at: string;
}

export interface ReviewDiffField {
  field: string;
  current: string | null;
  proposed: string;
}

export interface ReviewDetail {
  id: number;
  product: { id: number; name: string };
  type: ReviewType;
  provider: string;
  status: ReviewStatus;
  output_data: Record<string, string>;
  current_data: Record<string, string | null>;
  diff: ReviewDiffField[];
  image_url: string | null;
  cost_usd: number;
  duration_ms: number;
  created_at: string;
  ai_task_id: number;
}

export interface ImportLog {
  id: number;
  filename: string;
  status: string;
  total_rows: number;
  processed_rows: number;
  errors: number;
  started_at: string;
  completed_at: string | null;
}

export interface PaginationMeta {
  total: number;
  page: number;
  per_page: number;
  last_page: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface ApiError {
  error: string;
  code: string;
  request_id: string;
}

export interface LastImportInfo {
  id: string;
  date: string;
  status: string;
  products_created: number;
  products_updated: number;
}

export interface DashboardStats {
  products_total: number;
  products_in_stock: number;
  products_enriched: number;
  products_no_description: number;
  products_with_images: number;
  pending_reviews: number;
  categories_total: number;
  last_import: LastImportInfo | null;
  ai_tasks_today: number;
  ai_tasks_completed_today: number;
}
