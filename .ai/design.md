# UI/UX Design

## 1. Карта екранів

### Структура навігації

```
Login (/login) ─────→ Dashboard (/)
                           │
         ┌─────────────────┼──────────────────────┐
         │                 │                       │
    Products          Categories              AI & Reviews
    /products         /categories              /reviews
         │                                         │
    Product Detail                           Review Detail
    /products/:id                            /reviews/:id

         ┌─────────────────┐
         │    Admin Only    │
         ├─────────────────┤
         │ Users /users     │
         │ Import /import   │
         │ Settings /settings│
         └─────────────────┘

Error Pages: /404, /error
```

### Список екранів

| # | Екран | URL | Доступ (ролі) | Опис |
|---|-------|-----|---------------|------|
| 1 | Login | /login | public | Email + password auth |
| 2 | Dashboard | / | all | Stats, last import, pending reviews |
| 3 | Products | /products | all | Product list, filters, search, grid/table |
| 4 | Product Detail | /products/:id | all / edit: admin+operator | Card edit, images, AI, attributes |
| 5 | Categories | /categories | all / rename: admin+operator | Category tree, product filter |
| 6 | Reviews | /reviews | admin+operator+manager | AI review list |
| 7 | Review Detail | /reviews/:id | admin+operator+manager / action: admin+operator | Diff view, approve/reject |
| 8 | Users | /users | admin+manager(read) | User management |
| 9 | Import | /import | admin+manager(read) | Trigger import + logs |
| 10 | Settings | /settings | admin | AI providers, export URLs, profile |
| 11 | 404 | /404 | public | Page not found |
| 12 | Error | /error | public | Server error |

## 2. Дизайн-система

### Кольори

Meta Group brand — professional blue-gray.

| Роль | Light | Dark | Використання |
|------|-------|------|-------------|
| background | hsl(210 20% 98%) | hsl(222 47% 8%) | Фон сторінки |
| foreground | hsl(222 47% 11%) | hsl(210 20% 95%) | Основний текст |
| card | hsl(0 0% 100%) | hsl(222 47% 11%) | Картки, панелі |
| primary | hsl(217 91% 50%) | hsl(217 91% 60%) | Кнопки, акценти |
| secondary | hsl(214 32% 91%) | hsl(215 28% 17%) | Другорядні |
| muted | hsl(214 32% 91%) | hsl(215 28% 17%) | Підказки, disabled |
| destructive | hsl(0 84% 60%) | hsl(0 63% 40%) | Видалення, помилки |
| success | hsl(142 76% 36%) | hsl(142 70% 45%) | Успіх, in_stock |
| warning | hsl(38 92% 50%) | hsl(48 96% 53%) | Попередження |
| border | hsl(214 32% 91%) | hsl(215 28% 17%) | Рамки |

### Типографіка

Inter (body/headings) + JetBrains Mono (code). Google Fonts.

| Елемент | Шрифт | Розмір | Вага | Використання |
|---------|-------|--------|------|-------------|
| H1 | Inter | 2rem | 700 | Заголовки сторінок |
| H2 | Inter | 1.5rem | 600 | Секції |
| H3 | Inter | 1.25rem | 600 | Підсекції |
| Body | Inter | 1rem | 400 | Текст |
| Small | Inter | 0.875rem | 400 | Мітки, hints |
| Code | JetBrains Mono | 0.875rem | 400 | SKU, internal_code |

### Компоненти shadcn/ui

| Компонент | Кастомізація |
|-----------|-------------|
| Button | primary, secondary, destructive, ghost, outline |
| Input | з help text, error state |
| Textarea | auto-resize для description |
| Card | product cards, stat cards, info panels |
| Table | sortable headers, row click |
| Dialog | create/edit forms (md), AI trigger (sm) |
| AlertDialog | destructive confirms (sm) |
| Sheet | mobile sidebar, mobile filters |
| Badge | status indicators (in_stock, enrichment, review, role) |
| Toast (Sonner) | bottom-right, success/error/warning/info |
| Skeleton | loading states |
| DropdownMenu | row actions, user menu, reset field |
| Tabs | product detail sections |
| Select | filters, role picker, provider picker |
| Switch | dark/light toggle |
| Breadcrumb | product detail navigation |
| Tooltip | icon button labels |
| ScrollArea | category tree |
| Separator | sidebar sections |
| Checkbox | partial review approve |
| Label | form fields |

