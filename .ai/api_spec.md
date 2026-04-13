# API Specification

**Base URL:** `/api`
**Format:** JSON (except XML export)
**Auth:** JWT Bearer token in Authorization header
**Error format:** `{ "error": "message", "code": "ERROR_CODE", "request_id": "uuid" }`
**Pagination:** `{ "data": [...], "meta": { "total", "page", "per_page", "last_page" } }`

---

## Auth

### POST /api/auth/login
- **Auth:** public
- **Rate limit:** 5/min per IP
- **Body:**
  ```json
  { "email": "string", "password": "string" }
  ```
- **200:**
  ```json
  {
    "access_token": "string",
    "refresh_token": "string",
    "user": { "id": "uuid", "email": "string", "name": "string", "role": "string", "theme": "string" }
  }
  ```
- **401:** `{ "error": "Невірний email або пароль", "code": "INVALID_CREDENTIALS" }`
- **429:** `{ "error": "Забагато спроб", "code": "RATE_LIMIT" }`

### POST /api/auth/refresh
- **Auth:** refresh token in body
- **Body:** `{ "refresh_token": "string" }`
- **200:** `{ "access_token": "string", "refresh_token": "string" }`
- **401:** `{ "error": "Token expired", "code": "TOKEN_EXPIRED" }`

### POST /api/auth/logout
- **Auth:** any role
- **200:** `{ "message": "ok" }`

### GET /api/auth/me
- **Auth:** any role
- **200:** `{ "id", "email", "name", "role", "theme", "created_at" }`

### PATCH /api/auth/me
- **Auth:** any role
- **Body:** `{ "name?": "string", "theme?": "light|dark", "password?": "string", "current_password?": "string" }`
- **200:** `{ User }`
- **400:** `{ "error": "Поточний пароль невірний", "code": "INVALID_PASSWORD" }`

---

## Users

### GET /api/users
- **Auth:** admin, manager (read only)
- **Query:** `page=1&per_page=50&search=&role=&is_active=`
- **200:** `{ "data": [User], "meta": {...} }`
- **403:** operator, viewer

### POST /api/users
- **Auth:** admin
- **Body:** `{ "email": "string", "name": "string", "password": "string", "role": "admin|operator|manager|viewer" }`
- **201:** `{ User }`
- **409:** `{ "error": "Email вже зайнятий", "code": "DUPLICATE_EMAIL" }`
- **403:** non-admin

### GET /api/users/:id
- **Auth:** admin, manager
- **200:** `{ User }`
- **404:** `{ "error": "Користувача не знайдено", "code": "NOT_FOUND" }`

### PATCH /api/users/:id
- **Auth:** admin
- **Body:** `{ "email?", "name?", "password?", "role?", "is_active?" }`
- **200:** `{ User }`

### DELETE /api/users/:id
- **Auth:** admin
- **200:** `{ "message": "User deactivated" }` — sets is_active=false

---

## Categories

### GET /api/categories
- **Auth:** any role
- **Query:** `tree=true` | `parent_id=uuid`
- **200 (tree=true):**
  ```json
  {
    "data": [{
      "id": "uuid", "external_id": "string", "name": "string",
      "parent_id": "uuid|null", "is_active": true,
      "product_count": 42,
      "children": [{ ...recursive }]
    }]
  }
  ```
- **200 (parent_id=uuid):**
  ```json
  { "data": [{ Category without children }] }
  ```

### GET /api/categories/:id
- **Auth:** any role
- **200:**
  ```json
  {
    "id", "external_id", "name", "parent_id", "is_active", "product_count",
    "children": [{ id, name, product_count }],
    "breadcrumb": [{ "id": "uuid", "name": "string" }]
  }
  ```

### PATCH /api/categories/:id
- **Auth:** admin, operator
- **Body:** `{ "name": "string" }`
- **200:** `{ Category }`
- **403:** manager, viewer

---

## Products

### GET /api/products
- **Auth:** any role
- **Query:** `page=1&per_page=50&search=&category_id=&in_stock=true|false&enrichment_status=none|partial|full&has_pending_review=true|false&sort_by=name|price|created_at&sort_order=asc|desc`
- **200:**
  ```json
  {
    "data": [{
      "id": "uuid",
      "internal_code": "string",
      "sku": "string",
      "name": "string (resolved: custom ?? buf)",
      "brand": "string|null (resolved)",
      "price": 1015.16,
      "currency": "UAH",
      "in_stock": true,
      "category": { "id": "uuid", "name": "string" } | null,
      "primary_image": { "id": "uuid", "file_path": "string" } | null,
      "enrichment_status": "none|partial|full",
      "has_pending_review": false
    }],
    "meta": { "total": 11620, "page": 1, "per_page": 50, "last_page": 233 }
  }
  ```

