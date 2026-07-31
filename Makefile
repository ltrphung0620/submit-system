.PHONY: setup up down migrate seed format-check lint typecheck test test-integration test-concurrency test-realtime test-e2e build audit ci clean-verify verify-export

setup:
	python -m venv .venv
	.venv/Scripts/python -m pip install -e "./backend[dev]"
	cd frontend && npm ci

up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	docker compose run --rm api alembic upgrade head

seed:
	python scripts/create_synthetic_fixtures.py

format-check:
	cd backend && ../.venv/Scripts/python -m ruff format --check .
	cd frontend && npm run format:check

lint:
	cd backend && ../.venv/Scripts/python -m ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && ../.venv/Scripts/python -m mypy app
	cd frontend && npm run typecheck

test:
	cd backend && ../.venv/Scripts/python -m pytest -m "not integration and not concurrency and not realtime" --cov=app --cov-report=term-missing
	cd frontend && npm run test

test-integration:
	cd backend && ../.venv/Scripts/python -m pytest -m integration

test-concurrency:
	cd backend && ../.venv/Scripts/python -m pytest -m concurrency

test-realtime:
	cd backend && ../.venv/Scripts/python -m pytest -m realtime

test-e2e:
	cd frontend && npm run test:e2e

build:
	cd frontend && npm run build
	docker compose build

verify-export:
	cd backend && ../.venv/Scripts/python -m pytest tests/unit/test_export.py

audit:
	.venv/Scripts/python -m pip check
	.venv/Scripts/python -m pip_audit -r backend/requirements.lock
	cd frontend && npm audit --audit-level=high

ci: format-check lint typecheck test test-integration test-concurrency test-realtime build verify-export

clean-verify:
	docker compose down -v
	docker compose up --build -d --wait
	docker compose ps
