# Database Schema

**DB:** PostgreSQL 16
**ORM:** SQLAlchemy 2.x (async)
**Migrations:** Alembic (auto-generate)

## users

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| email | varchar(255) | UNIQUE, NOT NULL | логін |
| password_hash | varchar(255) | NOT NULL | bcrypt |
| name | varchar(100) | NOT NULL | — |
| role | enum(admin, operator, manager, viewer) | NOT NULL, default 'viewer' | RBAC |
| is_active | boolean | NOT NULL, default true | soft delete |
| theme | varchar(10) | NOT NULL, default 'light' | dark/light |
| created_at | timestamptz | NOT NULL, default now() | — |
| updated_at | timestamptz | NOT NULL, default now() | auto on update |

**Індекси:**
- `idx_users_email` (email) — UNIQUE
- `idx_users_role` (role)
- `idx_users_is_active` (is_active)

---

## categories

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | internal PK |
| external_id | varchar(50) | UNIQUE, NOT NULL | ID з BUF XML |
| parent_id | uuid | FK → categories.id, NULL | ієрархія (self-ref) |
| name | varchar(255) | NOT NULL | назва з BUF |
| is_active | boolean | NOT NULL, default true | з BUF |
| product_count | integer | NOT NULL, default 0 | denormalized counter |
| created_at | timestamptz | NOT NULL, default now() | — |
| updated_at | timestamptz | NOT NULL, default now() | — |

**Індекси:**
- `idx_categories_external_id` (external_id) — UNIQUE
- `idx_categories_parent_id` (parent_id)
- `idx_categories_is_active` (is_active)

---

## products

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| internal_code | varchar(50) | UNIQUE, NOT NULL | ключ upsert з BUF |
| sku | varchar(100) | NOT NULL | артикул (trimmed) |
| category_id | uuid | FK → categories.id, NULL | — |
| buf_name | varchar(500) | NOT NULL | назва з BUF |
| custom_name | varchar(500) | NULL | override |
| buf_brand | varchar(255) | NULL | бренд з BUF |
| custom_brand | varchar(255) | NULL | override |
| buf_country | varchar(100) | NULL | країна з BUF |
| custom_country | varchar(100) | NULL | override |
| buf_price | decimal(12,2) | NOT NULL, default 0 | ціна з BUF |
| buf_currency | varchar(3) | NOT NULL, default 'UAH' | — |
| buf_quantity | integer | NULL | кількість з BUF |
| buf_in_stock | boolean | NOT NULL, default false | наявність з BUF |
| uktzed | varchar(50) | NULL | митна класифікація |
| is_active | boolean | NOT NULL, default true | з BUF |
| description | text | NULL | опис (DataPIM/AI) |
| seo_title | varchar(255) | NULL | — |
| seo_description | text | NULL | — |
| has_pending_review | boolean | NOT NULL, default false | denorm |
| enrichment_status | enum(none, partial, full) | NOT NULL, default 'none' | — |
| created_at | timestamptz | NOT NULL, default now() | — |
| updated_at | timestamptz | NOT NULL, default now() | — |

**Індекси:**
- `idx_products_internal_code` (internal_code) — UNIQUE
- `idx_products_category_id` (category_id)
- `idx_products_buf_in_stock` (buf_in_stock)
- `idx_products_is_active` (is_active)
- `idx_products_enrichment_status` (enrichment_status)
- `idx_products_has_pending_review` (has_pending_review)
- `idx_products_search` — GIN on tsvector(buf_name, custom_name) for full-text

**Override pattern (R-017):**
- Display: `COALESCE(custom_name, buf_name)` AS name
- Import: always write buf_*, never touch custom_*
- Reset: SET custom_* = NULL

---

## product_attributes

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| product_id | uuid | FK → products.id, NOT NULL, ON DELETE CASCADE | — |
| key | varchar(100) | NOT NULL | "Вага" |
| value | varchar(500) | NOT NULL | "5 кг" |
| sort_order | integer | NOT NULL, default 0 | — |
| source | enum(manual, ai) | NOT NULL, default 'manual' | — |
| created_at | timestamptz | NOT NULL, default now() | — |
| updated_at | timestamptz | NOT NULL, default now() | — |

