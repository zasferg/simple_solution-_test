.PHONY: up down logs test test-unit lint format migrate

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker

test-unit:
	uv run pytest tests/unit

test:
	uv run --env-file .env.test pytest

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy app tests

format:
	uv run ruff check --fix .
	uv run ruff format .

migrate:
	docker compose run --rm api alembic upgrade head
