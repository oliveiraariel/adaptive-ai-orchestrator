#!/usr/bin/env bash
set -Eeuo pipefail

BOOTSTRAP_VERSION="1.0.0"
ADAPTIVE_REPO_URL="https://github.com/oliveiraariel/adaptive-ai-orchestrator.git"
DEFAULT_STACK_ROOT="${ADAPTIVE_STACK_ROOT:-$HOME/Projects/AdaptiveOpenClaw}"

log() { printf '\n[adaptive-bootstrap] %s\n' "$*"; }
die() { printf '\n[adaptive-bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

apt_run() {
  if [[ "${EUID:-$(id -u)}" == "0" ]]; then
    apt-get "$@"
  else
    command -v sudo >/dev/null 2>&1 || die "sudo is required to install Git on this host."
    sudo apt-get "$@"
  fi
}

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return
  fi
  command -v apt-get >/dev/null 2>&1 || die "Git is missing and apt-get is unavailable. Install Git, then rerun."
  log "Installing Git"
  apt_run update
  apt_run install -y git ca-certificates
}

STACK_ROOT="$DEFAULT_STACK_ROOT"
PASSTHROUGH=()
while (($#)); do
  case "$1" in
    --stack-root)
      [[ $# -ge 2 ]] || die "--stack-root requires a path"
      STACK_ROOT="$2"
      shift 2
      ;;
    --stack-root=*)
      STACK_ROOT="${1#*=}"
      shift
      ;;
    *)
      PASSTHROUGH+=("$1")
      shift
      ;;
  esac
done

STACK_ROOT="${STACK_ROOT/#\~/$HOME}"
ADAPTIVE_DIR="$STACK_ROOT/adaptive-ai-orchestrator"

ensure_git
mkdir -p "$STACK_ROOT"

if [[ -d "$ADAPTIVE_DIR/.git" ]]; then
  log "Adaptive repository already exists; synchronizing main safely"
  if [[ -n "$(git -C "$ADAPTIVE_DIR" status --porcelain)" ]]; then
    die "The Adaptive repository has local changes at $ADAPTIVE_DIR. Commit, stash, or discard them explicitly before bootstrap."
  fi
  git -C "$ADAPTIVE_DIR" fetch origin main
  git -C "$ADAPTIVE_DIR" switch main
  git -C "$ADAPTIVE_DIR" merge --ff-only origin/main
elif [[ -e "$ADAPTIVE_DIR" ]]; then
  die "$ADAPTIVE_DIR exists but is not a Git repository. Move it aside or choose another --stack-root."
else
  log "Cloning Adaptive AI Orchestrator"
  git clone --branch main --single-branch "$ADAPTIVE_REPO_URL" "$ADAPTIVE_DIR"
fi

log "Starting reproducible setup (bootstrap $BOOTSTRAP_VERSION)"
exec bash "$ADAPTIVE_DIR/bootstrap/setup.sh" --stack-root "$STACK_ROOT" "${PASSTHROUGH[@]}"
