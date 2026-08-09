#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNTIME="$HERE/runtime"
ENV_FILE="$RUNTIME/.env.runtime"
COMPOSE="docker compose --env-file $ENV_FILE -f $HERE/compose.yaml"
ROLLBACK_SHA=${ROLLBACK_SHA:-${1:-}}
PREVIOUS_CADDYFILE="$RUNTIME/Caddyfile.before-deploy"

case "$ROLLBACK_SHA" in
    [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
    *) echo "ROLLBACK_SHA must be a full 40-character hexadecimal commit SHA." >&2; exit 1 ;;
esac

if [ ! -f "$ENV_FILE" ]; then
    echo "Runtime environment is missing." >&2
    exit 1
fi
if [ ! -s "$RUNTIME/tls/fullchain.pem" ] || [ ! -s "$RUNTIME/tls/privkey.pem" ]; then
    echo "Trusted TLS certificate is missing; rollback stopped before starting Caddy." >&2
    exit 1
fi

PUBLIC_HOST=$(awk -F= '$1 == "FITCREW_PUBLIC_HOST" {print $2}' "$ENV_FILE")
if [ -z "$PUBLIC_HOST" ]; then
    echo "FITCREW_PUBLIC_HOST is missing from the runtime environment." >&2
    exit 1
fi

service_is_ready() {
    service="$1"
    expected_state="$2"
    container_id=$($COMPOSE ps -q "$service" 2>/dev/null || true)
    [ -n "$container_id" ] || return 1
    [ "$(docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null || true)" = "true" ] || return 1
    if [ "$expected_state" = "health" ]; then
        [ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_id" 2>/dev/null || true)" = "healthy" ] || return 1
    fi
}

wait_for_service() {
    service="$1"
    expected_state="$2"
    attempt=0
    until service_is_ready "$service" "$expected_state"; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 30 ]; then
            echo "${service} ${expected_state} gate failed." >&2
            return 1
        fi
        sleep 2
    done
}

wait_for_api_loopback() {
    attempt=0
    until $COMPOSE exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)" >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 30 ]; then
            echo "API loopback health gate failed." >&2
            return 1
        fi
        sleep 2
    done
}

wait_for_public_https() {
    attempt=0
    until curl --fail --silent --show-error --proto '=https' --tlsv1.2 \
        --connect-timeout 5 --max-time 15 "https://${PUBLIC_HOST}/healthz" >/dev/null; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 12 ]; then
            echo "Public HTTPS health gate failed." >&2
            return 1
        fi
        sleep 5
    done
}

docker image inspect "fitcrew-bodyos:$ROLLBACK_SHA" >/dev/null
"$HERE/backup.sh"
if [ -f "$PREVIOUS_CADDYFILE" ]; then
    install -m 0644 "$PREVIOUS_CADDYFILE" "$RUNTIME/Caddyfile"
fi
python3 "$HERE/set-runtime-image.py" --file "$ENV_FILE" "$ROLLBACK_SHA"
FITCREW_IMAGE_TAG="$ROLLBACK_SHA" $COMPOSE up -d --no-build db api worker gateway caddy

wait_for_service db health
wait_for_service api health
wait_for_service worker running
wait_for_service gateway running
wait_for_service caddy health
wait_for_api_loopback
wait_for_public_https
echo "Rollback health gates passed; database backup was taken first."
