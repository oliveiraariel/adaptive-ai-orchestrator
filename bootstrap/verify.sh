#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bootstrap/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

STACK_ROOT="$ADAPTIVE_STACK_ROOT"
RUN_TESTS=1
RUN_E2E=0
STATIC_ONLY=0

usage() {
  cat <<'EOF'
Usage: bootstrap/verify.sh [options]

Options:
  --stack-root PATH  Parent directory containing both repositories.
  --quick            Skip the full pytest suite.
  --e2e              Run live Adaptive→OpenClaw and OpenClaw→Adaptive→OpenClaw tests.
  --static           Validate only bootstrap files; no local OpenClaw required.
  -h, --help         Show this help.
EOF
}

while (($#)); do
  case "$1" in
    --stack-root)
      [[ $# -ge 2 ]] || die "--stack-root requires a path"
      STACK_ROOT="$2"; shift 2 ;;
    --stack-root=*) STACK_ROOT="${1#*=}"; shift ;;
    --quick) RUN_TESTS=0; shift ;;
    --e2e) RUN_E2E=1; shift ;;
    --static) STATIC_ONLY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

STACK_ROOT="$(expand_path "$STACK_ROOT")"
ADAPTIVE_DIR="$ADAPTIVE_REPO_ROOT"
SKILLS_DIR="$STACK_ROOT/ariel-agent-skills"
VENV_PYTHON="$ADAPTIVE_DIR/.venv/bin/python"
TOKEN_FILE="$(expand_path "$GATEWAY_SECRET_FILE")"

static_checks() {
  local scripts=(
    "$ADAPTIVE_DIR/install.sh"
    "$SCRIPT_DIR/setup.sh"
    "$SCRIPT_DIR/update.sh"
    "$SCRIPT_DIR/verify.sh"
    "$SCRIPT_DIR/install-launchers.sh"
    "$SCRIPT_DIR/show-dashboard-token.sh"
    "$SCRIPT_DIR/lib/common.sh"
  )
  local script
  [[ -f "$BOOTSTRAP_MANIFEST" ]] || die "Missing bootstrap manifest: $BOOTSTRAP_MANIFEST"
  python3 -m json.tool "$BOOTSTRAP_MANIFEST" >/dev/null
  for script in "${scripts[@]}"; do
    [[ -f "$script" ]] || die "Missing bootstrap script: $script"
    bash -n "$script"
  done
  ok "Bootstrap manifest and shell syntax"
}

static_checks
if [[ "$STATIC_ONLY" == "1" ]]; then
  printf '\nBOOTSTRAP STATIC VALIDATION: PASS\n'
  exit 0
fi

failures=0
check() {
  local label="$1"
  shift
  if "$@"; then
    ok "$label"
  else
    printf '[FAIL] %s\n' "$label" >&2
    failures=$((failures + 1))
  fi
}

log "Host and repository checks"
check_linux_family
ensure_python_312
check "Adaptive Git repository" test -d "$ADAPTIVE_DIR/.git"
check "Ariel Agent Skills Git repository" test -d "$SKILLS_DIR/.git"
check "Adaptive virtualenv" test -x "$VENV_PYTHON"

if [[ "$RUN_TESTS" == "1" && -x "$VENV_PYTHON" ]]; then
  if (cd "$ADAPTIVE_DIR" && "$VENV_PYTHON" -m pytest -q); then
    ok "Adaptive pytest suite"
  else
    printf '[FAIL] Adaptive pytest suite\n' >&2
    failures=$((failures + 1))
  fi
fi

if [[ -f "$SKILLS_DIR/scripts/validate_ecosystem.py" ]]; then
  if python3 "$SKILLS_DIR/scripts/validate_ecosystem.py"; then
    ok "Ariel skill ecosystem"
  else
    printf '[FAIL] Ariel skill ecosystem\n' >&2
    failures=$((failures + 1))
  fi
fi

OPENCLAW_BIN="$(resolve_openclaw || true)"
if [[ -z "$OPENCLAW_BIN" ]]; then
  printf '[FAIL] OpenClaw CLI not found\n' >&2
  failures=$((failures + 1))