### Сітка

- Container: `max-w-[1400px] mx-auto px-4`
- Breakpoints: mobile (<768px), tablet (768–1024px), desktop (>1024px)
- Product grid: `sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
- Stat cards: `sm:grid-cols-2 lg:grid-cols-4`

### i18n

- Основна мова: `uk` (українська)
- Інші мови: none (i18n architecture ready for `en`)
- Формат ключів: `namespace.section.key`
  - `auth.login.title`, `auth.login.email`, `auth.login.submit`
  - `products.title`, `products.filters.in_stock`, `products.table.name`
  - `dashboard.stats.total`, `dashboard.stats.enriched`

### Favicon і meta

- Favicon: SVG, "D" lettermark in primary color
- Title format: `[Page] — DataPIM`
- OG: not needed (internal tool)

## 3. UI-патерни

### Layout і навігація

- **Desktop:** Sidebar left (w-60, collapsible to w-16 icon-only) + Header top (h-14)
- **Tablet:** Sidebar collapsed (w-16 icons)
- **Mobile:** Sidebar → Sheet drawer (hamburger ≡ in header)
- **Header:** Logo "DataPIM" left, right: dark/light Switch + User DropdownMenu (Profile, Logout)
- **Sidebar items:**
  - Dashboard (LayoutDashboard) — all
  - Товари (Package) — all
  - Категорії (FolderTree) — all
  - Ревю AI (CheckCircle + Badge count) — admin, operator, manager
  - --- Separator ---
  - Користувачі (Users) — admin, manager
  - Імпорт (Upload) — admin, manager
  - Налаштування (Settings) — admin
- **Active state:** primary bg + foreground text, border-left-2 primary
- **Breadcrumbs:** product detail (Товари → Категорія → Товар)
- **Sidebar footer:** version badge

### Forms

| Елемент | Стандарт |
|---------|---------|
| Required field | Asterisk `*` red |
| Validation | Inline під полем, text-destructive |
| When validate | On blur (first), on change (after first error) |
| Help text | Під полем, text-muted-foreground, 0.875rem |
| Submit button | Disabled while invalid, spinner + "Зберігаю..." |
| Success | Toast "Зміни збережено" |
| Cancel | Ghost button, revert values |

### Tables / Lists

| Елемент | Стандарт |
|---------|---------|
| Pagination | Footer: `‹ 1 2 3 ... 8 ›` + Select "50/page" |
| Sort | Arrow ↑↓ in header, single column |
| Filter | Row above table: search Input + Select dropdowns |
| Search | Input + Search icon, debounce 300ms |
| Empty (no data) | Icon + text + CTA button |
| Empty (filtered) | Icon + "Нічого не знайдено" + "Скинути фільтри" |
| Row actions | Click row → detail page |
| Loading | 5 Skeleton rows |
| Mobile | Table → Card list (stacked) |
| View toggle | Grid/Table icons (products only) |

### Toast / Feedback (Sonner)

| Дія | Toast | Duration |
|-----|-------|----------|
| Save | "Зміни збережено" (success) | 3s |
| Create | "[Entity] створено" (success) | 4s |
| Delete/Deactivate | "[Entity] деактивовано" (success) | 4s |
| Import trigger | "Імпорт запущено" (info) | 3s |
| AI trigger | "AI-збагачення запущено" (info) | 3s |
| Review approve | "Зміни прийнято" (success) | 4s |
| Review reject | "Зміни відхилено" (warning) | 4s |
| Error | "[Message]" (destructive) | 6s |

Position: bottom-right

### Dialogs

| Коли | Компонент | Розмір |
|------|-----------|--------|
| Deactivate user | AlertDialog | sm |
| AI enrich trigger | Dialog (provider select) | sm |
| AI generate image | Dialog (provider select) | sm |
| Create user | Dialog (form) | md |
| Edit user | Dialog (form) | md |
| Product edit | Inline on page | — |
| Review detail | Full page | — |
| Mobile filters | Sheet (bottom) | lg |

### Permission-aware UI

| Сценарій | Поведінка |
|----------|-----------|
| Menu item for wrong role | Hidden (not rendered) |
| Action button without rights | Hidden (not disabled) |
| URL of forbidden page | Redirect → Dashboard + toast "Доступ заборонено" |
| Read-only data | Show without edit controls |

### Loading

| Контекст | Патерн |
|----------|--------|
| First page load | Full Skeleton (sidebar + content) |
| Data list | 5 Skeleton rows / cards |
| Detail page | Skeleton card (fields + images) |
| Category tree | 8 Skeleton lines with indent |
| Submit button | Spinner inside + disabled |
| AI in progress | Spinner badge + "Збагачується..." |

### Empty States

| Тип | Icon | Текст | CTA |
|-----|------|-------|-----|
| Products (no data) | Package | "Каталог порожній" | "Запустити імпорт" (admin) |
| Products (filtered) | Search | "Нічого не знайдено" | "Скинути фільтри" |
| Reviews (none) | CheckCircle | "Немає очікуючих ревю" | — |
| Users | Users | "Поки тільки ви" | "Запросити користувача" |
| Import logs | Upload | "Імпортів ще не було" | "Запустити перший імпорт" |
| Product images | ImagePlus | "Немає зображень" | "Завантажити" / "Згенерувати AI" |
| Attributes | List | "Немає характеристик" | "Додати" / "Згенерувати AI" |

### Error Pages

| Код | Текст | CTA |
|-----|-------|-----|
| 404 | "Сторінку не знайдено" | "На головну" |
| 500 | "Щось пішло не так" | "Спробувати знову" / "На головну" |

## 4. Екрани

### 4.1 Layout (каркас)

- **URL:** all pages
- **Компоненти:** Sheet, ScrollArea, Button, Switch, DropdownMenu, Separator, Badge
- **Structure:**
  ```
  ┌──────────────────────────────────────────┐
  │ [≡] DataPIM                [🌓] [👤 ▼] │ Header (h-14)
  ├────────┬─────────────────────────────────┤
  │ Sidebar│         Content Area            │
  │ (w-60) │         (flex-1, p-6)           │
  │        │                                 │
  │ Items  │         {children}              │
  │        │                                 │
  │ v1.0.0 │                                 │
  └────────┴─────────────────────────────────┘
  ```
- **Mobile:** Sidebar → Sheet (hamburger ≡), Header: `[≡] DataPIM [🌓] [👤]`
- **Reviews badge:** red Badge with pending count (if > 0)
- **i18n:** `nav.dashboard`, `nav.products`, `nav.categories`, `nav.reviews`, `nav.users`, `nav.import`, `nav.settings`

### 4.2 Login (/login)

- **Доступ:** public (redirect to / if logged in)
- **Компоненти:** Card, Input, Button, Label
- **Elements:** Card (max-w-md mx-auto mt-20), Logo "DataPIM" + "Meta Group", Email Input, Password Input (show/hide), Submit Button "Увійти" (primary, full-width)
- **States:** default, loading (spinner + "Входжу..."), error (inline destructive), rate-limited
- **Mobile:** Card full-width, less padding
- **i18n:** `auth.login.title`, `auth.login.email`, `auth.login.password`, `auth.login.submit`, `auth.login.error.*`

### 4.3 Error pages (404, 500)

- **Layout:** Centered, no sidebar, flex-col items-center justify-center h-screen
- **404:** Large "404" + "Сторінку не знайдено" + Button "На головну"
- **500:** Large "500" + "Щось пішло не так" + "Спробувати знову" + ghost "На головну"
- **i18n:** `error.404.*`, `error.500.*`, `error.back_home`, `error.retry`

### 4.4 Dashboard (/)

- **Доступ:** all roles
- **Компоненти:** Card, Badge, Button, Skeleton
- **Elements:**
  - H1 "Панель управління"
  - Stat cards row (grid sm:2 lg:4): Товарів, В наявності (success), Збагачено (%), Очікують ревю (warning, clickable → /reviews)
  - Card "Останній імпорт": date, status Badge, created/updated/errors, Button "Запустити імпорт" (admin)
  - Card "AI активність": tasks today, "Без опису: X" (clickable → /products?enrichment_status=none)
  - Quick actions (admin): "Імпортувати", "Bulk збагачення"
- **Permission:** viewer — stats only; manager — +import read; operator — +reviews+AI; admin — all
- **Mobile:** stat cards grid-cols-2, cards stacked
- **i18n:** `dashboard.title`, `dashboard.stats.*`, `dashboard.import.*`, `dashboard.ai.*`

### 4.5 Products (/products)

- **Доступ:** all roles
- **Компоненти:** Input, Select, Table, Badge, Button, Skeleton, Tabs
- **Elements:**
  - H1 "Товари" + View toggle (Grid/Table)
  - Filters row: Search input, Category Select, In_stock Select, Enrichment Select, Review Select, Reset button
  - Table view: columns — Photo (40px), Name (sortable), SKU, Category, Price (sortable), In_stock Badge, Enrichment Badge
  - Grid view: Card — image + name + price + category + badges; grid sm:1 md:2 lg:3 xl:4
  - Pagination footer
  - Row/card click → /products/:id
- **Badges:** In_stock: success/muted. Enrichment: destructive "Пусто" / warning "Частково" / success "Повністю"
- **States:** loading (skeleton), empty (no data + CTA), empty (filtered + reset)
- **Mobile:** Card view only, filters → Sheet (bottom), search sticky top
- **i18n:** `products.title`, `products.search`, `products.filters.*`, `products.table.*`, `products.empty.*`

### 4.6 Product Detail (/products/:id)

- **Доступ:** all read / edit: admin+operator
- **Компоненти:** Card, Tabs, Input, Textarea, Button, Badge, Dialog, Breadcrumb, Tooltip, DropdownMenu, Checkbox
- **Elements:**
  - Breadcrumb: Товари → [Category] → [Product name]
  - Header: H1 name (resolved) + badges (in_stock, enrichment, pending_review)
  - Tabs: Основне | Зображення | AI | Характеристики
  - **Tab Основне:**
    - Left (lg:w-2/3): Card "Дані BUF" (readonly, muted bg): buf_name, buf_brand, buf_country, buf_price, buf_quantity, sku, internal_code, uktzed + Card "Збагачені дані" (editable): custom_name (placeholder=buf_name), custom_brand, custom_country, description (textarea), seo_title, seo_description (textarea) + Save/Reset buttons
    - Right (lg:w-1/3): Card info — Category, SKU (mono), Internal code (mono), UKTZED, Price, In_stock Badge
  - **Tab Зображення:** Image grid (sm:2 md:3), primary border, Upload/Generate AI buttons, DropdownMenu per image (Set primary/Delete)
  - **Tab AI:** "Збагатити AI" button, pending review warning Card, AI tasks history Table
  - **Tab Характеристики:** Key-Value table (+ source Badge manual/ai), Add button, inline edit
- **Permission:** manager+viewer — all tabs read-only, no edit/AI/delete
- **Mobile:** Tabs full-width, columns stacked, BUF card collapsible
- **i18n:** `product.breadcrumb`, `product.tabs.*`, `product.buf.*`, `product.enriched.*`, `product.images.*`, `product.ai.*`, `product.attributes.*`

### 4.7 Categories (/categories)

- **Доступ:** all read / rename: admin+operator
- **Компоненти:** ScrollArea, Button, Input, Badge, Tooltip
- **Elements:**
  - H1 "Категорії"
  - Search input (filter by name)
  - Tree view (ScrollArea): collapsible items — chevron + name + Badge(count), click → /products?category_id=X, double-click → inline rename (admin+operator)
  - Desktop right panel (lg:w-1/2): products filtered by selected category
  - "Bulk збагатити" button on selected category (admin)
- **Mobile:** Tree full-width, products → separate page
- **i18n:** `categories.title`, `categories.search`, `categories.empty`, `categories.products_count`

### 4.8 Reviews (/reviews)

- **Доступ:** admin, operator, manager
- **Компоненти:** Table, Badge, Select, Button
- **Elements:**
  - H1 "Ревю AI" + Badge (pending count)
  - Filter: Select status (All / Pending / Approved / Rejected / Partial)
  - Table: Product (name+thumb), Type Badge (text/image), Provider, Status Badge, Date
  - Row click → /reviews/:id
- **Status Badges:** warning "Очікує", success "Прийнято", destructive "Відхилено", secondary "Частково"
- **Permission:** manager — read only
- **Mobile:** Table → cards
- **i18n:** `reviews.title`, `reviews.filters.*`, `reviews.table.*`, `reviews.status.*`

### 4.9 Review Detail (/reviews/:id)

- **Доступ:** admin+operator+manager / actions: admin+operator
- **Компоненти:** Card, Badge, Button, Separator, Checkbox
- **Elements:**
  - Breadcrumb: Ревю AI → [Product name]
  - Header: product name + type Badge + provider Badge + status Badge
  - Diff view: Left Card "Поточне" (muted) vs Right Card "Пропозиція AI" (primary border), checkboxes per field for partial approve, changes highlighted (green=new, yellow=changed)
  - Image review (type=image): large preview + Accept/Reject/Regenerate
  - Actions (admin+operator): "Прийняти все" (primary), "Прийняти обрані" (secondary), "Відхилити" (destructive outline)
  - Info Card: provider, cost, duration, date
- **Permission:** manager — diff visible, no action buttons
- **Mobile:** Stacked diff, buttons sticky bottom
- **i18n:** `review.breadcrumb`, `review.current`, `review.proposed`, `review.approve.*`, `review.reject`, `review.info.*`

### 4.10 Users (/users)

- **Доступ:** admin (full) + manager (read)
- **Компоненти:** Table, Dialog, Button, Input, Select, Badge, AlertDialog
- **Elements:**
  - H1 "Користувачі" + Button "Запросити" (admin)
  - Table: Name, Email, Role Badge, Status Badge (active), Created, Actions
  - Actions (admin): Edit Dialog / Deactivate AlertDialog
  - Create Dialog: Email, Name, Password, Role Select → "Створити"
  - Edit Dialog: Email, Name, Password (optional), Role Select → "Зберегти"
  - Deactivate AlertDialog: "Деактивувати [name]?"
- **Permission:** manager — table without Actions, no "Запросити"
- **Mobile:** Table → cards
- **i18n:** `users.title`, `users.invite`, `users.table.*`, `users.form.*`, `users.deactivate.*`

### 4.11 Import (/import)

- **Доступ:** admin (full) + manager (read logs)
- **Компоненти:** Card, Table, Button, Badge
- **Elements:**
  - H1 "Імпорт"
  - Card "Запуск імпорту" (admin): info text + Button "Запустити імпорт" + loading state
  - Card "Історія імпортів": Table — Date, File, Status Badge, Created, Updated, Stock changed, Errors, expand for error_details
- **Permission:** manager — logs only, no trigger card
- **Mobile:** Cards stacked
- **i18n:** `import.title`, `import.trigger.*`, `import.logs.*`, `import.status.*`

### 4.12 Settings (/settings)

- **Доступ:** admin only
- **Компоненти:** Card, Input, Select, Button
- **Elements:**
  - H1 "Налаштування"
  - Card "AI провайдери": Select text provider (Anthropic/OpenAI/Google), Select image provider (Flux/DALL-E/Imagen)
  - Card "XML Експорт": readonly URLs + Copy buttons + stats
  - Card "Профіль": Name Input, Email (readonly), Password change
- **Mobile:** Cards stacked
- **i18n:** `settings.title`, `settings.ai.*`, `settings.export.*`, `settings.profile.*`

## 5. Notification UI

No separate notification page. In-app badges:
- Sidebar: "Ревю AI" → red Badge with pending count
- Dashboard: stat card "Очікують ревю" (clickable → /reviews)
- Product detail: warning banner if has_pending_review = true

## Handoff → frontend-skeleton

- **Порядок генерації:**
  1. Layout (sidebar, header, theme toggle, route guards)
  2. Error pages (404, 500)
  3. Login
  4. Dashboard
  5. Products (list + detail)
  6. Categories
  7. Reviews (list + detail)
  8. Users
  9. Import
  10. Settings
- **UI-патерни:** Section 3 — all patterns must be implemented consistently
- **Складні компоненти:**
  - Category tree (recursive, collapsible, with inline rename)
  - Review diff view (side-by-side, field checkboxes)
  - Product card with override display (buf vs custom)
  - Image gallery with primary selection and AI generation
- **Кастомні shadcn/ui:** Badge variants (success, warning), Stat Card
- **Критичні breakpoints:**
  - Sidebar: desktop (w-60) → tablet (w-16) → mobile (Sheet)
  - Product detail: 2 columns → 1 column at <1024px
  - Tables: → Card list at <768px
  - Filters: inline → Sheet at <768px
- **Error pages:** 404, 500 — must implement
- **Favicon:** SVG "D" lettermark, primary color
- **Permission mapping:**
  - admin: all visible
  - operator: hide Users, Import trigger, Settings
  - manager: hide edit buttons, AI triggers, show Users+Import read-only
  - viewer: hide Reviews, Users, Import, Settings, all edit buttons
