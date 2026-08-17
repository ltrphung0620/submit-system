FROM python:3.13.7-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg unixodbc \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        | sed 's#signed-by=/usr/share/keyrings/microsoft-prod.gpg#signed-by=/usr/share/keyrings/microsoft-prod.gpg#' \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml requirements.lock alembic.ini ./
COPY app ./app
COPY migrations ./migrations
RUN pip install --no-cache-dir -r requirements.lock \
    && pip install --no-cache-dir --no-deps .
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/storage \
    && chown -R appuser:appuser /app /data/storage
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
