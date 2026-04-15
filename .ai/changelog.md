# Changelog — DataPIM

Всі помітні зміни в цьому проєкті.

Формат базується на [Keep a Changelog](https://keepachangelog.com/),
версіонування — [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Discovery brief: elevator pitch, 16 рішень, roadmap v1/v2/v3
- XML аналіз: 36K товарів, 1477 категорій, стратегія імпорту
- AI stack: Anthropic + OpenAI + Google (текст), Flux Pro + DALL-E 3 + Imagen 3 (зображення)
- PRD: 16 user stories, 4 ролі (admin/operator/manager/viewer), матриця дозволів
- Override pattern (R-017): buf_* + custom_* поля для захисту збагачених даних
- Architecture: Monolith, FastAPI + React + PostgreSQL, 8 таблиць, 42 API endpoints
- Decisions: DEC-001 (backend), DEC-002 (frontend), DEC-003 (pattern)
- Design: 12 screens, design system (colors, typography, 25 shadcn/ui components), UI patterns
- Frontend skeleton: React + Vite + TypeScript + shadcn/ui + Tailwind v4 + Zustand + react-i18next
- All screens implemented with MSW mocks, auth flow, RBAC, dark mode, i18n (UK)
- Characteristics CRUD with dialogs, category tree with create/edit, override pattern UI
- Decisions: R-018 (AI as optional module), R-019 (enrichment status — manual for v1.0), R-020 (v1.0 scope revision)
- Backend: FastAPI app — 9 routers (auth, users, categories, products, attributes, images, dashboard, import, export), 168 pytest passed, 4 Alembic migrations, override pattern split for category (buf_category_id + custom_category_id), category exclude_from_export flag with recursive subtree
- Bulk update endpoint POST /api/products/bulk-update + searchable Settings UI for mass brand assignment
- DELETE /api/categories/:id with safety checks (no children, no products)
- Reactivate + permanent delete для users
- Brand filter на /products + GET /api/products/brands
- DevOps prep артефакти: Dockerfile.backend/frontend, docker-compose.prod.yml, nginx-prod.conf (SSL + rate limit), backup.sh, systemd unit, GitHub Actions CI, devops_runbook.md
- QA audit report (`qa_report.md`) — 0 critical, 3 major (всі виправлені)
- Decisions: R-021 (login error wording — single message for security), R-022 (relax R-015 — categories full CRUD allowed)

### Changed
- Login rate limit: 5 req/60s per IP (in-memory dependency)
- Frontend: hero card з 3-зональним layout, Image+Stats card, sticky bottom buttons, searchable CategoryPicker
- Product list: per-page selector (20/50/100), Код+Бренд columns, table-fixed layout
- Categories tree: рекурсивні product_count, optimistic toggle для exclude_from_export, "успадковано" візуалізація

### Fixed
- BackgroundTasks для імпорту: rescue session оновлює ImportLog.failed якщо background coroutine кидає
- uktzed VARCHAR(50) → 255 (BUF фід пакує код+опис)
- Dashboard contract drop: повернуто `ai_tasks_completed_today`
- error_details JSON serialization: прибрано raw datetime
- /reviews routes у frontend (R-020 — AI v1.2+)
- Decimal → float у JSON для price fields

### Removed
- MSW mocks (frontend ходить у real API)

### Security
- Login rate limit (anti brute-force, R-022 background)

---
