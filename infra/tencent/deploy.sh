#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
RUNTIME="$HERE/runtime"
ENV_FILE="$RUNTIME/.env.runtime"
COMPOSE="docker compose --env-file $ENV_FILE -f $HERE/compose.yaml"
ROLLBACK_ARMED=0
ROLLBACK_ATTEMPTED=0
ROLLBACK_AVAILABLE=0
ROLLBACK_DB_REVISION=0002_pairing_exchange_sessions

if [ ! -f "$ENV_FILE" ]; then
    echo "Runtime environment missing; collecting owner-only values without echoing secrets."
    (cd "$HERE" && python3 generate-runtime-env.py)
fi
(cd "$HERE" && python3 generate-runtime-env.py --append-defaults --output runtime/.env.runtime)

mkdir -p "$RUNTIME/acme" "$RUNTIME/tls" "$RUNTIME/letsencrypt" "$RUNTIME/backups" \
    "$RUNTIME/private-books" "$RUNTIME/owner"
chmod 700 "$RUNTIME" "$RUNTIME/tls" "$RUNTIME/letsencrypt" "$RUNTIME/backups" \
    "$RUNTIME/private-books" "$RUNTIME/owner"
chmod 755 "$RUNTIME/acme"
chown 1000:1000 "$RUNTIME/tls"
chown 10001:10001 "$RUNTIME/private-books" "$RUNTIME/owner"

PUBLIC_HOST=$(awk -F= '$1 == "FITCREW_PUBLIC_HOST" {print $2}' "$ENV_FILE")
if [ -z "$PUBLIC_HOST" ]; then
    echo "FITCREW_PUBLIC_HOST is missing from the runtime environment." >&2
    exit 1
fi
python3 -c 'import ipaddress,sys; ipaddress.ip_address(sys.argv[1])' "$PUBLIC_HOST"

CERTIFICATE_DIR="$RUNTIME/letsencrypt/live/$PUBLIC_HOST"
if [ ! -s "$CERTIFICATE_DIR/fullchain.pem" ] || [ ! -s "$CERTIFICATE_DIR/privkey.pem" ]; then
    echo "A trusted certificate is required before deployment; no certificate agreement was accepted automatically." >&2
    echo "Complete the owner-controlled certificate setup, then rerun deployment." >&2
    exit 1
fi
PREVIOUS_CADDYFILE="$RUNTIME/Caddyfile.before-deploy"
PREVIOUS_CADDYFILE_PRESENT=0
if [ -f "$RUNTIME/Caddyfile" ]; then
    install -m 0600 "$RUNTIME/Caddyfile" "$PREVIOUS_CADDYFILE"
    PREVIOUS_CADDYFILE_PRESENT=1
fi
"$HERE/sync-certificate.sh"
install -m 0644 "$HERE/Caddyfile.https" "$RUNTIME/Caddyfile"

PREVIOUS_IMAGE_TAG=$(awk -F= '$1 == "FITCREW_IMAGE_TAG" {print $2}' "$ENV_FILE")

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

rollback_on_failure() {
    exit_status="$1"
    [ "$exit_status" -eq 0 ] && return
    [ "$ROLLBACK_ATTEMPTED" -eq 0 ] || return
    ROLLBACK_ATTEMPTED=1
    trap - 0

    if [ "$ROLLBACK_ARMED" -ne 1 ]; then
        echo "Deployment stopped before a rollback image was available." >&2
        exit "$exit_status"
    fi

    echo "Deployment gate failed; restoring the previous immutable image." >&2
    set +e
    $COMPOSE stop api worker gateway >/dev/null 2>&1
    FITCREW_IMAGE_TAG="$DEPLOY_SHA" $COMPOSE run --rm --no-deps api \
        alembic downgrade "$ROLLBACK_DB_REVISION"
    database_restored=$?
    if [ "$database_restored" -ne 0 ]; then
        echo "Database compatibility rollback failed; previous services were not started." >&2
        exit "$exit_status"
    fi
    if [ "$PREVIOUS_CADDYFILE_PRESENT" -eq 1 ]; then
        install -m 0644 "$PREVIOUS_CADDYFILE" "$RUNTIME/Caddyfile"
    fi
    python3 "$HERE/set-runtime-image.py" --file "$ENV_FILE" "$PREVIOUS_IMAGE_TAG"
    FITCREW_IMAGE_TAG="$PREVIOUS_IMAGE_TAG" $COMPOSE up -d --no-build db api worker gateway caddy
    restored=$?
    if [ "$restored" -eq 0 ]; then
        echo "Previous service set restore was requested; verify it through the normal health checks." >&2
    else
        echo "Automatic restore command failed; use the recorded previous image tag with rollback.sh." >&2
    fi
    exit "$exit_status"
}

trap 'rollback_on_failure $?' 0
trap 'exit 130' INT
trap 'exit 143' HUP TERM

DEPLOY_SHA=$(git -C "$ROOT" rev-parse HEAD)
case "$DEPLOY_SHA" in
    *[!0-9a-f]*|'') echo "Invalid deploy SHA" >&2; exit 1 ;;
esac

case "$PREVIOUS_IMAGE_TAG" in
    [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f])
        if docker image inspect "fitcrew-bodyos:$PREVIOUS_IMAGE_TAG" >/dev/null 2>&1; then
            ROLLBACK_AVAILABLE=1
        else
            echo "Previous immutable image is unavailable; deployment will stop rather than claim rollback coverage." >&2
            exit 1
        fi
        ;;
    *)
        echo "No previous immutable image tag is available; first deployment has no automatic rollback target." >&2
        ;;
esac

if [ "$ROLLBACK_AVAILABLE" -eq 1 ]; then
    "$HERE/backup.sh"
fi

echo "Building immutable BodyOS image for ${DEPLOY_SHA}."
FITCREW_IMAGE_TAG="$DEPLOY_SHA" $COMPOSE build api
python3 "$HERE/set-runtime-image.py" --file "$ENV_FILE" "$DEPLOY_SHA"
ROLLBACK_ARMED=$ROLLBACK_AVAILABLE

echo "Starting database, API, worker, Feishu gateway, and HTTPS gateway."
$COMPOSE up -d db api worker gateway caddy

wait_for_service db health
wait_for_service api health
wait_for_service worker running
wait_for_service gateway running
wait_for_service caddy health
wait_for_api_loopback
wait_for_public_https

echo "BodyOS deployed at SHA ${DEPLOY_SHA}; all service and HTTPS health gates passed."
echo "Next: run model-login.sh once only if its OAuth state has not already been established."
