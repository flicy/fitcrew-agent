#!/bin/bash
set -euo pipefail
umask 077

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$HERE/runtime/.env.runtime"
KEY_FILE="$HERE/runtime/backup.key"
BACKUP_DIR="$HERE/runtime/backups"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$HERE/compose.yaml")
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUTPUT="$BACKUP_DIR/bodyos-$STAMP.sql.enc"

test -s "$KEY_FILE"
mkdir -p "$BACKUP_DIR"
PARTIAL=$(mktemp "$BACKUP_DIR/.bodyos-$STAMP.XXXXXX.partial")
trap 'rm -f -- "$PARTIAL"' EXIT
"${COMPOSE[@]}" exec -T db pg_dump --no-owner --no-acl -U bodyos bodyos \
    | openssl enc -aes-256-cbc -pbkdf2 -salt -pass "file:$KEY_FILE" -out "$PARTIAL"
mv -- "$PARTIAL" "$OUTPUT"
find "$BACKUP_DIR" -type f -name 'bodyos-*.sql.enc' -mtime +7 -delete
echo "Encrypted database backup created; content and path omitted from logs."
