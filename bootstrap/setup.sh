#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bootstrap/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

STACK_ROOT="$ADAPTIVE_STACK_ROOT"
INSTALL_OPENCLAW=1
RUN_ONBOARD=1
INSTALL_DESKTOP=1
RUN_E2E=1

usage() {
  cat <<'EOF'
Adaptive + OpenClaw reproducible setup

Usage: bootstrap/setup.sh [options]

Options:
  --stack-root PATH       Parent directory containing both repositories.
  --dry-run               Print the setup plan without changing the machine.
  --skip-openclaw-install Do not install OpenClaw when missing.
  --skip-onboard          Do not launch OpenClaw's interactive onboarding.
  --skip-desktop          Do not install desktop/application-menu launchers.
  --skip-e2e              Skip the live outbound + inbound model smoke tests.
  -h, --help              Show this help.

Security:
  Gateway authentication is standardized on a generated file-backed token.
  The token is stored with mode 0600 and referenced through OpenClaw SecretRef.
  If OPENCLAW_GATEWAY_TOKEN is already exported, that value is migrated instead
  of generating a new token. Secrets are never printed by this script.
EOF
}

while (($#)); do
  case "$1" in
    --stack-root)
      [[ $# -ge 2 ]] || die "--stack-root requires a path"
      STACK_ROOT="$2"
      shift 2
      ;;
    --stack-root=*) STACK_ROOT="${1#*=}"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --skip-openclaw-install) INSTALL_OPENCLAW=0; shift ;;
    --skip-onboard) RUN_ONBOARD=0; shift ;;
    --skip-desktop) INSTALL_DESKTOP=0; shift ;;
    --skip-e2e) RUN_E2E=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

STACK_ROOT="$(expand_path "$STACK_ROOT")"
ADAPTIVE_DIR="$ADAPTIVE_REPO_ROOT"
SKILLS_DIR="$STACK_ROOT/ariel-agent-skills"
VENV_PYTHON="$ADAPTIVE_DIR/.venv/bin/python"
TOKEN_FILE="$(expand_path "$GATEWAY_SECRET_FILE")"

if [[ "$DRY_RUN" == "1" ]]; then
  cat <<EOF
[DRY-RUN] Adaptive/OpenClaw bootstrap $BOOTSTRAP_VERSION
  stack root:      $STACK_ROOT
  adaptive repo:   $ADAPTIVE_DIR
  skills repo:     $SKILLS_DIR
  gateway secret:  $TOKEN_FILE (0600; value never printed)
  OpenClaw install: $INSTALL_OPENCLAW
  onboarding:       $RUN_ONBOARD
  desktop launchers:$INSTALL_DESKTOP
  live E2E:         $RUN_E2E

Planned stages:
  1. Verify Debian/Ubuntu/Linux Mint host and Python 3.12+.
  2. Clone/update ariel-agent-skills without overwriting local work.
  3. Create Adaptive .venv and install .[test,gateway].
  4. Run Adaptive tests and Ariel skill-registry validation.
  5. Install OpenClaw from its official stable installer if absent.
  6. Run official OpenClaw onboarding if configuration is not ready.
  7. Add the Ariel skills repository to skills.load.extraDirs and preserve any agent skill allowlists.
  8. Create/migrate a file-backed Gateway token and SecretRefs.
  9. Enable adaptive-orchestrator-bridge and restart the Gateway.
 10. Verify Gateway RPC, main-agent skill visibility, and bridge discovery.
 11. Run outbound and full inbound E2E smoke tests.
 12. Install Setup / Update / Verify desktop launchers.
EOF
  exit 0
fi

log "Stage 1/12 — host prerequisites"
check_linux_family
ensure_apt_dependencies
ensure_python_312
need_cmd git
need_cmd curl
mkdir -p "$STACK_ROOT"

[[ -d "$ADAPTIVE_DIR/.git" ]] || die "Adaptive repository is not a Git checkout: $ADAPTIVE_DIR"
if [[ -n "$(git -C "$ADAPTIVE_DIR" status --porcelain --untracked-files=no)" ]]; then
  warn "Adaptive tracked files have local changes. Setup will use them but will not modify or discard them."
fi

log "Stage 2/12 — Ariel Agent Skills repository"
safe_git_sync "$SKILLS_REPO_URL" "$SKILLS_DIR" "$SKILLS_BRANCH" "Ariel Agent Skills"

log "Stage 3/12 — Adaptive Python environment"
if [[ ! -x "$VENV_PYTHON" ]]; then
  python3 -m venv "$ADAPTIVE_DIR/.venv"
fi
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e "$ADAPTIVE_DIR[test,gateway]"
ok "Adaptive virtual environment installed"

log "Stage 4/12 — repository validation"
(
  cd "$ADAPTIVE_DIR"
  "$VENV_PYTHON" -m pytest -q
)
python3 "$SKILLS_DIR/scripts/validate_ecosystem.py"
ok "Adaptive tests and skill ecosystem validation passed"

