# DataPIM — Roadmap

Живий документ. Оновлюється після кожного `/approve`.

---

## Поточна версія: v0.0.0

---

## Версії

| Версія | Що входить | Done коли | Статус |
|--------|-----------|-----------|--------|
| v1.0.0 | Повний workflow: імпорт, каталог, AI, ревю, експорт | 2026-04-14 | in_progress |
| v2.0.0 | B2B модуль: вхід партнерів, кабінет, замовлення | TBD | pending |
| v3.0.0 | SaaS, EN UI, аналітика, розширені permissions | TBD | pending |

---

## Деталі по версіях

### v1.0.0 — PIM Core

**Мета:** Повний цикл даних — від XML з BUF до збагачених карток і XML-експорту для партнерів.

| Компонент | Статус |
|-----------|--------|
| XML-імпорт (товари + категорії + картинки) | pending |
| Auth (JWT) + RBAC (admin, operator) | pending |
| Управління користувачами (CRUD, invite) | pending |
| Каталог товарів (список, фільтри, пошук) | pending |
| Управління категоріями (ієрархія, CRUD) | pending |
| Картка товару (повне редагування) | pending |
| AI-агент: текстове збагачення (опис, характеристики, SEO) | pending |
| AI-агент: генерація зображень | pending |
| Модуль ревю (AI → operator → production) | pending |
| XML-експорт для партнерів (2 файли, публічний URL) | pending |
| Dark/Light mode | pending |
| i18n-архітектура (UK only, ready for EN) | pending |

### v1.1 — Post-MVP покращення

**Філософія enrichment** (обговорено 2026-04-15):
BUF дані сирі — категорії = бренди, відсутні brand-поля, нема структури.
Архітектурно вже маємо рішення (override pattern R-017 + buf_category/custom_category).
Залишилось дати оператору **інструменти масового збагачення**, щоб привести 11k+ товарів
до партнерського каталогу з чистою таксономією, повними брендами і описами.

#### Bulk Tools

| Компонент | Статус | Примітки |
|-----------|--------|----------|
| **Quick-win:** `POST /api/products/bulk-update` | pending | Filter (buf_category_id рекурсивно по дітях) + set (custom_*); admin only; dry_run preview; ліміт 5000 рядків. Дозволить за 5-10 curl викликів закрити топ брендів. |
| **UI bulk edit на /products** | pending | Чекбокси на рядках → modal "змінити для N товарів" → preview → commit. |
| **Bulk import з CSV/Excel** | pending | Експорт каталогу → редагуєш у Excel → upload назад. Колонки: internal_code (key), custom_brand, custom_category_name, custom_country, description. |
| **"Promote BUF category to brand"** | pending | Кнопка на BUF-категорії: "Це бренд" → проставляє `custom_brand=<назва>` всім товарам цієї категорії та її підкатегорій рекурсивно. |
| **Bulk reset** | pending | Зворотня операція: скинути custom_* для виборки. |

#### Enrichment Monitoring

| Компонент | Статус | Примітки |
|-----------|--------|----------|
| Сторінка `/enrichment` | pending | Прогрес: % без бренду, без custom_category, без опису, без зображення. Клік → відфільтрований список товарів. |
| Filter на /products: "needs enrichment" | pending | Quick-filters: без custom_brand / без custom_category / без description / без image. |
| Дельта останнього імпорту | pending | "Нові товари без бренду: 12", "Нові BUF категорії: 8". Видно що принесла остання синхронізація. |

#### XML Export Control

| Компонент | Статус | Примітки |
|-----------|--------|----------|
| Per-category toggle "не відправляти в XML" | done v1.0 | `Category.exclude_from_export` + UI toggle (Eye/EyeOff). Категорія + всі діти + усі товари рекурсивно випадають з `/export/*.xml` і з `export_settings` лічильників. |
| Per-product toggle "не експортувати" | pending | На випадок одиничних виключень (тестові, застарілі). |

#### Two-tier Taxonomy UX (запис на 2026-04-15)

**Концепція.** Той самий патерн, що в карточці товару (BUF read-only зверху,
custom-збагачення знизу) — застосувати і до сторінки `/categories`.

| Компонент | Статус | Примітки |
|-----------|--------|----------|
| Tab "BUF" — read-only дерево імпортованих категорій | pending | Видно як є з фіду. Можна тільки toggle `exclude_from_export` (вже є) і дивитись що там за товари. Створювати/видаляти не можна — це BUF. |
| Tab "Збагачення" — повноцінний CRUD над нашою чистою таксономією | pending | Тут оператор будує власну ієрархію ("Електроінструмент → Дрилі → Ударні"). Тільки категорії з `external_id LIKE 'USER-%'`. |
| Backend filter `?source=buf\|custom\|all` на `/api/categories` | pending | За замовчуванням `all` (поточна поведінка). UI tabs шлють відповідне значення. |
| Перегляд "куди потрапляє товар" у обох таксономіях | pending | На карточці товару — два рядки: "BUF: Товар → Електро → JET", "Збагачена: Електроінструмент → Дрилі → Ударні". |
| Bulk reassign з BUF tab → у Збагачення tab | pending | Інтегрується з bulk-update endpoint (вже є). UI: "вибрати BUF категорію → перенести всі товари у [нашу категорію X]". |

#### Інше

