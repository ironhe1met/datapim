# Product Requirements Document

## 1. Огляд продукту
- **Назва:** DataPIM
- **Elevator pitch:** DataPIM — це PIM-система для Meta Group, яка перетворює голі товарні дані з BUF в повноцінні продуктові картки завдяки AI-збагаченню, і автоматично віддає готовий каталог партнерам через XML.
- **Ціль:** Автоматизувати збагачення товарних карток контентом (описи, характеристики, зображення) і дистрибуцію каталогу партнерам
- **Цільова аудиторія:** Оператори Meta Group (1–5, нетехнічні) + адмін (технічний)

## 2. Ролі та матриця дозволів

### Ролі

| Роль | Опис | Реєстрація | Кількість |
|------|------|------------|-----------|
| admin | Повний доступ: користувачі, імпорт/експорт, налаштування AI, редагування, ревю | seed (перший запуск) | 1–2 |
| operator | Редагування карток/категорій, ревю AI-змін, перегляд каталогу | invite від admin | 1–3 |
| manager | Перегляд всього (каталог, AI reviews, логи імпорту), без редагування | invite від admin | 1–2 |
| viewer | Тільки перегляд товарів і категорій | invite від admin | 1–5 |

### Матриця дозволів

| Сутність | Дія | admin | operator | manager | viewer |
|----------|-----|-------|----------|---------|--------|
| Users | create / delete | ✓ | — | — | — |
| Users | read (list) | ✓ | — | ✓ | — |
| Users | update | ✓ (всіх) | own | own | own |
| Products | read (list, card) | ✓ | ✓ | ✓ | ✓ |
| Products | update (edit) | ✓ | ✓ | — | — |
| Categories | read (tree) | ✓ | ✓ | ✓ | ✓ |
| Categories | update (rename) | ✓ | ✓ | — | — |
| Images | read | ✓ | ✓ | ✓ | ✓ |
| Images | upload / delete | ✓ | ✓ | — | — |
| AI Tasks | trigger | ✓ | ✓ | — | — |
| AI Tasks | read (history) | ✓ | ✓ | ✓ | — |
| AI Reviews | approve / reject | ✓ | ✓ | — | — |
| AI Reviews | read (pending) | ✓ | ✓ | ✓ | — |
| Import | trigger | ✓ | — | — | — |
| Import | read logs | ✓ | — | ✓ | — |
| Export XML | configure / read | ✓ | — | ✓ (read) | — |
| Settings | read / update | ✓ | — | — | — |

## 3. Функціональні вимоги

### 3.1 Must Have (v1.0.0)

#### US-001: Авторизація
- **Як** користувач, **я хочу** увійти в систему по email + пароль, **щоб** отримати доступ до функціоналу відповідно до моєї ролі
- **Версія:** v1 | **Залежить від:** —
- **AC:**
  - GIVEN правильні credentials WHEN login THEN redirect to dashboard + JWT token
  - GIVEN невірний email WHEN login THEN error "Користувача не знайдено"
  - GIVEN невірний пароль WHEN login THEN error "Невірний пароль"
  - GIVEN 5 невдалих спроб за хвилину WHEN login THEN error "Забагато спроб, спробуйте пізніше"
  - GIVEN expired token WHEN запит THEN 401 + redirect to login

#### US-002: Управління користувачами (admin)
- **Як** admin, **я хочу** створювати, редагувати та видаляти користувачів, **щоб** контролювати доступ до системи
- **Версія:** v1 | **Залежить від:** US-001
- **AC:**
  - GIVEN admin WHEN create user (email, name, password, role) THEN user створено, може логінитись
  - GIVEN admin WHEN edit user (email, name, password, role) THEN дані оновлені
  - GIVEN admin WHEN delete user THEN user деактивований (soft delete), не може логінитись
  - GIVEN operator/manager/viewer WHEN спроба manage users THEN 403
  - GIVEN admin WHEN create user з існуючим email THEN error "Email вже зайнятий"

