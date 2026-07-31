# Test report

## Public submission API regression - 2026-07-24

Executed in Asia/Saigon after the public API feed, global `file_name` grouping, operational history CSV, migration, and UI changes.

| Command | Exit | Result |
|---|---:|---|
| PDF render + visual review, pages 1-5 | 0 | Public API, KIS/QA/TRAKE bodies, arrival priority, CSV, and suggested UI reconfirmed; page 5 blank |
| `python -m ruff format --check .` | 0 | 37 backend files formatted |
| `python -m ruff check .` | 0 | All backend lint checks passed |
| `python -m mypy app` | 0 | Strict mode; 22 source files passed |
| `pytest tests` | 0 | 43 passed, including direct submit without query import, history CSV, migration constraint, realtime, and concurrent first-request grouping |
| `alembic check` | 0 | No new upgrade operations detected |
| `npm run format:check` | 0 | All frontend files matched Prettier |
| `npm run lint` | 0 | ESLint passed |
| `npm run typecheck` | 0 | TypeScript strict build passed |
| `npm run test` | 0 | 6 Vitest tests passed, including the KIS/QA/TRAKE request builder and real public-endpoint form submission |
| `npm run build` | 0 | Production Vite build passed; 35 modules |
| `npm audit --audit-level=high` | 0 | 0 vulnerabilities |

The Playwright flow was updated to exercise `/api/v1/submissions` and the history CSV, but browser E2E was not rerun in this regression pass.

## Historical baseline - 2026-07-22

All counts and durations below come from the earlier baseline command output. The Python 3.14 local run emits a non-failing FastAPI/Starlette `TestClient` deprecation warning; the production container uses Python 3.13 and is healthy.

| Command | Exit | Passed | Failed | Skipped/deselected | Tool wall time | Result |
|---|---:|---:|---:|---:|---:|---|
| PDF render + visual review, pages 1-5 | 0 | 5 pages | 0 | 0 | n/a | Page 5 blank; page 4 table visually checked |
| `python scripts/create_synthetic_fixtures.py` | 0 | 2 artifacts | 0 | 0 | 1.5s | Synthetic ZIP + PNG created |
| `python -m ruff format --check .` (backend) | 0 | 32 files | 0 | 0 | 1.8s | Already formatted |
| `python -m ruff check .` (backend) | 0 | 32 files | 0 | 0 | 1.8s | All checks passed |
| `python -m mypy app` | 0 | 21 files | 0 | 0 | 3.2s | Strict mode, no issues |
| `pytest tests/unit --cov=... --cov-branch` | 0 | 31 | 0 | 0 | 6.5s | Domain/export branch coverage 95% |
| `pytest -m integration -q` | 0 | 5 | 0 | 33 deselected | 5.5s tool / 0.98s pytest | PostgreSQL 17, no fake DB |
| `pytest -m concurrency -q` | 0 | 1 | 0 | 37 deselected | 7.0s tool / 2.56s pytest | 50/50 stored; arrival sequence 1-50 unique |
| `pytest -m realtime -q` | 0 | 1 | 0 | 37 deselected | 5.0s tool / 0.46s pytest | Versioned create/update/delete events |
| `alembic upgrade head; alembic check` | 0 | 2 migrations | 0 | 0 | 5.0s | No new upgrade operations detected |
| `npm run format:check` | 0 | all matched files | 0 | 0 | 3.7s | Prettier pass |
| `npm run lint` | 0 | all source files | 0 | 0 | 6.5s | ESLint pass |
| `npm run typecheck` | 0 | project | 0 | 0 | 5.9s | TypeScript strict pass |
| `npm run test` | 0 | 4 | 0 | 0 | 8.0s tool / 3.03s Vitest | 2 files; realtime reducer 100% branch/statement/function/line |
| `npm run build` | 0 | 33 modules | 0 | 0 | 6.6s | Production bundle 199.30 kB JS (63.30 kB gzip) |
| `npm run test:e2e` (final clean stack) | 0 | 1 | 0 | 0 | 6.3s tool / 3.3s Playwright | Full desktop/mobile flow; ZIP opened; 0 console errors |
| `pip check` | 0 | dependency graph | 0 | 0 | 2.9s | No broken requirements |
| `pip_audit -r backend/requirements.lock` | 0 | production lock | 0 vulnerabilities | 0 | 47.2s | No known vulnerabilities found |
| `npm audit --audit-level=high` | 0 | lockfile | 0 vulnerabilities | 0 | 3.9s | No vulnerabilities |
| `docker compose down -v; docker compose up --build -d --wait` | 0 | 3 services | 0 | 0 | 67.3s | Fresh DB/storage; migration ran; API/DB/web healthy |
| `docker compose ps` after final E2E | 0 | 3 healthy | 0 | 0 | 1.5s | API :8000, DB :5432, web :8080 |

## Coverage

- Structural validation: 96% branch-inclusive coverage.
- Image decoding/storage: 96% branch-inclusive coverage.
- Query ZIP importer: 90% branch-inclusive coverage.
- Export modules: 97% branch-inclusive coverage after official adapter boundaries were added.
- Combined domain/import/image/export: 95% branch-inclusive coverage.
- Frontend realtime reconciliation reducer: 100% statements, branches, functions, and lines.
- UI interaction coverage is acceptance-oriented: QueryCard component test plus the complete Playwright flow. Overall source-line percentage is intentionally not presented as equivalent to E2E acceptance coverage.

## E2E assertions

The final Playwright flow starts from a clean migrated database, uploads `synthetic-query-pack.zip`, observes three query rows, sends KIS/QA/TRAKE through the API, observes realtime UI updates within the 2-second assertion window, adds a second candidate, edits without changing priority, confirms deletion, opens the image modal, validates/exports preview, reopens the ZIP, checks all three `submission/*.csv` entries, verifies “Bình Định” round-trip, verifies official export is disabled, switches to 390×844 mobile viewport, and asserts an empty browser-console error list.

## Security remediation during audit

The first audits found five npm advisories and twelve Python advisories. Patched pins were applied (`vite 7.3.6`, `vitest 3.2.7`, `playwright 1.61.1`, `fastapi 0.139.2`, `starlette 1.3.1`, `python-multipart 0.0.32`), all gates were rerun, and the final audits report zero known vulnerabilities.
