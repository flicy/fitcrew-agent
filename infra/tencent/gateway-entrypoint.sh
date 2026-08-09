#!/bin/sh
set -eu

ALLOWLIST_FILE=/owner-runtime/feishu-allowed-users

if [ -e "$ALLOWLIST_FILE" ]; then
    if [ ! -f "$ALLOWLIST_FILE" ] || [ -L "$ALLOWLIST_FILE" ] || [ ! -s "$ALLOWLIST_FILE" ] || \
        [ "$(stat -c %a "$ALLOWLIST_FILE" 2>/dev/null || true)" != "600" ]; then
        echo "Invalid private Feishu allowlist; gateway refused to start." >&2
        exit 1
    fi

    if ! allowed_users=$(awk '
        /^[^[:space:],]+$/ {
            if (seen[$0]++) {
                invalid = 1
                next
            }
            rendered = rendered (count++ ? "," : "") $0
            next
        }
        { invalid = 1 }
        END {
            if (invalid || count == 0) {
                exit 1
            }
            print rendered
        }
    ' "$ALLOWLIST_FILE"); then
        echo "Invalid private Feishu allowlist; gateway refused to start." >&2
        exit 1
    fi
    export FEISHU_ALLOWED_USERS="$allowed_users"
fi

python /app/scripts/render_hermes_profile.py --profile-dir /home/bodyos/.hermes/profiles/bodyos
exec hermes --profile bodyos gateway --accept-hooks run
