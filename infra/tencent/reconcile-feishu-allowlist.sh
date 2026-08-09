#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$HERE/runtime/.env.runtime"
COMPOSE="docker compose --env-file $ENV_FILE -f $HERE/compose.yaml"

if [ ! -s "$ENV_FILE" ]; then
    echo "Private runtime environment is unavailable; reconciliation stopped." >&2
    exit 1
fi
for required_key in FEISHU_ALLOWED_USERS BODYOS_ENCRYPTION_KEY; do
    if ! grep -q "^${required_key}=[^[:space:]].*$" "$ENV_FILE"; then
        echo "Private runtime environment is unavailable; reconciliation stopped." >&2
        exit 1
    fi
done

$COMPOSE exec -T api python /app/scripts/reconcile_feishu_allowlist.py
$COMPOSE restart gateway

echo "Private Feishu allowlist reconciliation completed."
