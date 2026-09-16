#!/bin/bash
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$HERE/runtime/.env.runtime"
KEY_FILE="$HERE/runtime/backup.key"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$HERE/compose.yaml")
BACKUP_FILE=${1:-}
RESTORE_DB=bodyos_restore_test

case "$BACKUP_FILE" in
    "$HERE"/runtime/backups/bodyos-*.sql.enc) ;;
    *) echo "Pass an encrypted backup from the private runtime backup directory." >&2; exit 1 ;;
esac
test -f "$BACKUP_FILE"
test -s "$KEY_FILE"
"${COMPOSE[@]}" exec -T db dropdb --if-exists -U bodyos "$RESTORE_DB"
"${COMPOSE[@]}" exec -T db createdb -U bodyos "$RESTORE_DB"
cleanup() {
    status=$?
    trap - EXIT
    if ! "${COMPOSE[@]}" exec -T db dropdb --if-exists -U bodyos "$RESTORE_DB"; then
        echo "Restore-test database cleanup failed." >&2
        status=1
    fi
    exit "$status"
}
trap cleanup EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -pass "file:$KEY_FILE" -in "$BACKUP_FILE" \
    | "${COMPOSE[@]}" exec -T db psql -v ON_ERROR_STOP=1 -U bodyos "$RESTORE_DB" >/dev/null
TABLE_COUNT=$("${COMPOSE[@]}" exec -T db psql -At -U bodyos "$RESTORE_DB" -c \
    "select count(*) from information_schema.tables where table_schema='public';")
test "$TABLE_COUNT" -ge 12
"${COMPOSE[@]}" exec -T db dropdb --if-exists -U bodyos "$RESTORE_DB"
trap - EXIT
echo "Restore test passed with expected schema cardinality."
