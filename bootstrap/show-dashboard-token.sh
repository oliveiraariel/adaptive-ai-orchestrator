#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bootstrap/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

TOKEN_FILE="$(expand_path "$GATEWAY_SECRET_FILE")"

[[ -s "$TOKEN_FILE" ]] || die "Gateway token file not found: $TOKEN_FILE"

cat <<EOF
The OpenClaw Control UI may ask for the shared Gateway token.
This command intentionally reveals it on your terminal. Do not paste it into
chat messages, issue trackers, screenshots, or repositories.

Token file: $TOKEN_FILE

Gateway token:
EOF
cat "$TOKEN_FILE"
printf '\n'