#### US-003: XML-імпорт товарів
- **Як** admin, **я хочу** імпортувати товари і категорії з XML-файлів (BUF), **щоб** наповнити каталог актуальними даними
- **Версія:** v1 | **Залежить від:** US-001
- **AC:**
  - GIVEN XML в inbox-папці WHEN trigger import THEN нові товари (in_stock=true) створюються, існуючі оновлюються
  - GIVEN товар є в БД але зник з XML WHEN import THEN in_stock=false, картка залишається
  - GIVEN товар повернувся в XML з in_stock=true WHEN import THEN in_stock=true, збагачення збережено
  - GIVEN дублікати категорій в XML WHEN import THEN upsert по ID, без дублів в БД
  - GIVEN формат ціни "1 015,16" WHEN import THEN парситься коректно як 1015.16
  - GIVEN невалідний XML WHEN import THEN error в лозі, імпорт не ламає існуючі дані
  - GIVEN operator/manager/viewer WHEN trigger import THEN 403
  - **Override pattern:** імпорт пише в `buf_*` поля, ніколи не чіпає `custom_*` поля
- **Примітки:** BUF кладе XML в shared folder. Імпорт 1+ разів/день.

#### US-004: Перегляд каталогу товарів
- **Як** operator, **я хочу** бачити список всіх товарів з фільтрами і пошуком, **щоб** швидко знаходити потрібні позиції
- **Версія:** v1 | **Залежить від:** US-003
- **AC:**
  - GIVEN авторизований user (будь-яка роль) WHEN відкриваю каталог THEN бачу список товарів з пагінацією
  - GIVEN фільтр по категорії WHEN apply THEN тільки товари цієї категорії
  - GIVEN фільтр по in_stock WHEN apply THEN тільки товари в наявності / не в наявності
  - GIVEN пошук по назві WHEN type THEN результати містять substring
  - GIVEN 0 товарів WHEN відкриваю каталог THEN empty state "Товари відсутні. Запустіть імпорт"
  - GIVEN неавторизований WHEN запит THEN 401

#### US-005: Перегляд дерева категорій
- **Як** operator, **я хочу** бачити ієрархію категорій, **щоб** навігувати по каталогу
- **Версія:** v1 | **Залежить від:** US-003
- **AC:**
  - GIVEN авторизований (будь-яка роль) WHEN відкриваю категорії THEN бачу дерево (parent → child)
  - GIVEN категорія має товари WHEN клікаю THEN бачу кількість товарів і перехід до фільтрованого списку
  - GIVEN admin/operator WHEN rename категорії THEN назва оновлена
  - GIVEN manager/viewer WHEN rename THEN 403

#### US-006: Редагування картки товару
- **Як** operator, **я хочу** редагувати картку товару (назва, опис, характеристики, бренд), **щоб** збагатити її контентом
- **Версія:** v1 | **Залежить від:** US-004
- **AC:**
  - GIVEN operator/admin WHEN edit card THEN зміни збережені в `custom_*` полях
  - GIVEN manager/viewer WHEN edit THEN 403
  - GIVEN порожнє обов'язкове поле (назва) WHEN save THEN validation error
  - GIVEN картка WHEN перегляд THEN показує `custom_*` якщо заповнено, інакше `buf_*`
  - GIVEN характеристики WHEN edit THEN можу додавати/видаляти/редагувати key-value пари
  - GIVEN operator WHEN "Скинути до оригіналу" THEN custom_* = NULL, показує buf_*
- **Примітки:** Override pattern — buf_name/custom_name, buf_brand/custom_brand, buf_country/custom_country

#### US-007: Управління зображеннями товару
- **Як** operator, **я хочу** завантажувати, видаляти та переглядати зображення товару, **щоб** картка мала візуальний контент
- **Версія:** v1 | **Залежить від:** US-006
- **AC:**
  - GIVEN operator/admin WHEN upload image (png/jpeg/webp) THEN зображення прив'язано до товару
  - GIVEN файл > 10MB WHEN upload THEN error "Файл занадто великий"
  - GIVEN невалідний формат WHEN upload THEN error "Підтримуються png, jpeg, webp"
  - GIVEN operator/admin WHEN delete image THEN зображення видалено
  - GIVEN manager/viewer WHEN upload/delete THEN 403
  - GIVEN кілька зображень WHEN перегляд THEN галерея з можливістю вибору головного

