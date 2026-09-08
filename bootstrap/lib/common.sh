#!/usr/bin/env bash
set -Eeuo pipefail

BOOTSTRAP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ADAPTIVE_REPO_ROOT="$(cd -- "$BOOTSTRAP_DIR/.." && pwd)"
BOOTSTRAP_MANIFEST="$BOOTSTRAP_DIR/manifest.json"
BOOTSTRAP_VERSION="1.0.0"

: "${DRY_RUN:=0}"
: "${ADAPTIVE_STACK_ROOT:=$HOME/Projects/AdaptiveOpenClaw}"
: "${ADAPTIVE_REPO_URL:=https://github.com/oliveiraariel/adaptive-ai-orchestrator.git}"
: "${SKILLS_REPO_URL:=https://github.com/oliveiraariel/ariel-agent-skills.git}"
: "${ADAPTIVE_BRANCH:=main}"
: "${SKILLS_BRANCH:=main}"
: "${OPENCLAW_MIN_VERSION:=2026.9.2}"
: "${GATEWAY_SECRET_PROVIDER:=adaptive_gateway_file}"
: "${GATEWAY_SECRET_FILE:=$HOME/.openclaw/secrets/adaptive-gateway-token.txt}"

log() { printf '\n[adaptive-bootstrap] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARN] %s\n' "$*" >&2; }
die() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

quote_cmd() {
  printf '%q ' "$@"
  printf '\n'
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '[DRY-RUN] '
    quote_cmd "$@"
    return 0
  fi
  "$@"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

expand_path() {
  local path="$1"
  printf '%s\n' "${path/#\~/$HOME}"
}

version_ge() {
  local have="$1" need="$2"
  [[ "$(printf '%s\n%s\n' "$need" "$have" | sort -V | head -n1)" == "$need" ]]
}

check_linux_family() {
  [[ "$(uname -s)" == "Linux" ]] || die "This bootstrap currently targets Linux."
  [[ -r /etc/os-release ]] || die "Cannot identify Linux distribution (/etc/os-release missing)."
  # shellcheck disable=SC1091
  source /etc/os-release
  case "${ID:-}" in
    linuxmint|ubuntu|debian|pop) ;;
    *)
      if [[ "${ID_LIKE:-}" != *debian* && "${ID_LIKE:-}" != *ubuntu* ]]; then
        die "Unsupported distribution: ${PRETTY_NAME:-${ID:-unknown}}. Supported family: Debian/Ubuntu/Linux Mint."
      fi
      ;;
  esac
}

