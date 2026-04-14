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

### Changed
### Fixed
### Removed
### Security

---
