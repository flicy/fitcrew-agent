#!/bin/sh
set -eu

case "${BODYOS_DATABASE_MIGRATION_MODE:-alembic}" in
    alembic)
        if [ -n "${BODYOS_DATABASE_SCHEMA:-}" ]; then
            echo 'Private schema requires managed CloudBase verification.' >&2
            exit 1
        fi
        alembic upgrade head
        ;;
    verify-cloudbase-pg)
        if [ "${BODYOS_DATABASE_SCHEMA:-}" != fitcrew ]; then
            echo 'CloudBase verification requires fitcrew schema.' >&2
            exit 1
        fi
        python -m bodyos_api.cloudbase_pg_runtime
        ;;
    *)
        echo 'Unsupported database migration mode.' >&2
        exit 1
        ;;
esac
exec uvicorn bodyos_api.app:app --host 0.0.0.0 --port 8000 --proxy-headers --no-access-log