#### US-008: AI-збагачення картки (текст)
- **Як** operator, **я хочу** запустити AI-агента для генерації опису, характеристик і SEO, **щоб** автоматизувати збагачення
- **Версія:** v1 | **Залежить від:** US-006
- **AC:**
  - GIVEN operator/admin на картці товару WHEN trigger "Збагатити AI" THEN AI генерує draft (опис + характеристики + SEO)
  - GIVEN draft згенеровано WHEN перегляд THEN draft видно поруч з поточними даними (diff)
  - GIVEN AI provider недоступний WHEN trigger THEN fallback на наступний провайдер, якщо всі недоступні — error
  - GIVEN manager/viewer WHEN trigger THEN 403
  - GIVEN вже є pending AI review WHEN trigger знову THEN error "Вже є незатверджений draft"

#### US-009: AI-генерація зображень
- **Як** operator, **я хочу** згенерувати зображення товару через AI, **щоб** картка мала якісне фото навіть без фотографа
- **Версія:** v1 | **Залежить від:** US-007
- **AC:**
  - GIVEN operator/admin WHEN trigger "Згенерувати зображення" THEN AI створює зображення на базі назви + категорії
  - GIVEN зображення згенеровано WHEN перегляд THEN preview з кнопками "Прийняти" / "Відхилити" / "Перегенерувати"
  - GIVEN AI image provider недоступний WHEN trigger THEN fallback, якщо всі — error
  - GIVEN manager/viewer WHEN trigger THEN 403

#### US-010: Ревю AI-змін
- **Як** operator, **я хочу** переглядати AI-згенерований контент і затверджувати або відхиляти, **щоб** тільки якісні зміни потрапляли в production
- **Версія:** v1 | **Залежить від:** US-008, US-009
- **AC:**
  - GIVEN pending AI review WHEN operator/admin opens review THEN бачить diff: поточне vs AI-draft
  - GIVEN review WHEN approve THEN AI-draft замінює поточні дані в custom_* полях, статус = approved
  - GIVEN review WHEN reject THEN draft видалено, статус = rejected
  - GIVEN review WHEN partial approve THEN можна прийняти окремі поля, відхилити інші
  - GIVEN manager WHEN read review list THEN бачить, але не може approve/reject
  - GIVEN viewer WHEN access reviews THEN 403

#### US-011: XML-експорт для партнерів
- **Як** admin, **я хочу** мати публічний URL з XML-файлами каталогу (тільки in_stock), **щоб** партнери могли забирати актуальні дані
- **Версія:** v1 | **Залежить від:** US-003
- **AC:**
  - GIVEN публічний URL /export/products.xml WHEN GET THEN XML з усіма in_stock товарами (збагачені дані: custom ?? buf), без quantity
  - GIVEN публічний URL /export/categories.xml WHEN GET THEN XML з категоріями що мають in_stock товари
  - GIVEN товар не in_stock WHEN export THEN не включено
  - GIVEN no auth WHEN GET export THEN доступно (публічний endpoint)
  - GIVEN зміни в каталозі WHEN export THEN XML актуальний

#### US-012: Dark/Light mode
- **Як** користувач, **я хочу** перемикати тему (dark/light), **щоб** працювати комфортно
- **Версія:** v1 | **Залежить від:** US-001
- **AC:**
  - GIVEN будь-яка роль WHEN toggle theme THEN UI змінюється, preference зберігається
  - GIVEN наступний логін WHEN open THEN тема як було збережено

### 3.2 Should Have (v1.0.0 — якщо встигнемо)