**Індекси:**
- `idx_product_attributes_product_id` (product_id)
- `uq_product_attributes_product_key` (product_id, key) — UNIQUE

---

## product_images

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| product_id | uuid | FK → products.id, NOT NULL, ON DELETE CASCADE | — |
| file_path | varchar(500) | NOT NULL | шлях до файлу |
| file_name | varchar(255) | NOT NULL | оригінальне ім'я |
| file_size | integer | NOT NULL | байти |
| mime_type | varchar(50) | NOT NULL | image/png, etc |
| is_primary | boolean | NOT NULL, default false | головне |
| source | enum(upload, ai, import) | NOT NULL | — |
| sort_order | integer | NOT NULL, default 0 | — |
| created_at | timestamptz | NOT NULL, default now() | — |

**Індекси:**
- `idx_product_images_product_id` (product_id)

---

## ai_tasks

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| product_id | uuid | FK → products.id, NOT NULL | — |
| user_id | uuid | FK → users.id, NOT NULL | хто запустив |
| type | enum(text, image) | NOT NULL | — |
| provider | varchar(50) | NOT NULL | anthropic/openai/google/flux/dalle/imagen |
| status | enum(pending, processing, completed, failed) | NOT NULL, default 'pending' | — |
| input_data | jsonb | NULL | вхідні дані |
| output_data | jsonb | NULL | результат AI |
| error_message | text | NULL | — |
| cost_usd | decimal(8,4) | NULL | вартість |
| duration_ms | integer | NULL | — |
| created_at | timestamptz | NOT NULL, default now() | — |
| completed_at | timestamptz | NULL | — |

**Індекси:**
- `idx_ai_tasks_product_id` (product_id)
- `idx_ai_tasks_user_id` (user_id)
- `idx_ai_tasks_status` (status)
- `idx_ai_tasks_type` (type)
- `idx_ai_tasks_created_at` (created_at DESC)

---

## ai_reviews

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| ai_task_id | uuid | FK → ai_tasks.id, UNIQUE, NOT NULL | 1:1 |
| status | enum(pending, approved, rejected, partial) | NOT NULL, default 'pending' | — |
| reviewed_by | uuid | FK → users.id, NULL | — |
| changes_applied | jsonb | NULL | які поля прийняті |
| created_at | timestamptz | NOT NULL, default now() | — |
| reviewed_at | timestamptz | NULL | — |

**Індекси:**
- `idx_ai_reviews_ai_task_id` (ai_task_id) — UNIQUE
- `idx_ai_reviews_status` (status)
- `idx_ai_reviews_reviewed_by` (reviewed_by)

---

## import_logs

| Поле | Тип | Constraints | Опис |
|------|-----|------------|------|
| id | uuid | PK, default gen_random_uuid() | — |
| file_name | varchar(255) | NOT NULL | TMC.xml / TMCC.xml |
| started_at | timestamptz | NOT NULL, default now() | — |
| finished_at | timestamptz | NULL | — |
| status | enum(running, completed, failed) | NOT NULL, default 'running' | — |
| products_created | integer | NOT NULL, default 0 | — |
| products_updated | integer | NOT NULL, default 0 | — |
| products_stock_changed | integer | NOT NULL, default 0 | — |
| categories_upserted | integer | NOT NULL, default 0 | — |
| errors_count | integer | NOT NULL, default 0 | — |
| error_details | jsonb | NULL | масив помилок |

**Індекси:**
- `idx_import_logs_started_at` (started_at DESC)

---

## Діаграма зв'язків

```
users 1──N ai_tasks
               │
         ai_tasks 1──1 ai_reviews
               │
         ai_tasks N──1 products
                         │
               products 1──N product_images
               products 1──N product_attributes
               products N──1 categories
                                │
                        categories ──→ categories (self-ref parent_id)

import_logs (standalone)
```

## Seed Data

При першому запуску (`make seed`):
- Створити admin user з DEV_EMAIL / DEV_PASSWORD / DEV_NAME з .env

## Migration Strategy

- Alembic auto-generate від SQLAlchemy models
- `make migrate` → `alembic upgrade head`
- `make rollback` → `alembic downgrade -1`
- Backward-compatible: no data loss
- Test locally → apply to prod
