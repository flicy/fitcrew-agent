FROM python:3.11.13-slim-bookworm

ARG UV_VERSION=0.8.13

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/apps/api \
    PATH=/app/.venv/bin:/usr/local/bin:/usr/bin:/bin \
    HOME=/tmp

WORKDIR /app
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/bodyos_api ./apps/api/bodyos_api
COPY apps/api/migrations ./apps/api/migrations
COPY alembic.ini ./
COPY infra/tencent/api-entrypoint.sh /usr/local/bin/api-entrypoint
COPY infra/tencent/cloudbase-api-entrypoint.sh /usr/local/bin/cloudbase-api-entrypoint
RUN uv sync --frozen --no-dev \
    && chmod 0555 /usr/local/bin/api-entrypoint /usr/local/bin/cloudbase-api-entrypoint

USER 10001:10001
EXPOSE 8000
CMD ["cloudbase-api-entrypoint"]