| Компонент | Статус | Примітки |
|-----------|--------|----------|
| Ручне створення товару (не тільки з BUF) | pending | Scope відкладено з v1.0 по R-020. |
| Приховати порожні кореневі категорії | pending | Зараз "Удалённые" залишається видимою навіть без дітей. |
| Soft-delete BUF категорій що зникли з фіду | pending | Якщо категорія відсутня у XML 7+ днів — позначити неактивною. Не fyzilly видаляти (бо overrides). |
| Вирішити долю `POST /api/categories` (QA #m-1) | pending | R-015 каже "category import-driven, no create". Або видалити endpoint + seed "Main" у міграції, або додати в spec + `DELETE`. Зараз endpoint є, DELETE нема. |
| Image upload приймає `is_primary` як form field (QA #m-2) | pending | Зараз перше фото автоматично primary. Треба `is_primary: bool \| None = Form(None)` у `images.py:upload_image`. |
| `ProductListItem.quantity` — або drop, або додати в api_spec (QA #m-3) | pending | XML export навмисно ховає quantity від партнерів (R-004). Якщо dev випадково засеріалізує ProductListItem → quantity протіче. |
| Документувати "SKU не унікальний" (QA #m-4) | pending | У BUF фіді 149 дублів SKU. Партнери-імпортери можуть подвоїти товари. Додати нотатку в devops_runbook або `.ai/api_spec.md`. |
| Cleanup тестових артефактів з QA (QA requires-human) | pending | Одна orphan категорія `QA-PROBE-CAT`, 2 orphan image files в `uploads/`. Безпечно видалити перед prod. |
| Login error wording — спец vs реалізація (QA #C-11) | pending | PRD/spec каже два різні повідомлення ("користувача нема" / "невірний пароль"); реалізація віддає одне ("Невірний email або пароль") — security best practice. Треба оновити PRD. |
| Dashboard 6 COUNT → 1 CTE-запит (QA #i-7) | pending | Зараз ~50мс на порожній БД. При зростанні до 100k+ товарів треба оптимізувати. |
| Swap `python-jose` → `pyjwt` (QA #i-3) | pending | `python-jose` використовує deprecated `datetime.utcnow()` — зламається в Python 3.13. |
| Прибрати `@pytest.mark.asyncio` з sync тестів (QA #i-2) | pending | 6 sync тестів у `test_import.py` з непотрібним маркером — cosmetic warnings. |

### v1.2 — AI Enrichment

**Мета:** автоматизувати збагачення для решти товарів які bulk-tools не покриють.

| Компонент | Статус | Примітки |
|-----------|--------|----------|
| AI-агент категоризації | pending | На вхід: name + buf_brand + uktzed. На вихід: пропозиція custom_brand + custom_category + опис. Batch'ами по 50. |
| Review workflow | pending | Архітектурно готовий (`ai_reviews` таблиця). UI: список pending → approve/reject/edit → запис у custom_*. |
| "Збагатити категорію" одним кліком | pending | Запускає batch AI на всі товари в категорії з progress bar. |
| AI генерація зображень для товарів без фото | pending | Flux/DALL-E з review workflow. Cost guardrails: денний ліміт. |
| Settings: AI provider toggle + API keys | pending | Multi-provider: Anthropic / OpenAI / Google. |

---

## Overnight QA + DevOps queue (план на вечір v1.0 → v1.1)

Коли Daedalus v2 (autonomous queue) буде готовий, запустити по черзі чотири
задачі з патерном two-phase:

| # | Time | Task | Boundary |
|---|------|------|----------|
| 1 | 00:30 | **QA audit** | read-only: RBAC матриця (4 ролі × 12 екранів), AC перевірка, contract tests проти api_spec.md, UI smoke. Пише `.ai/qa_report.md`. |
| 2 | 02:30 | **QA fix** | Читає qa_report.md, фіксить тільки явні баги. Per-fix commit + pytest + tsc. Рефакторів і нових фіч не робити. Judgment → "requires-human" в звіті. |
| 3 | 05:00 | **DevOps prep** | Готує prod Dockerfile + docker-compose.prod.yml, nginx.conf з SSL, systemd unit, backup script, GitHub Actions CI (build+test), `.env.example` для prod, `.ai/devops_runbook.md`. **Не деплоїть, не SSH, не push.** |
| 4 | 07:30 | **Overnight summary** | Читає qa_report.md + devops_runbook.md + git log → `.ai/overnight_summary.md`: що пофіксили, що залишилось для людини, наступні кроки. |

**Загальні правила для всіх автономних:**
- Кожен cron-firing = свіжа Claude сесія (власний rate limit)
- Стан через файли в `.ai/` — це queue між тригерами
- Якщо попередній впав у ліміт → наступний підхопить по стану у `queue.md`
- Commit після кожної логічної зміни з referenced issue у `qa_report.md`

### v2.0.0 — B2B Module

**Мета:** Партнери отримують доступ до системи — логін, перегляд каталогу, замовлення.

| Компонент | Статус |
|-----------|--------|
| Реєстрація/вхід для партнерів | pending |
| Особистий кабінет партнера | pending |
| Каталог для партнерів (ціни, наявність) | pending |
| Замовлення / кошик | pending |
| Multi-tenancy для клієнтів | pending |

### v3.0.0 — Scale

**Мета:** Розширення до SaaS, аналітика, мультимовність.

| Компонент | Статус |
|-----------|--------|
| Англійський UI | pending |
| Гнучка система permissions | pending |
| Аналітика / статистика | pending |
| SaaS mode (multi-company) | pending |
| Роль manager (view-only) | pending |