log "Stage 5/12 — OpenClaw installation"
OPENCLAW_BIN="$(resolve_openclaw || true)"
if [[ -z "$OPENCLAW_BIN" ]]; then
  if [[ "$INSTALL_OPENCLAW" != "1" ]]; then
    die "OpenClaw is not installed and --skip-openclaw-install was requested."
  fi
  info "Installing OpenClaw using the official stable installer"
  curl -fsSL https://openclaw.ai/install.sh | bash -s -- --no-onboard
  export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
  OPENCLAW_BIN="$(resolve_openclaw || true)"
  [[ -n "$OPENCLAW_BIN" ]] || die "OpenClaw installation finished but the CLI could not be located. Start a new shell and rerun setup."
fi
OC_VERSION="$(openclaw_version "$OPENCLAW_BIN")"
[[ -n "$OC_VERSION" ]] || die "Could not determine OpenClaw version from $OPENCLAW_BIN"
version_ge "$OC_VERSION" "$OPENCLAW_MIN_VERSION" || die "OpenClaw $OPENCLAW_MIN_VERSION+ is required; found $OC_VERSION. Run 'openclaw update --yes' and retry."
ok "OpenClaw $OC_VERSION"

log "Stage 6/12 — OpenClaw onboarding / model authentication"
if ! "$OPENCLAW_BIN" config validate >/dev/null 2>&1; then
  if [[ "$RUN_ONBOARD" != "1" ]]; then
    die "OpenClaw configuration is not valid and --skip-onboard was requested. Run 'openclaw onboard --install-daemon' and rerun setup."
  fi
  cat <<'EOF'

OpenClaw now needs its normal interactive onboarding. This is the only part
that cannot be safely automated because you must authenticate your own model
provider (for example OpenAI OAuth/API credentials). Complete the wizard; the
bootstrap resumes automatically afterward.
EOF
  "$OPENCLAW_BIN" onboard --install-daemon
fi
"$OPENCLAW_BIN" config validate

if ! "$OPENCLAW_BIN" skills check --agent main >/dev/null 2>&1; then
  if [[ "$RUN_ONBOARD" != "1" ]]; then
    die "The OpenClaw 'main' agent is not ready. Run OpenClaw onboarding and rerun setup."
  fi
  warn "The main agent is not ready; reopening onboarding."
  "$OPENCLAW_BIN" onboard --install-daemon
fi

log "Stage 7/12 — skill discovery configuration"
append_skill_root "$OPENCLAW_BIN" "$SKILLS_DIR"
"$OPENCLAW_BIN" config validate
ensure_bridge_allowlisted "$OPENCLAW_BIN"
"$OPENCLAW_BIN" config validate

log "Stage 8/12 — durable Gateway secret"
ensure_secret_file "$TOKEN_FILE"
configure_openclaw_secretrefs "$OPENCLAW_BIN" "$TOKEN_FILE" "$GATEWAY_SECRET_PROVIDER"
"$OPENCLAW_BIN" config validate
ok "Gateway and bridge now use the same file-backed SecretRef token"

log "Stage 9/12 — managed Gateway service"
restart_or_install_gateway "$OPENCLAW_BIN"

log "Stage 10/12 — bridge and skill visibility"
python3 "$SKILLS_DIR/scripts/validate_ecosystem.py"
"$OPENCLAW_BIN" skills check --agent main
"$OPENCLAW_BIN" skills info adaptive-orchestrator-bridge --agent main
ok "adaptive-orchestrator-bridge is visible to agent main"

log "Stage 11/12 — live end-to-end validation"
if [[ "$RUN_E2E" == "1" ]]; then
  bash "$SCRIPT_DIR/verify.sh" --stack-root "$STACK_ROOT" --quick --e2e
else
  info "Live E2E smoke tests skipped by request"
fi

log "Stage 12/12 — desktop/application launchers"
if [[ "$INSTALL_DESKTOP" == "1" ]]; then
  bash "$SCRIPT_DIR/install-launchers.sh" --stack-root "$STACK_ROOT"
else
  info "Desktop launchers skipped by request"
fi

cat <<EOF

============================================================
 ADAPTIVE + OPENCLAW ENVIRONMENT READY
============================================================

Stack root:
  $STACK_ROOT

Adaptive:
  $ADAPTIVE_DIR

Ariel Agent Skills:
  $SKILLS_DIR

Useful commands:
  bash "$SCRIPT_DIR/verify.sh" --e2e
  bash "$SCRIPT_DIR/update.sh"
  bash "$SCRIPT_DIR/show-dashboard-token.sh"

OpenClaw dashboard:
  $OPENCLAW_BIN dashboard

The Gateway secret is stored at:
  $TOKEN_FILE
It is intentionally not printed. Use show-dashboard-token.sh only if the
Control UI explicitly asks you to paste the shared token.
============================================================
EOF
