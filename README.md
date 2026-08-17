# Submission API Desk

A public API and shared review UI for KIS, QA, and TRAKE submissions. Another system can submit JSON without first importing a query ZIP. The backend automatically groups requests by case-insensitive `file_name`, preserves immutable per-group arrival order, maintains contiguous active priorities per query, broadcasts changes over WebSocket, stores optional base64 images as binary files, and exports the complete operational history as a Vietnamese-safe CSV.

Official Codabench export is deliberately disabled because `requirements.pdf` links to rules that were not publicly readable and the repository contains no accepted official fixture. See [BLOCKERS.md](BLOCKERS.md).

## Architecture

- React 19 + strict TypeScript + Vite UI served by Nginx.
- FastAPI, Pydantic, SQLAlchemy, Alembic API under `/api/v1`.
- Local SQL Server 2016 with atomic per-query `arrival_seq` and optimistic `version` checks.
- In-process versioned WebSocket broadcast for the single API instance in Compose.
- Local persistent image/export volume behind an `ImageStorage` interface.
- Preview exporter adapters, deterministic `submission/*.csv` ZIP builder, and reopen/parse self-validation.
- Separate fail-closed `KisCsvExporter`, `QaCsvExporter`, and `TrakeCsvExporter` boundaries backed by `OfficialFormatProvider`.

More detail is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Requirements

- SQL Server available as `ltrphung`, with Windows Authentication enabled.
- Microsoft ODBC Driver 17 for SQL Server.
- Python 3.12+ and Node.js 22+.
- PowerShell examples below assume Windows; equivalent POSIX commands work with `.venv/bin/python`.

## Run locally on Windows

Prepare the database and apply Alembic migrations from the repository root:

```powershell
.\.venv\Scripts\python.exe .\scripts\create_local_database.py
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Start the backend in that terminal:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Start the frontend in a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Open `http://localhost:5173`; interactive Swagger UI is at `http://localhost:8000/swagger.html` and the raw schema is at `http://localhost:8000/openapi.json`. The legacy `/docs` URL redirects to Swagger UI. Health probes are:

The API root (`http://localhost:8000`) redirects to Swagger UI. When `AUTH_MODE=api_key`, click **Authorize** and enter an API key; Swagger sends it as `X-API-Key` for protected operations.

```text
GET http://localhost:8000/api/v1/health/live
GET http://localhost:8000/api/v1/health/ready
```

Stop either development server with `Ctrl+C`. The application never creates tables at runtime; apply schema changes through Alembic.

## Local development setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
Set-Location frontend
cmd /c npm ci
Set-Location ..
```

## Synthetic development data

Generate clearly labeled, non-official fixtures:

```powershell
python .\scripts\create_synthetic_fixtures.py
```

Upload `test-fixtures/synthetic-query-pack.zip` in the UI or with curl:

```bash
curl -X POST http://localhost:8080/api/v1/query-sets/import \
  -F "upload=@test-fixtures/synthetic-query-pack.zip"
```

Importer policy: strict ZIP, recursive `.txt`, UTF-8/UTF-8 BOM, no duplicate canonical basename, maximum 5 MiB upload, 500 entries, 20 MiB extracted content, and suspicious compression-ratio rejection. Unknown suffixes import as `unknown` and cannot accept candidates.

## Public submission API

The preferred integration endpoint is:

```text
POST /api/v1/submissions
```

`POST /api/v1/results` remains as a backward-compatible alias. A new `file_name` automatically creates a UI group and stores its required `query_content`; later requests with the same canonical name join that group in `arrival_seq` order. The query type is inferred from the required `-kis`, `-qa`, or `-trake` suffix. Query ZIP upload is optional and can enrich matching groups with query text.

Submit requests to `POST /api/v1/submissions`. Reuse the same `file_name` to test arrival ordering.

### Request examples

KIS:

```bash
curl -X POST http://localhost:8080/api/v1/submissions -H "Content-Type: application/json" -d \
'{"file_name":"query-p1-1-kis","query_content":"Tìm khoảnh khắc một người bước vào cửa hàng.","img_id":24834,"video_id":"L21_V001","submitter":"Định"}'
```

QA:

```bash
curl -X POST http://localhost:8080/api/v1/submissions -H "Content-Type: application/json" -d \
'{"file_name":"query-p1-2-qa","query_content":"Địa danh xuất hiện trong hình thuộc tỉnh nào?","img_id":24834,"video_id":"L21_V001","answer":"Bình Định","submitter":"Định"}'
```

TRAKE:

```bash
curl -X POST http://localhost:8080/api/v1/submissions -H "Content-Type: application/json" -d \
'{"file_name":"query-p1-3-trake","query_content":"Theo dõi chiếc xe màu đỏ qua các khung hình.","img_id":[24834,25230,25432],"video_id":"L21_V001","submitter":"Định"}'
```

Fields use strict JSON types: booleans and numeric strings are not accepted as frame integers. PATCH requires `expected_version`; DELETE requires `?expected_version=N`. A stale version returns 409 instead of silently overwriting.

`arrival_seq` is immutable history within each query. Active `priority` is also scoped to each query and is compacted to `1..N` after a deletion; a later request receives priority `N+1` without reusing or changing historical `arrival_seq` values.

### Optional base64 image

Add `image_base64` and optionally `image_mime_type`. Raw base64 and data URLs are accepted. The decoded content must be JPEG, PNG, or WebP and at most 5 MiB. Magic bytes are authoritative; binary goes to the persistent volume and only MIME/size/SHA-256/opaque key go to SQL Server.

```json
{
  "file_name": "query-p1-1-kis",
  "query_content": "Tìm khoảnh khắc một người bước vào cửa hàng.",
  "img_id": 24834,
  "video_id": "L21_V001",
  "submitter": "Định",
  "image_base64": "data:image/png;base64,iVBORw0KGgo...",
  "image_mime_type": "image/png"
}
```

## API keys for Salamanders and the shared UI

Development defaults to `AUTH_MODE=disabled`. Production should use:

```dotenv
AUTH_MODE=api_key
SALAMANDERS_KEY=<random-secret-used-only-by-the-salamanders-backend>
UI_SHARED_KEY=<different-random-secret-entered-on-the-ui-login>
PERMISSION_MODE=all_members
```

Generate each secret independently with an approved secret manager or
`python -c "import secrets; print(secrets.token_urlsafe(32))"`; never commit
them. Both clients send their own value as `X-API-Key`. The backend derives
the stored source (`Salamanders` or `UI`) from the key and does not trust the
body `submitter`. The shared UI key is validated by `/api/v1/auth/me`, saved in
the browser's local storage after login, and removed on logout. `all_members`
allows the review UI to edit results received from Salamanders. API keys and
base64 are never logged.

## Realtime

Connect to `ws://localhost:8080/api/v1/ws`. Events use:

