.PHONY: install dev test lint format migrate rollback seed reset health

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --port 8000

test:
	pytest -v

lint:
	ruff check . && ruff format --check .

format:
	ruff check --fix . && ruff format .

migrate:
	alembic upgrade head

rollback:
	alembic downgrade -1

seed:
	python seed.py

reset:
	alembic downgrade base && alembic upgrade head && python seed.py

health:
	curl -f http://localhost:8000/health || exit 1