### GET /api/products/:id
- **Auth:** any role
- **200:**
  ```json
  {
    "id": "uuid",
    "internal_code": "string",
    "sku": "string",
    "buf_name": "string", "custom_name": "string|null", "name": "resolved",
    "buf_brand": "string|null", "custom_brand": "string|null", "brand": "resolved",
    "buf_country": "string|null", "custom_country": "string|null", "country": "resolved",
    "buf_price": 1015.16, "buf_currency": "UAH",
    "buf_quantity": 1, "buf_in_stock": true,
    "uktzed": "string|null",
    "is_active": true,
    "description": "string|null",
    "seo_title": "string|null",
    "seo_description": "string|null",
    "enrichment_status": "none|partial|full",
    "has_pending_review": false,
    "category": { "id", "name", "breadcrumb": [{ "id", "name" }] } | null,
    "images": [{ "id", "file_path", "file_name", "is_primary", "source", "sort_order" }],
    "attributes": [{ "id", "key", "value", "source", "sort_order" }],
    "created_at": "iso", "updated_at": "iso"
  }
  ```

### PATCH /api/products/:id
- **Auth:** admin, operator
- **Body:** `{ "custom_name?", "custom_brand?", "custom_country?", "description?", "seo_title?", "seo_description?" }`
- **200:** `{ Product (full) }`
- **403:** manager, viewer

### POST /api/products/:id/reset-field
- **Auth:** admin, operator
- **Body:** `{ "field": "name|brand|country" }`
- **200:** `{ Product }` — custom_* = NULL

---

## Product Attributes

### GET /api/products/:id/attributes
- **Auth:** any role
- **200:** `{ "data": [{ "id", "key", "value", "source", "sort_order" }] }`

### POST /api/products/:id/attributes
- **Auth:** admin, operator
- **Body:** `{ "key": "string", "value": "string" }`
- **201:** `{ Attribute }`
- **409:** `{ "error": "Атрибут з таким ключем вже існує", "code": "DUPLICATE_KEY" }`

### PATCH /api/products/:id/attributes/:attr_id
- **Auth:** admin, operator
- **Body:** `{ "key?", "value?", "sort_order?" }`
- **200:** `{ Attribute }`

### DELETE /api/products/:id/attributes/:attr_id
- **Auth:** admin, operator
- **200:** `{ "message": "Deleted" }`

---

## Product Images

### GET /api/products/:id/images
- **Auth:** any role
- **200:** `{ "data": [{ "id", "file_path", "file_name", "file_size", "mime_type", "is_primary", "source", "sort_order" }] }`

### POST /api/products/:id/images
- **Auth:** admin, operator
- **Content-Type:** multipart/form-data
- **Body:** `file` (binary) + `is_primary` (optional bool)
- **201:** `{ Image }`
- **400:** `{ "error": "Файл занадто великий (max 10MB)", "code": "FILE_TOO_LARGE" }`
- **400:** `{ "error": "Непідтримуваний формат (png, jpeg, webp)", "code": "INVALID_FILE_TYPE" }`

### PATCH /api/products/:id/images/:img_id
- **Auth:** admin, operator
- **Body:** `{ "is_primary?": true, "sort_order?": 0 }`
- **200:** `{ Image }`

### DELETE /api/products/:id/images/:img_id
- **Auth:** admin, operator
- **200:** `{ "message": "Deleted" }` — file + DB record

---

## AI Tasks

### POST /api/products/:id/ai/enrich
- **Auth:** admin, operator
- **Body:** `{ "provider?": "anthropic|openai|google" }`
- **202:** `{ "task_id": "uuid", "status": "pending" }`
- **409:** `{ "error": "Вже є незатверджений draft", "code": "PENDING_REVIEW_EXISTS" }`
- **403:** manager, viewer

### POST /api/products/:id/ai/generate-image
- **Auth:** admin, operator
- **Body:** `{ "provider?": "flux|dalle|imagen" }`
- **202:** `{ "task_id": "uuid", "status": "pending" }`
- **403:** manager, viewer

### POST /api/categories/:id/ai/bulk-enrich
- **Auth:** admin only
- **Body:** `{ "provider?": "anthropic|openai|google" }`
- **202:** `{ "batch_id": "uuid", "total_products": 120, "status": "pending" }`
- **403:** non-admin

### GET /api/ai/tasks
- **Auth:** admin, operator, manager
- **Query:** `page=1&per_page=50&product_id=&type=text|image&status=pending|processing|completed|failed&sort_by=created_at&sort_order=desc`
- **200:** `{ "data": [{ "id", "product": {"id","name"}, "type", "provider", "status", "cost_usd", "duration_ms", "created_at" }], "meta": {...} }`

### GET /api/ai/tasks/:id
- **Auth:** admin, operator, manager
- **200:** `{ AITask full with input_data, output_data, error_message }`

---

