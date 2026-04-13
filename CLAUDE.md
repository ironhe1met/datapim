# DataPIM

## About

- **Category:** business
- **Created:** 2026-04-13
- **Pipeline:** app
- **Platform:** web
- **Stack:** (fill in during architect stage)
- **Goal:** (fill in during discovery)

## Architecture

(describe during architect stage)

## Development

```bash
cp .env.example .env            # заповни змінні
docker compose up -d            # підняти сервіси
make migrate                    # застосувати міграції
make seed                       # seed admin
make dev                        # запустити dev-сервер
```

## Commands

```bash
make test                       # запустити тести
make lint                       # linting + formatting
make reset                      # знести все і підняти заново
make health                     # перевірити що сервіс живий
```

## Notes

- `inbox/` — папка для вхідних XML-файлів та картинок з 1С