#### US-013: Масове AI-збагачення
- **Як** admin, **я хочу** запустити AI-збагачення на вибрану категорію (bulk), **щоб** не клікати кожну картку
- **Версія:** v1 | **Залежить від:** US-008
- **AC:**
  - GIVEN admin WHEN select category + "Збагатити все" THEN AI tasks створюються для кожного товару в категорії
  - GIVEN bulk job WHEN перегляд THEN прогрес-бар (5/120 completed)
  - GIVEN operator WHEN bulk trigger THEN 403 (тільки admin)

#### US-014: Лог імпорту
- **Як** admin/manager, **я хочу** бачити історію імпортів (дата, кількість, помилки), **щоб** контролювати процес
- **Версія:** v1 | **Залежить від:** US-003
- **AC:**
  - GIVEN admin/manager WHEN open import logs THEN список імпортів: дата, нових, оновлених, помилок
  - GIVEN operator/viewer WHEN access THEN 403

### 3.3 Could Have (v1.x)

#### US-015: Налаштування AI-провайдерів
- **Як** admin, **я хочу** обирати який AI-провайдер використовувати, **щоб** контролювати якість і витрати
- **Версія:** v1.x | **Залежить від:** US-008

#### US-016: Історія змін картки
- **Як** operator, **я хочу** бачити хто і коли змінював картку, **щоб** відстежувати зміни
- **Версія:** v1.x | **Залежить від:** US-006

### 3.4 Won't Have (зараз)

- **B2B модуль** (логін партнерів, замовлення, кабінет) → v2
- **Англійський UI** → v2
- **Мобільний додаток** → v3
- **SaaS / multi-company** → v3
- **Аналітика продажів** → v3
- **Гнучка система permissions** → v2

## 4. User Flows

### Flow 0: Перший запуск / Onboarding
1. Admin відкриває сайт → login page
2. Вводить seed credentials (з .env) → dashboard
3. Dashboard порожній → banner "Каталог порожній. Імпортуйте дані з BUF"
4. Admin → Settings → Import → кладе XML в inbox → trigger import
5. Import завершено → dashboard показує: "Імпортовано 11 620 товарів, 1 477 категорій"
6. Admin → Users → Invite → створює operator

### Flow 1: Збагачення картки (основний)
1. Operator логіниться → dashboard (статистика: всього/збагачених/pending review)
2. Каталог → фільтр "без опису" → список незбагачених карток
3. Відкриває картку → бачить: назва (buf), sku, ціна, категорія, пусті поля
4. Натискає "Збагатити AI" → spinner → AI генерує draft
5. З'являється diff: ліворуч — поточне (пусто), праворуч — AI draft (опис, характеристики, SEO)
6. Operator переглядає → "Прийняти все" / коригує окремі поля → "Зберегти"
7. Картка в production зі збагаченим контентом (custom_* заповнені)
8. (Опціонально) "Згенерувати зображення" → preview → approve → картинка додана

### Flow 2: Admin flow
1. Admin логіниться → dashboard (імпорт, AI tasks, users, export stats)
2. Import: Settings → бачить дату останнього імпорту, кількість, помилки
3. Users: бачить список → може create/edit/delete
4. Export: бачить URL для партнерів, може перегенерувати XML
5. AI Settings: бачить статистику використання, обраний провайдер
6. Bulk: обирає категорію → "Збагатити все AI" → бачить прогрес

### Flow 3: Manager flow
1. Manager логіниться → dashboard (read-only статистика)
2. Каталог → бачить товари, може фільтрувати/шукати, але не редагувати
3. AI Reviews → бачить список pending/approved/rejected, але не може approve
4. Import logs → бачить історію імпортів

## 5. Концептуальна модель даних

### Діаграма зв'язків

```
[User] 1──N [AITask]
  │                │
  │           [AITask] 1──1 [AIReview]
  │                │
  │           [AITask] N──1 [Product]
  │
[Category] 1──N [Category]  (self-ref: parent → child)
  │
[Category] 1──N [Product]
  │
[Product] 1──N [ProductImage]
  │
[Product] 1──N [ProductAttribute]  (key-value характеристики)
  │
[ImportLog] (standalone)
```

