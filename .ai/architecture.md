# Technical Architecture

## 1. Огляд
- **Патерн:** Monolith — MVP, 5 concurrent users, 1 developer, дедлайн "завтра"
- **Схема взаємодії:**
```
[Browser] ←→ [nginx] ←→ [FastAPI Backend] ←→ [PostgreSQL]
                │                │
                │                ├→ [BUF XML] (inbox/ folder)
                │                ├→ [Anthropic API]
                │                ├→ [OpenAI API]
                │                ├→ [Google AI API]
                │                ├→ [Flux Pro API]
                │                ├→ [DALL-E 3 API]
                │                └→ [Imagen 3 API]
                │
                └→ [Vite SPA] (static files)
                └→ [uploads/] (product images)
```

## 2. Стек технологій

| Компонент | Вибір | Альтернативи | DEC-ID | Обґрунтування |
|-----------|-------|--------------|--------|---------------|
| Backend | FastAPI + Python 3.12 | Hono, Django | DEC-001 | Async, Pydantic, нативні AI SDK |
| Frontend | React + Vite + TypeScript | Vue, Next.js | DEC-002 | shadcn/ui, Tailwind v4, SPA |
| DB | PostgreSQL 16 | SQLite | DEC-003 | Вже сконфігуровано, ієрархія, JSON |
| ORM | SQLAlchemy 2.x | Tortoise | DEC-001 | Стандарт для FastAPI |
| Validation | Pydantic v2 | — | DEC-001 | Вбудовано в FastAPI |
| Migrations | Alembic | — | DEC-001 | Стандарт для SQLAlchemy |
| CSS | Tailwind v4 | — | DEC-002 | Стандарт з shadcn/ui |
| Components | shadcn/ui | Radix, MUI | DEC-002 | Material-like, кастомізація |
| Icons | Lucide | — | DEC-002 | Стандарт з shadcn/ui |
| State | Zustand | Context, Redux | DEC-002 | Легкий, простий API |
| i18n | react-i18next | — | DEC-002 | Стандарт для React i18n |
| Cache | Не потрібен (MVP) | Redis | — | 5 users, PostgreSQL достатньо |
| Queue | Не потрібен (MVP) | Celery, RQ | — | FastAPI BackgroundTasks |
| File storage | Local filesystem | MinIO | — | Простота, nginx static serve |

## 3. Структура проєкту

