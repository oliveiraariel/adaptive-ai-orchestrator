#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bootstrap/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

STACK_ROOT="$ADAPTIVE_STACK_ROOT"
UPDATE_OPENCLAW=1
RUN_E2E=1

usage() {
  cat <<'EOF'
Usage: bootstrap/update.sh [options]

Options:
  --stack-root PATH   Parent directory containing both repositories.
  --skip-openclaw     Update Adaptive/skills only; leave OpenClaw unchanged.
  --skip-e2e          Skip live E2E validation after updating.
  --dry-run           Preview OpenClaw update plus Git actions without applying.
  -h, --help          Show this help.

Safety:
  Git updates are fast-forward only and abort on local changes.
  OpenClaw uses its supported `openclaw update` command. Capability changes are
  NOT auto-accepted; if OpenClaw asks for capability review, the update stops so
  you can inspect it explicitly.

Recovery:
  Every successful update refreshes the Adaptive/OpenClaw launchers and the
  persisted ~/.local/bin shell PATH registration before final verification.
EOF
}

while (($#)); do
  case "$1" in
    --stack-root)
      [[ $# -ge 2 ]] || die "--stack-root requires a path"
      STACK_ROOT="$2"; shift 2 ;;
    --stack-root=*) STACK_ROOT="${1#*=}"; shift ;;
    --skip-openclaw) UPDATE_OPENCLAW=0; shift ;;
    --skip-e2e) RUN_E2E=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

STACK_ROOT="$(expand_path "$STACK_ROOT")"
ADAPTIVE_DIR="$ADAPTIVE_REPO_ROOT"
SKILLS_DIR="$STACK_ROOT/ariel-agent-skills"

if [[ "$DRY_RUN" == "1" ]]; then
  info "Would fast-forward $ADAPTIVE_DIR from origin/main"
  info "Would fast-forward $SKILLS_DIR from origin/main"
  info "Would refresh adaptive-openclaw-* launchers and persist ~/.local/bin in shell startup PATH"
  if [[ "$UPDATE_OPENCLAW" == "1" ]]; then
    OPENCLAW_BIN="$(resolve_openclaw || true)"
    if [[ -n "$OPENCLAW_BIN" ]]; then
      "$OPENCLAW_BIN" update --dry-run || true
    else
      info "OpenClaw not currently found; setup.sh would be required first"
    fi
  fi
  info "Would reinstall Adaptive editable dependencies and validate repositories"
  [[ "$RUN_E2E" == "1" ]] && info "Would run complete E2E verification"
  exit 0
fi

check_linux_family
ensure_python_312
need_cmd git

safe_git_sync "$ADAPTIVE_REPO_URL" "$ADAPTIVE_DIR" "$ADAPTIVE_BRANCH" "Adaptive AI Orchestrator"
safe_git_sync "$SKILLS_REPO_URL" "$SKILLS_DIR" "$SKILLS_BRANCH" "Ariel Agent Skills"

# Refresh launchers after repository synchronization so updates carry forward
# bootstrap fixes instead of leaving old wrappers/PATH metadata behind.
log "Refreshing Adaptive/OpenClaw launchers and shell PATH registration"
bash "$SCRIPT_DIR/install-launchers.sh" --stack-root "$STACK_ROOT"
export PATH="$HOME/.local/bin:$PATH"
ok "Launcher/PATH recovery surface refreshed"

VENV_PYTHON="$ADAPTIVE_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  python3 -m venv "$ADAPTIVE_DIR/.venv"
fi
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e "$ADAPTIVE_DIR[test,gateway]"

(
  cd "$ADAPTIVE_DIR"
  "$VENV_PYTHON" -m pytest -q
)
python3 "$SKILLS_DIR/scripts/validate_ecosystem.py"

OPENCLAW_BIN="$(resolve_openclaw || true)"
[[ -n "$OPENCLAW_BIN" ]] || die "OpenClaw not found. Run bootstrap/setup.sh first."

if [[ "$UPDATE_OPENCLAW" == "1" ]]; then
  log "Updating OpenClaw through its supported stable updater"
  "$OPENCLAW_BIN" update --yes
fi

"$OPENCLAW_BIN" config validate
"$OPENCLAW_BIN" gateway status --require-rpc
"$OPENCLAW_BIN" skills info adaptive-orchestrator-bridge --agent main >/dev/null

VERIFY_ARGS=(--stack-root "$STACK_ROOT")
if [[ "$RUN_E2E" == "1" ]]; then
  VERIFY_ARGS+=(--e2e)
fi
bash "$SCRIPT_DIR/verify.sh" "${VERIFY_ARGS[@]}"

printf '\nSTACK UPDATE: PASS\n'