```json
{"schema_version":1,"event":"created","occurred_at":"<UTC>","data":{}}
```

Events are `created`, `updated`, `deleted`, and `query_set_imported`. The UI reconnects with exponential backoff and re-fetches state after every reconnect. HTTP responses and WebSocket events are reconciled by result ID, so one change does not create duplicate rows.

## Export

```text
GET  /api/v1/exports/history.csv
GET  /api/v1/exports/status
GET  /api/v1/exports/validate
POST /api/v1/exports/preview
POST /api/v1/exports/official
GET  /api/v1/exports/{id}/download
```

`history.csv` contains every received submission record, including soft-deleted rows, in receive-time order. It is UTF-8 with BOM for Vietnamese-safe spreadsheet opening and is explicitly an **operational history file, not an official Codabench submission**.

Preview output is UTF-8 with BOM under `submission/`, contains every active structurally valid candidate in priority order, has no header row, and is visibly marked `UNVERIFIED`. KIS rows contain `video_id,img_id`; QA rows contain `video_id,img_id,answer`; TRAKE rows contain `video_id` followed by each ordered `img_id` in its own CSV column. For example:

```csv
L21_V001,24834
L21_V001,24834,Bình Định
L21_V001,24834,25230,25432
```

Each file contains rows for only one query type. The builder reopens the ZIP, verifies exact entry paths, decodes every CSV, checks the type-specific field count, and validates every TRAKE frame value before making it downloadable.

Official output always returns HTTP 409 / `OFFICIAL_FORMAT_NOT_VERIFIED` until the user-provided row format, encoding/BOM, filename mapping, row limits, selection policy, and complete archive layout are verified against an organizer-accepted fixture and automated golden tests are added. Preview output must not be submitted as an organizer-compatible archive.

## Quality commands

```text
make format-check
make lint
make typecheck
make test
make test-integration
make test-concurrency
make test-realtime
make test-e2e
make build
make verify-export
make audit
make clean-verify
```

On Windows without GNU Make, run the commands in [Makefile](Makefile) directly. SQL Server tests require `DATABASE_URL` and `TEST_DATABASE_URL` pointing to a disposable SQL Server database. No integration test uses a fake database.

## Backup and restore

Use SSMS: right-click the `submission` database, choose **Tasks → Back Up**, and create a full `.bak` backup. Restore only while the application is stopped and after confirming the target database. Back up the local `storage` directory separately; database rows contain only storage keys, not image bytes.

## Troubleshooting

- **401:** set `X-API-Key` when `AUTH_MODE=api_key`.
- **UI login rejects the key:** only `UI_SHARED_KEY` is accepted by the UI;
  `SALAMANDERS_KEY` is valid only for the Salamanders backend.
- **409 `VERSION_CONFLICT`:** refetch and retry the intended edit against the latest version.
- **409 official export:** expected until the P0 questions in `BLOCKERS.md` are resolved.
- **413:** ZIP, extracted query data, request body, image, entry count, or compression ratio exceeded configuration.
- **422 import:** inspect the machine-readable `error.code`; invalid UTF-8, traversal, duplicate basename, unknown result type, and malformed image data are rejected without partial import.
- **Readiness fails:** confirm the `MSSQLSERVER` Windows service is running, then run `alembic upgrade head` and inspect the backend terminal.
- **No realtime:** check the UI connection badge and reverse-proxy WebSocket upgrade configuration; reconnect triggers a full refetch.