else
  OC_VERSION="$(openclaw_version "$OPENCLAW_BIN")"
  if [[ -n "$OC_VERSION" ]] && version_ge "$OC_VERSION" "$OPENCLAW_MIN_VERSION"; then
    ok "OpenClaw $OC_VERSION"
  else
    printf '[FAIL] OpenClaw version (need %s+, found %s)\n' "$OPENCLAW_MIN_VERSION" "${OC_VERSION:-unknown}" >&2
    failures=$((failures + 1))
  fi

  if "$OPENCLAW_BIN" config validate; then
    ok "OpenClaw config validation"
  else
    printf '[FAIL] OpenClaw config validation\n' >&2
    failures=$((failures + 1))
  fi

  if "$OPENCLAW_BIN" gateway status --require-rpc; then
    ok "OpenClaw Gateway RPC"
  else
    printf '[FAIL] OpenClaw Gateway RPC\n' >&2
    failures=$((failures + 1))
  fi

  if "$OPENCLAW_BIN" skills info adaptive-orchestrator-bridge --agent main >/dev/null; then
    ok "adaptive-orchestrator-bridge visible to main"
  else
    printf '[FAIL] adaptive-orchestrator-bridge is not visible to main\n' >&2
    failures=$((failures + 1))
  fi

  skill_dirs="$("$OPENCLAW_BIN" config get skills.load.extraDirs --json 2>/dev/null || printf '[]')"
  if python3 - "$skill_dirs" "$SKILLS_DIR" <<'PY'
import json, sys
try:
    dirs = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit(1)
raise SystemExit(0 if isinstance(dirs, list) and sys.argv[2] in dirs else 1)
PY
  then
    ok "Ariel skills root configured"
  else
    printf '[FAIL] Ariel skills root missing from skills.load.extraDirs\n' >&2
    failures=$((failures + 1))
  fi

  auth_ref="$("$OPENCLAW_BIN" config get gateway.auth.token --json 2>/dev/null || true)"
  if [[ "$auth_ref" == *"$GATEWAY_SECRET_PROVIDER"* ]]; then
    ok "Gateway auth uses file-backed SecretRef"
  else
    printf '[FAIL] Gateway auth is not using the bootstrap SecretRef provider\n' >&2
    failures=$((failures + 1))
  fi
fi

if [[ -s "$TOKEN_FILE" ]]; then
  mode="$(stat -c '%a' "$TOKEN_FILE" 2>/dev/null || printf '?')"
  if [[ "$mode" == "600" ]]; then
    ok "Gateway secret file permissions 0600"
  else
    printf '[FAIL] Gateway secret file mode is %s, expected 600\n' "$mode" >&2
    failures=$((failures + 1))
  fi
else
  printf '[FAIL] Gateway secret file missing or empty: %s\n' "$TOKEN_FILE" >&2
  failures=$((failures + 1))
fi

if ((failures > 0)); then
  printf '\nENVIRONMENT VERIFICATION: FAIL (%d check(s))\n' "$failures" >&2
  exit 1
fi

if [[ "$RUN_E2E" == "1" ]]; then
  [[ -n "${OPENCLAW_BIN:-}" ]] || die "OpenClaw is required for E2E"
  [[ -x "$VENV_PYTHON" ]] || die "Adaptive virtualenv is required for E2E"
  TOKEN="$(read_secret_token "$TOKEN_FILE")" || die "Cannot read Gateway token file"

  log "E2E 1/2 — Adaptive → OpenClaw Gateway"
  OUTBOUND_MARKER="ADAPTIVE_BOOTSTRAP_OUTBOUND_OK"
  OUTBOUND_RESULT="$(OPENCLAW_GATEWAY_TOKEN="$TOKEN" \
    "$VENV_PYTHON" -m adaptive_orchestrator run \
      --objective "Respond exactly with $OUTBOUND_MARKER." \
      --agent main \
      --accept "$OUTBOUND_MARKER")"
  if [[ "$OUTBOUND_RESULT" != *"$OUTBOUND_MARKER"* ]]; then
    die "Outbound Adaptive→OpenClaw E2E did not return $OUTBOUND_MARKER"
  fi
  ok "Adaptive → OpenClaw Gateway → main → Adaptive"

  log "E2E 2/2 — OpenClaw → bridge → Adaptive → OpenClaw"
  INBOUND_MARKER="ADAPTIVE_BOOTSTRAP_INBOUND_OK"
  SESSION_KEY="adaptive-bootstrap-$(date +%s)-$RANDOM"
  PROMPT="/adaptive-orchestrator-bridge Delegate only this objective through the Adaptive AI Orchestrator: Respond exactly with $INBOUND_MARKER. Use agent main. Use $INBOUND_MARKER as the explicit acceptance criterion. Do not alter files or configuration. Return the Adaptive runtime_status, work_unit_state, verdict, output, and execution_id."
  INBOUND_RESULT="$("$OPENCLAW_BIN" agent \
    --agent main \
    --session-key "$SESSION_KEY" \
    --message "$PROMPT" \
    --json)"
  if [[ "$INBOUND_RESULT" != *"$INBOUND_MARKER"* ]]; then
    die "Inbound OpenClaw→Adaptive E2E did not return $INBOUND_MARKER"
  fi
  ok "OpenClaw → bridge → Adaptive → OpenClaw → Adaptive → OpenClaw"
fi

printf '\nENVIRONMENT VERIFICATION: PASS\n'