## AI Reviews

### GET /api/reviews
- **Auth:** admin, operator, manager
- **Query:** `page=1&per_page=50&status=pending|approved|rejected|partial&sort_by=created_at&sort_order=desc`
- **200:**
  ```json
  {
    "data": [{
      "id": "uuid",
      "ai_task": { "id", "type", "provider" },
      "product": { "id", "name" },
      "status": "pending",
      "created_at": "iso"
    }],
    "meta": {...}
  }
  ```

### GET /api/reviews/:id
- **Auth:** admin, operator, manager
- **200:**
  ```json
  {
    "id": "uuid",
    "status": "pending",
    "ai_task": { "id", "type", "provider", "output_data": {...} },
    "product": {
      "id", "name",
      "current_data": { "description": "...", "custom_name": "...", ... }
    },
    "diff": {
      "description": { "current": "null", "proposed": "AI generated text..." },
      "seo_title": { "current": "null", "proposed": "..." }
    },
    "created_at": "iso"
  }
  ```

### POST /api/reviews/:id/approve
- **Auth:** admin, operator
- **Body:** `{}`
- **200:** `{ Review }` — applies all AI output → custom_* fields
- **403:** manager, viewer

### POST /api/reviews/:id/partial-approve
- **Auth:** admin, operator
- **Body:** `{ "fields": ["description", "seo_title"] }`
- **200:** `{ Review }` — applies only selected fields

### POST /api/reviews/:id/reject
- **Auth:** admin, operator
- **Body:** `{ "reason?": "string" }`
- **200:** `{ Review }`

---

## Import

### POST /api/import/trigger
- **Auth:** admin
- **202:** `{ "import_id": "uuid", "status": "running" }`
- **403:** non-admin

### GET /api/import/logs
- **Auth:** admin, manager
- **Query:** `page=1&per_page=20`
- **200:** `{ "data": [ImportLog], "meta": {...} }`

### GET /api/import/logs/:id
- **Auth:** admin, manager
- **200:** `{ ImportLog full with error_details }`

---

## Export (public)

### GET /export/products.xml
- **Auth:** public (no auth required)
- **200:** XML content-type
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <Catalog generated_at="2026-04-13T15:00">
    <Product>
      <internal_code>U-45GCS</internal_code>
      <sku>U-45GCS</sku>
      <name>Resolved name (custom ?? buf)</name>
      <brand>Resolved brand</brand>
      <description>AI-enriched description</description>
      <category_id>18003</category_id>
      <category_name>Category name</category_name>
      <uktzed>8467810000</uktzed>
      <country_of_origin>Resolved country</country_of_origin>
      <price_rrp>999.00</price_rrp>
      <currency>UAH</currency>
      <in_stock>true</in_stock>
      <image_url>https://domain/uploads/uuid.png</image_url>
      <updated_at>2026-04-13T15:00</updated_at>
    </Product>
  </Catalog>
  ```
- **Note:** Only in_stock=true products. No quantity field.

### GET /export/categories.xml
- **Auth:** public
- **200:** XML — categories that have in_stock products
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <Categories generated_at="2026-04-13T15:00">
    <Category>
      <id>18003</id>
      <parent_id>18000</parent_id>
      <name>Category name</name>
    </Category>
  </Categories>
  ```

### GET /api/export/settings
- **Auth:** admin, manager
- **200:**
  ```json
  {
    "products_url": "/export/products.xml",
    "categories_url": "/export/categories.xml",
    "last_generated": "iso|null",
    "products_count": 11620,
    "categories_count": 781
  }
  ```

---

## Dashboard

### GET /api/dashboard/stats
- **Auth:** any role
- **200:**
  ```json
  {
    "products_total": 11620,
    "products_in_stock": 11620,
    "products_enriched": 3500,
    "products_no_description": 8120,
    "products_with_images": 2100,
    "pending_reviews": 15,
    "categories_total": 1477,
    "last_import": {
      "id": "uuid",
      "date": "iso",
      "status": "completed",
      "products_created": 150,
      "products_updated": 1200
    },
    "ai_tasks_today": 42,
    "ai_tasks_completed_today": 38
  }
  ```

---

## Summary

| Група | Endpoints | Methods |
|-------|-----------|---------|
| Auth | 5 | POST, GET, PATCH |
| Users | 5 | GET, POST, PATCH, DELETE |
| Categories | 3 | GET, PATCH |
| Products | 4 | GET, PATCH, POST |
| Product Attributes | 4 | GET, POST, PATCH, DELETE |
| Product Images | 4 | GET, POST, PATCH, DELETE |
| AI Tasks | 5 | POST, GET |
| AI Reviews | 5 | GET, POST |
| Import | 3 | POST, GET |
| Export | 3 | GET |
| Dashboard | 1 | GET |
| **Total** | **42** | — |
