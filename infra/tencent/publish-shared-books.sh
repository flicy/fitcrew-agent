#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$HERE/runtime/.env.runtime"
OWNER_FILE="$HERE/runtime/owner/owner-bootstrap.json"
COMPOSE="docker compose --env-file $ENV_FILE -f $HERE/compose.yaml"

test -s "$ENV_FILE"
test -s "$OWNER_FILE"
$COMPOSE exec -T api python scripts/publish_shared_books.py \
    --owner-record /owner-runtime/owner-bootstrap.json