ensure_apt_dependencies() {
  local packages=(git curl ca-certificates python3 python3-venv python3-pip)
  local missing=()
  command -v git >/dev/null 2>&1 || missing+=(git)
  command -v curl >/dev/null 2>&1 || missing+=(curl)
  command -v python3 >/dev/null 2>&1 || missing+=(python3 python3-venv python3-pip)
  if ((${#missing[@]} == 0)); then
    return
  fi
  need_cmd sudo
  need_cmd apt-get
  log "Installing required system packages"
  run sudo apt-get update
  run sudo apt-get install -y "${packages[@]}"
}

ensure_python_312() {
  need_cmd python3
  local pyver
  pyver="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  version_ge "$pyver" "3.12" || die "Python 3.12+ is required; found $pyver. Upgrade Python, then rerun bootstrap."
  ok "Python $pyver"
}

safe_git_sync() {
  local url="$1" dir="$2" branch="$3" label="$4"
  if [[ -d "$dir/.git" ]]; then
    if [[ -n "$(git -C "$dir" status --porcelain)" ]]; then
      die "$label has local changes at $dir. Bootstrap will not overwrite them. Commit, stash, or resolve them explicitly."
    fi
    log "Synchronizing $label"
    run git -C "$dir" fetch origin "$branch"
    run git -C "$dir" switch "$branch"
    run git -C "$dir" merge --ff-only "origin/$branch"
    return
  fi
  if [[ -e "$dir" ]]; then
    die "$dir exists but is not a Git repository. Move it or choose another stack root."
  fi
  log "Cloning $label"
  run git clone --branch "$branch" --single-branch "$url" "$dir"
}

resolve_openclaw() {
  local candidate
  if command -v openclaw >/dev/null 2>&1; then
    command -v openclaw
    return 0
  fi
  for candidate in "$HOME/.local/bin/openclaw" "$HOME/.npm-global/bin/openclaw"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  if [[ -d "$HOME/.nvm/versions/node" ]]; then
    candidate="$(find "$HOME/.nvm/versions/node" -maxdepth 4 -type f -path '*/bin/openclaw' -perm -u+x 2>/dev/null | sort -V | tail -n1 || true)"
    if [[ -n "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  fi
  return 1
}

openclaw_version() {
  local bin="$1"
  "$bin" --version 2>/dev/null | grep -Eo '[0-9]{4}\.[0-9]+\.[0-9]+' | head -n1
}

append_skill_root() {
  local openclaw_bin="$1" skill_root="$2" current json
  current="$($openclaw_bin config get skills.load.extraDirs --json 2>/dev/null || printf '[]')"
  json="$(python3 - "$current" "$skill_root" <<'PY'
import json, sys
raw, wanted = sys.argv[1], sys.argv[2]
try:
    value = json.loads(raw)
except json.JSONDecodeError:
    value = []
if not isinstance(value, list):
    value = []
if wanted not in value:
    value.append(wanted)
print(json.dumps(value, ensure_ascii=False))
PY
)"
  run "$openclaw_bin" config set skills.load.extraDirs "$json" --strict-json
}

ensure_secret_file() {
  local file="$1" token="${OPENCLAW_GATEWAY_TOKEN:-}"
  file="$(expand_path "$file")"
  if [[ -s "$file" && -z "$token" ]]; then
    ok "Reusing existing file-backed Gateway token"
    return 0
  fi
  if [[ -z "$token" ]]; then
    token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    info "Would write a generated/provided Gateway token to $file with mode 0600"
    return 0
  fi
  umask 077
  mkdir -p "$(dirname "$file")"
  chmod 700 "$(dirname "$file")"
  printf '%s' "$token" > "$file"
  chmod 600 "$file"
  ok "Gateway token stored securely at $file"
}

configure_openclaw_secretrefs() {
  local openclaw_bin="$1" token_file="$2" provider="$3"
  token_file="$(expand_path "$token_file")"
  local provider_json ref_json
  provider_json="$(python3 - "$token_file" <<'PY'
import json, sys
print(json.dumps({"source":"file","path":sys.argv[1],"mode":"singleValue"}))
PY
)"
  ref_json="$(python3 - "$provider" <<'PY'
import json, sys
print(json.dumps({"source":"file","provider":sys.argv[1],"id":"value"}))
PY
)"
  run "$openclaw_bin" config set "secrets.providers.$provider" "$provider_json" --strict-json
  run "$openclaw_bin" config set gateway.auth.mode '"token"' --strict-json
  run "$openclaw_bin" config set gateway.auth.token "$ref_json" --strict-json
  run "$openclaw_bin" config set skills.entries.adaptive-orchestrator-bridge.enabled true --strict-json
  run "$openclaw_bin" config set skills.entries.adaptive-orchestrator-bridge.apiKey "$ref_json" --strict-json
}

restart_or_install_gateway() {
  local openclaw_bin="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "Would restart the OpenClaw Gateway; if absent, install and start its managed user service"
    return 0
  fi
  if ! "$openclaw_bin" gateway restart; then
    warn "Gateway restart failed; attempting managed Gateway installation"
    "$openclaw_bin" gateway install
    "$openclaw_bin" gateway start
  fi
  "$openclaw_bin" gateway status --require-rpc
}

read_secret_token() {
  local file
  file="$(expand_path "$1")"
  [[ -s "$file" ]] || return 1
  cat "$file"
}