### Деталі сутностей

| Сутність | Ключові поля (бізнес) | Зв'язки | Обсяг | Ріст |
|----------|----------------------|---------|-------|------|
| User | email, name, password_hash, role, is_active | has many AITasks | 1–10 | Фіксований |
| Category | external_id, name, parent, is_active | has many Products, self-ref parent | ~1 477 | Рідко |
| Product | internal_code, sku, buf_name, custom_name, buf_brand, custom_brand, buf_country, custom_country, buf_price, buf_in_stock, buf_quantity, buf_category_id, uktzed, is_active, description, seo_title, seo_description | belongs to Category, has many Images/Attributes/AITasks | ~11 600 | +десятки/тижд. |
| ProductAttribute | key, value | belongs to Product | Десятки тисяч | З збагаченням |
| ProductImage | file_path, is_primary, source (upload/ai/import), sort_order | belongs to Product | Тисячі | З збагаченням |
| AITask | type (text/image), provider, status, input, output, cost, duration | belongs to Product + User, has one AIReview | Десятки/день | Постійно |
| AIReview | status (pending/approved/rejected/partial), reviewed_by, reviewed_at, changes_applied | belongs to AITask | Десятки/день | Постійно |
| ImportLog | started_at, finished_at, file_name, products_created, products_updated, categories_upserted, errors_count, error_details | standalone | 1–5/день | Постійно |

### Override pattern (R-017)

Поля Product з подвійним джерелом:

| BUF поле | Override поле | Логіка відображення |
|----------|--------------|---------------------|
| buf_name | custom_name | custom_name ?? buf_name |
| buf_brand | custom_brand | custom_brand ?? buf_brand |
| buf_country | custom_country | custom_country ?? buf_country |
| buf_price | — | Тільки BUF |
| buf_in_stock | — | Тільки BUF |
| buf_quantity | — | Тільки BUF |
| buf_category_id | — | Тільки BUF |
| — | description | Тільки DataPIM |
| — | seo_title | Тільки DataPIM |
| — | seo_description | Тільки DataPIM |

## 6. Edge Cases

| Сценарій | Сутність | Поведінка |
|----------|----------|-----------|
| 0 товарів | Product | Empty state: "Каталог порожній. Імпортуйте дані" |
| 0 категорій | Category | Empty state: "Категорії відсутні. Запустіть імпорт" |
| Категорія без товарів | Category | Показувати в дереві, позначити "(0 товарів)" |
| Товар без категорії | Product | Помістити в "Без категорії" (fallback) |
| Товар без зображень | Product | Placeholder image, кнопка "Згенерувати AI" |
| 1000+ товарів в категорії | Product | Пагінація (50 per page) |
| Одночасне редагування | Product | Last write wins (1–5 users, low probability) |
| Видалення user | User | Soft delete (is_active=false), AI tasks/reviews зберігаються |
| AI task failed | AITask | status=failed, error message, retry button |
| Pending AI review + new trigger | AITask | Error "Вже є незатверджений draft" |
| Імпорт з битим XML | ImportLog | Rollback, error в лозі, існуючі дані не зачеплені |
| Товар зник з XML | Product | in_stock=false, збагачення (custom_*) збережено |
| Дублікат category_id | Category | Upsert — останній запис виграє |
| Ціна "1 015,16" | Product | Trim spaces, replace comma → 1015.16 |
| SKU з trailing spaces | Product | Trim при імпорті |
| Зображення > 10MB | ProductImage | Reject з error |
| XML-експорт при 0 in_stock | Export | Пустий XML з валідною структурою |
| "Скинути до оригіналу" | Product | custom_* = NULL, показує buf_* |

## 7. Нотифікації

