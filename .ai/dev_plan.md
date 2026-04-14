# Development Plan — DataPIM Backend

## Статус: В процесі

## Стек (з architecture.md)
- Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Pydantic v2 + Alembic
- PostgreSQL 16 (shared, database: `datapim`)
- Port: 8000
- JWT HS256 (24h access, 7d refresh), bcrypt
- Ruff (lint + format), pytest для тестів
- Без Redis/Celery (MVP) — FastAPI BackgroundTasks
- File storage: local `uploads/` + nginx

## Scope v1.0 (per R-020)
**Обов'язково:**
- Auth (JWT, login, refresh, me)
- Users CRUD
- Products list + edit (override pattern)
- Categories CRUD з деревом
- Characteristics CRUD (attributes)
- Images upload/delete
- XML import (папка + ручний trigger)
- XML export (публічний URL)

**НЕ входить в v1.0:**
- Додавання товару вручну → v1.1
- AI enrichment → v1.2+
- AI review workflow → v1.2+
- Rate limiting → перевірити потребу (5 users)
- Notifications → не потрібні для v1.0

---

## Етапи

### Етап 1: Ініціалізація каркасу
- [ ] Структура папок (backend/app, models, schemas, routers, services)
- [ ] requirements.txt (fastapi, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose, bcrypt, python-multipart)
- [ ] Makefile (dev, test, lint, migrate, seed, reset, health)
- [ ] Ruff config (.ruff.toml)
- [ ] ENV validation (Pydantic Settings)
- [ ] Docker + docker-compose.yml + healthcheck
- [ ] .dockerignore
- [ ] Health endpoints (/health, /ready)
- [ ] Request ID middleware
- [ ] Structured JSON logging (loguru)
- [ ] Graceful shutdown
- [ ] Error handler middleware (єдиний формат {error, code, request_id})
- [ ] CORS (origins з .env)

### Етап 2: Моделі та дані
- [ ] SQLAlchemy моделі з db_schema.md (8 таблиць)
- [ ] Alembic init + initial migration
- [ ] Seed admin user (з DEV_EMAIL / DEV_PASSWORD)
- [ ] Тестова інфраструктура (pytest + test DB)

### Етап 3: Auth
- [ ] POST /api/auth/login
- [ ] POST /api/auth/refresh
- [ ] GET /api/auth/me
- [ ] PATCH /api/auth/me
- [ ] POST /api/auth/logout
- [ ] JWT utilities (create, verify)
- [ ] get_current_user dependency
- [ ] require_role RBAC dependency
- [ ] Тести

### Етап 4: Users CRUD
- [ ] GET /api/users (pagination, filters)
- [ ] POST /api/users (admin)
- [ ] GET /api/users/:id
- [ ] PATCH /api/users/:id
- [ ] DELETE /api/users/:id (soft delete)
- [ ] RBAC: admin full, manager read
- [ ] Тести

### Етап 5: Categories CRUD
- [ ] GET /api/categories (tree=true)
- [ ] GET /api/categories/:id
- [ ] POST /api/categories (create with parent)
- [ ] PATCH /api/categories/:id (rename, reparent)
- [ ] Тести

### Етап 6: Products CRUD (edit only, no create per R-020)
- [ ] GET /api/products (pagination, filters, search, sort)
- [ ] GET /api/products/:id (full detail with override)
- [ ] PATCH /api/products/:id (custom_* fields)
- [ ] POST /api/products/:id/reset-field
- [ ] RBAC: admin+operator edit, all read
- [ ] Тести

### Етап 7: Product Attributes (characteristics)
- [ ] GET /api/products/:id/attributes
- [ ] POST /api/products/:id/attributes
- [ ] PATCH /api/products/:id/attributes/:attr_id
- [ ] DELETE /api/products/:id/attributes/:attr_id
- [ ] Тести

### Етап 8: Product Images
- [ ] GET /api/products/:id/images
- [ ] POST /api/products/:id/images (multipart upload, max 10MB, png/jpeg/webp)
- [ ] PATCH /api/products/:id/images/:img_id (is_primary)
- [ ] DELETE /api/products/:id/images/:img_id
- [ ] Local filesystem storage (uploads/ folder, UUID names)
- [ ] Static serve через nginx (або FastAPI StaticFiles в dev)
- [ ] Тести

### Етап 9: XML Import (BUF)
- [ ] POST /api/import/trigger (background task)
- [ ] GET /api/import/logs
- [ ] GET /api/import/logs/:id
- [ ] XML parser для products (TMC.xml) і categories (TMCC.xml)
- [ ] Price parsing "1 015,16" → 1015.16
- [ ] SKU trimming
- [ ] Upsert по internal_code (product) і external_id (category)
- [ ] Логіка: нові створюємо тільки in_stock=true, існуючі оновлюємо флаг, не видаляємо
- [ ] Категорії: дедуплікація по external_id
- [ ] Import log з лічильниками (created, updated, stock_changed, errors)
- [ ] Тести

### Етап 10: XML Export (для партнерів)
- [ ] GET /export/products.xml (публічний, без auth)
- [ ] GET /export/categories.xml (публічний, без auth)
- [ ] GET /api/export/settings (admin+manager read)
- [ ] Генерація XML: тільки in_stock=true, resolved поля (custom ?? buf)
- [ ] Тести

### Етап 11: Dashboard
- [ ] GET /api/dashboard/stats
- [ ] Підрахунок метрик з БД
- [ ] Тести

### Етап 12: Підключення frontend
- [ ] VITE_MSW_ENABLED=false в frontend/.env
- [ ] Перевірити всі екрани з реальним API
- [ ] Виправити невідповідності
- [ ] Permission-aware UI перевірка (admin/operator/manager/viewer)

### Етап 13: Фіналізація
- [ ] Чистий старт (make reset + make dev + make test)
- [ ] Performance check vs budget
- [ ] OpenAPI /docs доступний
- [ ] README з командами
- [ ] make lint — 0 errors
- [ ] make test — all green

---

## Handoff → QA (заповнюється в кінці)

_Буде заповнено коли backend готовий._
