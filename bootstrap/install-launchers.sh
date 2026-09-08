#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=bootstrap/lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

STACK_ROOT="$ADAPTIVE_STACK_ROOT"

while (($#)); do
  case "$1" in
    --stack-root)
      [[ $# -ge 2 ]] || die "--stack-root requires a path"
      STACK_ROOT="$2"; shift 2 ;;
    --stack-root=*) STACK_ROOT="${1#*=}"; shift ;;
    -h|--help)
      echo "Usage: bootstrap/install-launchers.sh [--stack-root PATH]"
      exit 0
      ;;
    *) die "Unknown option: $1" ;;
  esac
done

STACK_ROOT="$(expand_path "$STACK_ROOT")"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$BIN_DIR" "$APP_DIR"

ensure_path_block() {
  local file="$1"
  local marker="# >>> adaptive-openclaw launcher PATH >>>"
  [[ -n "$file" ]] || return 0
  touch "$file"
  if grep -Fq "$marker" "$file" 2>/dev/null; then
    return 0
  fi
  cat >>"$file" <<'EOF'

# >>> adaptive-openclaw launcher PATH >>>
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
# <<< adaptive-openclaw launcher PATH <<<
EOF
}

ensure_launcher_path() {
  export PATH="$BIN_DIR:$PATH"
  ensure_path_block "$HOME/.profile"
  case "${SHELL:-}" in
    */bash) ensure_path_block "$HOME/.bashrc" ;;
    */zsh) ensure_path_block "$HOME/.zshrc" ;;
    *) ;;
  esac
}

write_wrapper() {
  local name="$1" script="$2"
  local target="$BIN_DIR/$name"
  {
    echo '#!/usr/bin/env bash'
    printf 'exec bash %q --stack-root %q "$@"\n' "$script" "$STACK_ROOT"
  } > "$target"
  chmod 755 "$target"
}

write_desktop() {
  local filename="$1" name="$2" comment="$3" executable="$4"
  cat > "$APP_DIR/$filename" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=$name
Comment=$comment
Exec=$executable
Icon=utilities-terminal
Terminal=true
Categories=Development;Utility;
StartupNotify=true
EOF
  chmod 755 "$APP_DIR/$filename"
}

ensure_launcher_path

write_wrapper adaptive-openclaw-setup "$SCRIPT_DIR/setup.sh"
write_wrapper adaptive-openclaw-update "$SCRIPT_DIR/update.sh"

VERIFY_WRAPPER="$BIN_DIR/adaptive-openclaw-verify"
{
  echo '#!/usr/bin/env bash'
  printf 'exec bash %q --stack-root %q --e2e "$@"\n' "$SCRIPT_DIR/verify.sh" "$STACK_ROOT"
} > "$VERIFY_WRAPPER"
chmod 755 "$VERIFY_WRAPPER"

write_desktop adaptive-openclaw-setup.desktop \
  "Adaptive + OpenClaw — Setup" \
  "Install or repair the reproducible Adaptive/OpenClaw environment" \
  "$BIN_DIR/adaptive-openclaw-setup"
write_desktop adaptive-openclaw-update.desktop \
  "Adaptive + OpenClaw — Update" \
  "Safely update Adaptive, skills, OpenClaw, and revalidate the stack" \
  "$BIN_DIR/adaptive-openclaw-update"
write_desktop adaptive-openclaw-verify.desktop \
  "Adaptive + OpenClaw — Verify" \
  "Run full environment and end-to-end validation" \
  "$BIN_DIR/adaptive-openclaw-verify"

DESKTOP_DIR=""
if command -v xdg-user-dir >/dev/null 2>&1; then
  DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
fi
if [[ -n "$DESKTOP_DIR" && -d "$DESKTOP_DIR" ]]; then
  for file in adaptive-openclaw-setup.desktop adaptive-openclaw-update.desktop adaptive-openclaw-verify.desktop; do
    cp "$APP_DIR/$file" "$DESKTOP_DIR/$file"
    chmod 755 "$DESKTOP_DIR/$file"
  done
  ok "Desktop shortcuts installed in $DESKTOP_DIR"
fi

ok "Application launchers installed"
ok "$BIN_DIR registered in shell startup PATH"
info "Commands: adaptive-openclaw-setup | adaptive-openclaw-update | adaptive-openclaw-verify"
if [[ ":${PATH}:" != *":$BIN_DIR:"* ]]; then
  warn "$BIN_DIR is not visible in this process PATH"
fi
info "A parent shell that was already open before setup cannot be modified in-place. Open a new terminal, or run: export PATH=\"$HOME/.local/bin:\$PATH\""
