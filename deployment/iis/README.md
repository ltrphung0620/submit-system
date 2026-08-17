# IIS production target

This directory contains the IIS files for the production origin:

```text
http://171.244.37.116:18111
```

The IIS site serves the React build and proxies these paths to the single
Uvicorn process listening on `127.0.0.1:18112`:

```text
/api/*
/swagger.html
/redoc
/openapi.json
/docs
```

## Server configuration

1. Install IIS URL Rewrite, Application Request Routing (ARR), and WebSocket
   Protocol. Enable the ARR proxy at the server level.
2. Bind the IIS site to `171.244.37.116` on HTTP port `18111`.
3. Point the IIS site to `C:\apps\submit-system\current\web`.
4. Copy `.env.production.example` to
   `C:\apps\submit-system\shared\.env`, replace all placeholder secrets, and
   restrict its ACL to administrators and the API service account. Generate
   separate values for `SALAMANDERS_KEY` and `UI_SHARED_KEY`; do not reuse
   either value.
5. Run Uvicorn from `C:\apps\submit-system\current\backend`:

   ```powershell
   C:\apps\submit-system\current\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 18112 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1
   ```

6. Configure the GitHub `production` environment and a Windows self-hosted
   runner with the `iis-production` label before enabling CD.

The frontend intentionally uses the relative `/api/v1` base path. No public IP
is compiled into its JavaScript, so the same artifact continues to work after
HTTPS or a domain is added.

The five UI users enter the same `UI_SHARED_KEY` on the login screen. The
browser stores it locally and sends it as `X-API-Key` on subsequent requests.
The separate `SALAMANDERS_KEY` stays only in the Salamanders backend
environment and is rejected by the UI login.

## Required GitHub production values

Variables:

```text
IIS_DEPLOY_ROOT=C:\apps\submit-system
IIS_SITE_NAME=SubmitSystem
IIS_APP_POOL=SubmitSystem
API_TASK_NAME=SubmitSystem-API
PUBLIC_BASE_URL=http://171.244.37.116:18111
PYTHON_EXE=C:\Program Files\Python313\python.exe
```

Secret:

```text
PRODUCTION_MIGRATION_DATABASE_URL
```

API keys are sent in clear text over plain HTTP. Add an HTTPS binding before
using real API keys over an untrusted network.
