# Decisions

Архітектурні та технічні рішення проєкту. Кожне рішення має ID,
дату, розглянуті альтернативи та обґрунтування.

## DEC-003: Архітектурний патерн
- **Дата:** 2026-04-13
- **Контекст:** Вибір архітектури для PIM-системи (internal tool, 5 users, MVP)
- **Альтернативи:** Monolith, Modular Monolith, Microservices
- **Рішення:** Monolith
- **Обґрунтування:** 5 users, 1 developer, MVP з дедлайном 1 день. Zero overhead.
- **Trade-off:** Менша гнучкість для масштабування (не потрібна)
- **Хто прийняв:** agent + user

## DEC-002: Frontend стек
- **Дата:** 2026-04-13
- **Контекст:** Вибір frontend framework для SPA internal tool
- **Альтернативи:** React + Vite, Vue + Vite, Next.js
- **Рішення:** React + Vite + TypeScript + shadcn/ui + Tailwind v4 + Zustand + react-i18next
- **Обґрунтування:** Стандарт Daedalus, shadcn/ui для Material Design, SPA без SSR (внутрішній інструмент)
- **Trade-off:** Більший bundle ніж Vue, але багатша екосистема
- **Хто прийняв:** agent + user

## DEC-001: Backend стек
- **Дата:** 2026-04-13
- **Контекст:** Вибір backend framework для PIM з AI-інтеграціями
- **Альтернативи:** FastAPI (Python), Hono (Node), Django
- **Рішення:** FastAPI + Python 3.12 + SQLAlchemy 2.x + Pydantic v2 + Alembic
- **Обґрунтування:** Async, нативні AI SDK (anthropic, openai, google-generativeai), auto OpenAPI docs, стандарт Daedalus
- **Trade-off:** Python повільніший за Node для CPU-bound, але AI calls — IO-bound
- **Хто прийняв:** agent + user

---

(нові рішення додаються зверху)
