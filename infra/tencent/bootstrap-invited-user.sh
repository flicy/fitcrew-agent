#!/bin/sh
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE="$HERE/runtime/.env.runtime"
COMPOSE="docker compose --env-file $ENV_FILE -f $HERE/compose.yaml"

if [ ! -t 0 ] || [ ! -t 2 ]; then
    echo "Controlled invitation requires an interactive terminal." >&2
    exit 1
fi

stty_state=$(stty -g)
restore_terminal() {
    stty "$stty_state"
}
trap restore_terminal EXIT
trap 'restore_terminal; exit 130' HUP INT TERM

read_private() {
    label="$1"
    printf "%s: " "$label" >&2
    stty -echo
    if ! IFS= read -r value; then
        stty "$stty_state"
        return 1
    fi
    stty "$stty_state"
    printf '\n' >&2
    printf '%s' "$value"
}

SUBJECT=$(read_private "Verified Feishu subject")
DEVICE_PUBLIC_ID=$(read_private "Public device identifier")
printf "Local slug: " >&2
IFS= read -r SLUG

case "$SUBJECT" in
    ''|*,*|*[![:graph:]]*)
        echo "Feishu subject is invalid." >&2
        exit 1
        ;;
esac
case "$DEVICE_PUBLIC_ID" in
    ''|*[![:print:]]*)
        echo "Public device identifier is invalid." >&2
        exit 1
        ;;
esac
case "$SLUG" in
    ''|*[!a-z0-9_-]*|[!a-z0-9]*)
        echo "Local slug must use lowercase letters, digits, _ or -." >&2
        exit 1
        ;;
esac
if [ "${#SLUG}" -gt 64 ]; then
    echo "Local slug must use lowercase letters, digits, _ or -." >&2
    exit 1
fi

$COMPOSE exec -T \
    -e "BODYOS_INVITEE_FEISHU_SUBJECT=$SUBJECT" \
    -e "BODYOS_INVITEE_DEVICE_PUBLIC_ID=$DEVICE_PUBLIC_ID" \
    -e "BODYOS_INVITEE_SLUG=$SLUG" \
    api python /app/scripts/bootstrap_invited_user.py
$COMPOSE restart gateway

echo "Controlled invitation completed; deliver the private pairing artifact only through a verified private channel."