```
datapim/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, middleware, startup
│   │   ├── config.py               # Pydantic Settings from .env
│   │   ├── database.py             # SQLAlchemy engine, session
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── category.py
│   │   │   ├── image.py
│   │   │   ├── attribute.py
│   │   │   ├── ai_task.py
│   │   │   ├── ai_review.py
│   │   │   └── import_log.py
│   │   ├── schemas/                # Pydantic request/response
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── category.py
│   │   │   ├── image.py
│   │   │   ├── ai.py
│   │   │   ├── review.py
│   │   │   ├── import_.py
│   │   │   └── common.py           # PaginatedResponse, ErrorResponse
│   │   ├── routers/                # FastAPI routers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── products.py
│   │   │   ├── categories.py
│   │   │   ├── images.py
│   │   │   ├── ai.py
│   │   │   ├── reviews.py
│   │   │   ├── import_.py
│   │   │   ├── export.py
│   │   │   └── dashboard.py
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── user_service.py
│   │   │   ├── product_service.py
│   │   │   ├── category_service.py
│   │   │   ├── import_service.py   # XML parsing + upsert
│   │   │   ├── export_service.py   # XML generation
│   │   │   ├── ai_service.py       # Multi-provider text routing
│   │   │   ├── ai_image_service.py # Multi-provider image routing
│   │   │   └── review_service.py   # Approve/reject logic
│   │   ├── dependencies/           # FastAPI Depends
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # get_current_user
│   │   │   └── rbac.py             # require_role decorator
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── xml_parser.py       # BUF XML → dict
│   │       ├── price_parser.py     # "1 015,16" → Decimal
│   │       └── request_id.py       # middleware
│   ├── migrations/                 # Alembic
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_products.py
│   │   └── ...
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Makefile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/             # shadcn/ui + custom
│   │   │   ├── ui/                 # shadcn primitives
│   │   │   ├── layout/             # sidebar, header, theme toggle
│   │   │   ├── products/           # product list, card, filters
│   │   │   ├── categories/         # category tree
│   │   │   ├── ai/                 # AI enrich button, diff viewer
│   │   │   ├── reviews/            # review list, approve/reject
│   │   │   └── users/              # user management
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ProductsPage.tsx
│   │   │   ├── ProductDetailPage.tsx
│   │   │   ├── CategoriesPage.tsx
│   │   │   ├── ReviewsPage.tsx
│   │   │   ├── UsersPage.tsx
│   │   │   ├── ImportPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useProducts.ts
│   │   │   └── ...
│   │   ├── services/
│   │   │   └── api.ts              # fetch wrapper with auth
│   │   ├── stores/
│   │   │   ├── authStore.ts        # zustand
│   │   │   └── themeStore.ts
│   │   ├── lib/
│   │   │   ├── i18n.ts             # react-i18next setup
│   │   │   └── utils.ts
│   │   ├── locales/
│   │   │   └── uk.json             # Ukrainian translations
│   │   └── types/
│   │       └── api.ts              # TypeScript types from API
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
├── uploads/                        # Product images (gitignored)
├── inbox/                          # BUF XML input (gitignored)
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── nginx.conf
├── .env / .env.example
└── .gitignore

## 4. Безпека
- **Auth:** JWT HS256, access token 24h, refresh token 7d
- **Authz:** RBAC middleware — `require_role("admin", "operator")` decorator
- **Password:** bcrypt, min 8 chars
- **Secrets:** Pydantic Settings з валідацією при старті (missing key = fail fast)
- **Rate limiting:** SlowAPI — login 5/min per IP
- **CORS:** dev: `localhost:5174`, prod: domain
- **File upload:** max 10MB, allowed: png/jpeg/webp, UUID rename
- **API keys:** в .env, валідуються при старті, ніколи не в БД і не в response

## 5. Error Handling
- **Формат:** `{ "error": "message", "code": "ERROR_CODE", "request_id": "uuid" }`
- **HTTP коди:**

| Код | Коли |
|-----|------|
| 400 | Невалідний вхід (з переліком полів) |
| 401 | Не авторизований / token expired |
| 403 | Немає прав (RBAC) |
| 404 | Ресурс не знайдено |
| 409 | Конфлікт (duplicate email, pending review exists) |
| 422 | Бізнес-логіка (Pydantic validation) |
| 429 | Rate limit |
| 500 | Внутрішня помилка (без деталей клієнту) |

## 6. Pagination
- **Тип:** offset
- **Формат:** `{ "data": [...], "meta": { "total", "page", "per_page", "last_page" } }`
- **Дефолти:** page=1, per_page=50, max=100

## 7. Soft Delete

| Сутність | Стратегія | Причина |
|----------|-----------|---------|
| User | is_active=false | зв'язані AI tasks/reviews |
| Product | ніколи не видаляється | R-014: тільки in_stock flag |
| Category | ніколи не видаляється | R-015: з BUF |
| ProductImage | hard delete | файл + запис |
| ProductAttribute | hard delete | можна перестворити |
| AITask | зберігається | аудит |
| AIReview | зберігається | аудит |
| ImportLog | зберігається | аудит |

## 8. Caching
Не потрібен на MVP. 5 users, <12K products, PostgreSQL з індексами достатньо.
Додати Redis коли: >50 concurrent users, або heavy dashboard queries.

## 9. Background Jobs
FastAPI BackgroundTasks (без Celery/Redis):

| Задача | Тип | Retry |
|--------|-----|-------|
| XML import | BackgroundTask (admin trigger) | 1 раз, log errors |
| AI text enrichment | BackgroundTask | fallback provider |
| AI image generation | BackgroundTask | fallback provider |
| Bulk AI enrichment | asyncio.gather (batch) | per-item fallback |
| XML export | on-demand (cached in-memory) | — |

## 10. File Storage
- **Де:** Local filesystem `uploads/`
- **Serve:** nginx static `/uploads/`
- **Ліміти:** max 10MB, png/jpeg/webp
- **Іменування:** `{uuid}.{ext}` (уникнення колізій)
- **Доступ:** public URL через nginx

## 11. Notifications
In-app only (DB query, polling):

| Канал | Реалізація |
|-------|-----------|
| Pending reviews badge | `SELECT COUNT(*) FROM ai_reviews WHERE status='pending'` |
| Import status | Dashboard query |
| AI tasks progress | Dashboard query |

## 12. Performance Budget

| Категорія | Бюджет |
|-----------|--------|
| Auth endpoints | p95 < 100ms |
| CRUD endpoints | p95 < 200ms |
| List + pagination | p95 < 500ms |
| XML import (36K parse) | < 60s |
| AI enrichment (1 card) | < 30s |
| File upload (10MB) | p95 < 2s |
| Page LCP | < 3s |
| Frontend bundle | < 500KB gzipped |
| DB query (single) | < 50ms |
| DB query (join/aggregate) | < 200ms |
| XML export (11K) | < 10s |

## 13. Інфраструктура
- **Docker:** docker-compose.yml — backend + frontend + postgres (shared)
- **Healthchecks:** postgres (pg_isready), backend (/health)
- **CI/CD:** GitHub Actions (lint → test → build) — пізніше
- **Хостинг:** Ubuntu 22, nginx reverse proxy, власний сервер
- **Моніторинг:** `/health`, `/ready`, structured JSON logs (loguru)
- **Бекапи:** `pg_dump` cron daily, зберігати 7 днів, RTO < 1h

## 14. Environments

| Env | БД | Особливості |
|-----|----|----|
| dev | localhost:5432/datapim | hot reload, debug logs, CORS localhost:5174 |
| test | localhost:5432/datapim_test | auto-create/drop, fixtures |
| prod | remote/datapim | SSL, pg_dump backups, min logs |

## 15. Connection Pool
SQLAlchemy async:
- pool_size: 5
- max_overflow: 10
- pool_timeout: 30s
- pool_recycle: 1800s

## 16. Стратегія міграцій БД
- **Інструмент:** Alembic (auto-generate від SQLAlchemy models)
- **Порядок:** `alembic upgrade head` (up), `alembic downgrade -1` (down)
- **Правила:** backward-compatible, no data loss, test locally before prod

## 17. Інтеграції

| Сервіс | Призначення | API/SDK | Rate limits | Fallback |
|--------|-------------|---------|-------------|----------|
| BUF XML | Імпорт товарів | File read (inbox/) | — | Log error |
| Anthropic | AI text enrichment | anthropic SDK | Standard tier | → OpenAI |
| OpenAI | AI text enrichment | openai SDK | Standard tier | → Google |
| Google AI | AI text enrichment | google-generativeai | Standard tier | → Anthropic |
| Flux Pro | AI image gen | replicate SDK / REST | Varies | → DALL-E 3 |
| DALL-E 3 | AI image gen | openai SDK | 50 img/min | → Imagen 3 |
| Imagen 3 | AI image gen | google-cloud SDK | Varies | Error message |

## Handoff → Design
- **api_spec.md готовий** — frontend-skeleton читає для TypeScript типів і MSW handlers
- **Фронтенд-стек:** React + Vite + TypeScript + shadcn/ui + Tailwind v4 + Zustand + react-i18next
- **Ролі та доступи:** 4 ролі → RBAC middleware, frontend route guards
- **Ключові сутності:** Product (override pattern), Category (tree), AITask, AIReview
- **Pagination format:** `{ data, meta: { total, page, per_page, last_page } }`
- **Error format:** `{ error, code, request_id }`
- **Performance budget (frontend):** LCP < 3s, bundle < 500KB gzipped
- **Developer очікує:**
  - Makefile commands (dev, test, lint, migrate, seed, reset, health)
  - Health endpoints (/health, /ready)
  - Request ID middleware
  - Structured JSON logging (loguru)
  - ENV validation при старті (Pydantic Settings)
  - Docker healthchecks
  - Linting: ruff (backend), biome (frontend)
  - Graceful shutdown
