#!/bin/sh
set -eu

if [ "${BODYOS_ENVIRONMENT:-}" != production ] ||
   [ "${BODYOS_PUBLIC_AUTH_ENABLED:-}" != true ] ||
   [ "${BODYOS_PRIVATE_WECHAT_CLOUD_ENABLED:-}" != true ] ||
   [ "${BODYOS_DATABASE_SCHEMA:-}" != fitcrew ] ||
   [ "${BODYOS_DATABASE_MIGRATION_MODE:-}" != verify-cloudbase-pg ]; then
    echo 'CloudBase API requires explicit production, private WeChat and managed PG settings.' >&2
    exit 1
fi

case "${BODYOS_DATABASE_URL:-}" in
    postgresql://*|postgresql+psycopg://*) ;;
    *) echo 'CloudBase API requires a persistent PostgreSQL URL.' >&2; exit 1 ;;
esac

case "${BODYOS_PUBLIC_BASE_URL-UNSET}" in
    ''|https://*) ;;
    *) echo 'CloudBase API requires an explicit empty or HTTPS public URL.' >&2; exit 1 ;;
esac

[ -n "${BODYOS_WECHAT_APP_ID:-}" ] || { echo 'Missing BODYOS_WECHAT_APP_ID.' >&2; exit 1; }
[ -n "${BODYOS_WECHAT_APP_SECRET:-}" ] || { echo 'Missing BODYOS_WECHAT_APP_SECRET.' >&2; exit 1; }
[ -n "${BODYOS_IDENTITY_PEPPER:-}" ] || { echo 'Missing BODYOS_IDENTITY_PEPPER.' >&2; exit 1; }
[ -n "${BODYOS_ENCRYPTION_KEY:-}" ] || { echo 'Missing BODYOS_ENCRYPTION_KEY.' >&2; exit 1; }

exec /usr/local/bin/api-entrypoint