| Подія | Канал | Отримувач | Коли |
|-------|-------|-----------|------|
| Імпорт завершено | in-app (dashboard) | admin | Після кожного імпорту |
| Імпорт з помилками | in-app (badge) | admin | Коли errors > 0 |
| AI review pending | in-app (badge/counter) | operator, admin | Коли є pending reviews |
| Bulk AI завершено | in-app (dashboard) | admin | Коли batch done |

Email — не в v1.

## 8. Нефункціональні вимоги

| Категорія | Вимога | Ціль |
|-----------|--------|------|
| API latency | p95 response time | < 500ms |
| Page load | LCP (каталог, картка) | < 3s |
| Uptime | availability | 99% |
| Навантаження | concurrent users | 5 |
| Import | парсинг 36K товарів | < 60s |
| AI enrichment | одна картка (text) | < 30s |
| DB size | за рік | < 5 GB |
| Безпека | password policy | min 8 chars, bcrypt |
| Безпека | JWT access token | 24h |
| Безпека | JWT refresh token | 7 днів |
| Безпека | API keys | в .env, не в БД |
| Export XML | генерація | < 10s для 11K товарів |

## 9. Інтеграції

| Сервіс | User story | Критичність | Fallback |
|--------|-----------|-------------|----------|
| BUF XML (folder) | US-003 | Must have | Логувати помилку, дані не чіпати |
| Anthropic API | US-008 | Must have | → OpenAI |
| OpenAI API | US-008 | Must have | → Google AI |
| Google AI (Gemini) | US-008 | Must have | → Anthropic |
| Flux Pro (Replicate) | US-009 | Must have | → DALL-E 3 |
| DALL-E 3 (OpenAI) | US-009 | Must have | → Imagen 3 |
| Imagen 3 (Vertex AI) | US-009 | Should have | Error message |

## 10. Мови та локалізація

- UI: українська (i18n-архітектура ready для EN)
- Дані товарів: українською
- Системні повідомлення: українською

## 11. Обмеження та залежності

### Залежності між stories

```
US-001 (Auth)
  ├── US-002 (Users)
  ├── US-012 (Theme)
  ├── US-003 (Import)
  │     ├── US-004 (Catalog)
  │     │     └── US-006 (Edit card)
  │     │           ├── US-007 (Images)
  │     │           │     └── US-009 (AI images)
  │     │           ├── US-008 (AI text)
  │     │           └── US-010 (Review) ← US-008, US-009
  │     ├── US-005 (Categories)
  │     ├── US-011 (Export XML)
  │     └── US-014 (Import logs)
  └── US-013 (Bulk AI) ← US-008
```

## 12. Метрики успіху

| Метрика | Ціль | Як вимірюємо |
|---------|------|--------------|
| Імпорт працює | 100% in_stock товарів в БД | count products vs XML |
| AI збагачення | >80% карток мають опис | count filled / total |
| Export актуальний | XML відповідає БД | diff export vs DB |
| Час на картку | < 2 хв з AI | user feedback |

## Handoff → Architect

- **Ролі:** 4 (admin, operator, manager, viewer)
- **Матриця дозволів:** секція 2 — контракт для RBAC
- **Концептуальна модель:** секція 5 — 8 сутностей, override pattern (R-017)
- **Кількість endpoints (оцінка):** ~25–30 (auth, users CRUD, products CRUD, categories, images, AI tasks, AI reviews, import, export, settings)
- **Обсяг даних:** ~11 600 products, ~1 477 categories, тисячі images, <5 GB/рік
- **Критичні інтеграції:** BUF XML (folder watch), 3 AI text APIs (Anthropic/OpenAI/Google), 3 AI image APIs (Flux/DALL-E/Imagen)
- **NFR targets:** p95 < 500ms, LCP < 3s, import < 60s, AI < 30s
- **Навантаження:** 5 concurrent users, 1–5 imports/day, десятки AI tasks/day
- **Override pattern:** buf_* (import overwrites) + custom_* (user/AI edits, import never touches)
- **Ризики:** стислий дедлайн, якість XML (дублікати, формати), AI API costs
- **Відкриті питання:** 0
- **Дедлайн:** 2026-04-14
