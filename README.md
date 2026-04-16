# DataPIM

Product Information Management (PIM) для Meta Group.
Імпорт товарів і категорій з BUF (ERP), збагачення (бренди, описи, фото, SEO),
публічний XML-експорт для B2B партнерів.

## Стек

| Компонент | Технологія |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2 |
| Frontend | React 19, Vite, TypeScript, Tailwind v4, shadcn/ui, Zustand, React Query |
| Database | PostgreSQL 16 |
| Runtime | Docker, Docker Compose |
| Proxy | nginx (внутрішній у Docker + зовнішній на proxy VPS) |

## Архітектура

```
Internet → [Proxy VPS: nginx + SSL] → [Internal Server: Docker stack, port 3000]
                                              ├── nginx (router)
                                              ├── backend (FastAPI)
                                              ├── frontend (React SPA)
                                              └── postgres
```

Дані з BUF (Windows Server) синхронізуються через SMB щогодини.

## Швидкий старт (deploy)

### 1. Внутрішній сервер

```bash
git clone https://github.com/ironhe1met/datapim.git /opt/datapim
cd /opt/datapim
cp deploy/.env.prod.example .env.prod
nano .env.prod    # DOMAIN, DEV_EMAIL, DEV_PASSWORD, DEV_NAME
sudo bash deploy/setup.sh
```

### 2. Proxy VPS

```bash
sudo bash deploy/proxy-setup.sh
# Спитає: домен, URL внутрішнього сервера, email для SSL
```

### 3. BUF синхронізація (опціонально)

```bash
sudo apt install cifs-utils
nano /opt/datapim/.buf-credentials    # username, password, domain
sudo bash deploy/sync-buf.sh --share //WIN-IP/export
# Cron: 0 * * * * /opt/datapim/deploy/sync-buf.sh >> /var/log/datapim-sync.log 2>&1
```

## Скрипти в `deploy/`

| Файл | Призначення |
|------|-------------|
| `setup.sh` | Встановлення на внутрішній сервер. Генерує секрети, build images, start stack, міграції, seed admin. Без SSL. |
| `proxy-setup.sh` | Налаштування proxy VPS. Генерує nginx конфіг, certbot SSL, reload nginx. |
| `sync-buf.sh` | Синхронізація XML + images з Windows BUF сервера через SMB. Mount → copy → unmount. Якщо Windows offline — тихо виходить. |
| `docker-compose.prod.yml` | Production stack: postgres + backend + frontend + nginx. Порт 3000. |
| `nginx-internal.conf` | Nginx конфіг всередині Docker. HTTP-only роутер: /api → backend, /* → frontend. |
| `nginx-prod.conf` | Legacy конфіг з SSL (для single-server deploy). |
| `Dockerfile.backend` | Multi-stage: builder + runtime, non-root user, healthcheck. |
| `Dockerfile.frontend` | Multi-stage: node build → nginx serve. |
| `backup.sh` | pg_dump + gzip + rotation (7 daily + 4 weekly). |
| `.env.prod.example` | Шаблон env. Заповни 4 поля, решту генерує setup.sh. |
| `systemd/datapim.service` | Опціональний systemd unit. |

## Конфігурація `.env.prod`

| Змінна | Обовʼязкова | Опис |
|--------|-------------|------|
| `DOMAIN` | ✅ | Піддомен без `https://` |
| `DEV_EMAIL` | ✅ | Email першого адміна |
| `DEV_PASSWORD` | ✅ | Пароль першого адміна (мін. 8 символів) |
| `DEV_NAME` | ✅ | Імʼя адміна (в лапках якщо з пробілом) |
| `POSTGRES_PASSWORD` | auto | Генерується setup.sh |
| `JWT_SECRET` | auto | Генерується setup.sh |
| `LISTEN_PORT` | ні | Порт на хості (default: 3000) |
| `UVICORN_WORKERS` | ні | Кількість воркерів (default: 2) |

## BUF синхронізація

### Файли

```
/var/lib/docker/volumes/datapim_inbox/_data/xml/
├── TMC.xml       ← товари (36k+)
├── TMCC.xml      ← категорії (2900+)
└── img/          ← зображення товарів
```

### Credentials файл `/opt/datapim/.buf-credentials`

```
username=BUF_WINDOWS_USER
password=BUF_WINDOWS_PASSWORD
domain=WORKGROUP
```

`chmod 600 /opt/datapim/.buf-credentials` — ніколи не комітити.

### Cron

```bash
# Синхронізація з BUF щогодини
0 * * * * /opt/datapim/deploy/sync-buf.sh --share //10.10.1.XX/export >> /var/log/datapim-sync.log 2>&1

# Бекап БД щодня о 3:00
0 3 * * * /opt/datapim/deploy/backup.sh

# Оновлення SSL сертифікату (на proxy VPS)
0 3 * * * certbot renew --quiet && nginx -s reload
```

## Оновлення (re-deploy)

### Як працює цикл розробки

```
Розробник (локально)
    ↓ git push
GitHub repo (ironhe1met/datapim)
    ↓ git pull (на кожному сервері)
Production сервери
```

1. Розробник пушить зміни в GitHub
2. На production сервері(ах) — `git pull` + restart
3. Міграції БД виконуються автоматично при старті backend
4. Якщо кілька серверів — кожен робить git pull незалежно

### Команди оновлення

**На сервері (SSH):**
```bash
cd /opt/datapim
git pull
sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d --build
```

**Або віддалено (з локального ПК):**
```bash
ssh web-mg "cd /opt/datapim && git pull && sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d --build"
```

`--build` перебудовує images тільки якщо код змінився (кеш Docker).
Якщо змін в коді нема (тільки конфіги) — без `--build`:
```bash
ssh web-mg "cd /opt/datapim && git pull && sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d"
```

### Відкат до попередньої версії

```bash
cd /opt/datapim
git log --oneline -5              # знайти потрібний commit
git checkout <commit-hash>
sudo docker compose -f deploy/docker-compose.prod.yml --env-file .env.prod up -d --build
```

## Корисні команди

```bash
# Статус контейнерів
sudo docker compose -f deploy/docker-compose.prod.yml ps

# Логи backend
sudo docker compose -f deploy/docker-compose.prod.yml logs -f backend

# Логи nginx
sudo docker compose -f deploy/docker-compose.prod.yml logs -f nginx

# Перезапуск backend
sudo docker compose -f deploy/docker-compose.prod.yml restart backend

# Ручний бекап
sudo bash deploy/backup.sh

# Відкрити shell в backend контейнері
sudo docker exec -it datapim-backend bash
```

## Відомі нюанси

| Проблема | Рішення |
|----------|---------|
| Ubuntu 20.04: `http2 on;` не працює в nginx 1.18 | Замінити на `listen 443 ssl http2;` (автоматично в proxy-setup.sh) |
| Ubuntu 20.04: apt repos "changed Origin" | `apt-get update --allow-releaseinfo-change -y` |
| Docker install: `docker-model-plugin` not found на focal | Ігнорувати, основні пакети ставляться |
| scp не працює (`subsystem request failed`) | Копіювати через `cat \| ssh` замість scp |
| certbot: nginx не стартує без cert | Тимчасовий HTTP-only конфіг → certbot → повний конфіг |
| DEV_NAME з пробілом ламає setup.sh | Обгорнути лапками: `DEV_NAME="Eugene Chernenko"` |

## Ліцензія

Proprietary — Meta Group. Не для публічного використання.
