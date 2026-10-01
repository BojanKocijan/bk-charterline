#!/usr/bin/env bash
# Design Forge — Claude Code rules installer
# One-shot setup:
#   1. Clones the rules repo locally and wires it into Claude's global memory
#      (~/.claude/CLAUDE.md) so every Claude Code session auto-loads them.
#   2. Installs `dforge-update` as a shell function that refreshes the clone.
#
# Run once:
#   curl -fsSL https://raw.githubusercontent.com/bojankocijan/design-forge/main/install.sh | bash
#
# Update anytime:
#   dforge-update

set -euo pipefail

RULES_REPO="https://github.com/bojankocijan/design-forge.git"
LOCAL_DIR="${HOME}/.design-forge"
GLOBAL_MEMORY="${HOME}/.claude/CLAUDE.md"
IMPORT_LINE="@${HOME}/.design-forge/CLAUDE.md"
MARKER_BEGIN="<!-- design-forge:begin -->"
MARKER_END="<!-- design-forge:end -->"

# Shell-rc function markers
FN_MARKER_BEGIN="# design-forge:fn:begin"
FN_MARKER_END="# design-forge:fn:end"

# Colors (skip if not a TTY)
if [ -t 1 ]; then
  BLUE=$'\033[0;34m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
else
  BLUE=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

say() { printf "%s[design-forge]%s %s\n" "$BLUE" "$RESET" "$1"; }
ok()  { printf "%s✓%s %s\n"             "$GREEN" "$RESET" "$1"; }
warn(){ printf "%s!%s %s\n"             "$YELLOW" "$RESET" "$1"; }
die() { printf "%s✗%s %s\n"             "$RED"    "$RESET" "$1" >&2; exit 1; }

# 1. Sanity checks
command -v git >/dev/null 2>&1 || die "git is not installed. Install it first: https://git-scm.com/downloads"

# 2. Clone or pull the rules repo
if [ -d "$LOCAL_DIR/.git" ]; then
  say "Updating existing rules clone at $LOCAL_DIR ..."
  git -C "$LOCAL_DIR" pull --quiet --ff-only || die "git pull failed in $LOCAL_DIR"
  ok "Rules repo updated."
else
  say "Cloning rules repo to $LOCAL_DIR ..."
  git clone --quiet "$RULES_REPO" "$LOCAL_DIR" || die "git clone failed. Check your network connection."
  ok "Rules repo cloned."
fi

# 3. Ensure ~/.claude/ exists
mkdir -p "$(dirname "$GLOBAL_MEMORY")"

# 4. Write (or update) the import block in ~/.claude/CLAUDE.md
BLOCK=$(cat <<EOF
$MARKER_BEGIN
# Design Forge governance — auto-installed by dforge
# Edit ~/.design-forge/ to change rules (pull latest with: dforge-update)
$IMPORT_LINE
$MARKER_END
EOF
)

if [ -f "$GLOBAL_MEMORY" ]; then
  if grep -q "$MARKER_BEGIN" "$GLOBAL_MEMORY"; then
    # Replace the existing block using awk (portable; no in-place sed needed)
    tmp=$(mktemp)
    awk -v begin="$MARKER_BEGIN" -v end="$MARKER_END" -v block="$BLOCK" '
      $0==begin { inblock=1; print block; next }
      $0==end   { inblock=0; next }
      !inblock  { print }
    ' "$GLOBAL_MEMORY" > "$tmp"
    mv "$tmp" "$GLOBAL_MEMORY"
    ok "Refreshed Design Forge block in $GLOBAL_MEMORY"
  else
    printf "\n%s\n" "$BLOCK" >> "$GLOBAL_MEMORY"
    ok "Appended Design Forge block to $GLOBAL_MEMORY"
  fi
else
  printf "%s\n" "$BLOCK" > "$GLOBAL_MEMORY"
  ok "Created $GLOBAL_MEMORY with Design Forge block"
fi

# 5. Register the Law 32 guardrail hook globally (~/.claude/settings.json)
GLOBAL_SETTINGS="${HOME}/.claude/settings.json"
HOOK_SCRIPT="${LOCAL_DIR}/.claude/hooks/enforce-laws.py"
HOOK_COMMAND="python3 \"${HOOK_SCRIPT}\""

if command -v python3 >/dev/null 2>&1; then
  mkdir -p "$(dirname "$GLOBAL_SETTINGS")"
  [ -f "$GLOBAL_SETTINGS" ] || printf '{}\n' > "$GLOBAL_SETTINGS"
  if python3 - "$GLOBAL_SETTINGS" "$HOOK_COMMAND" <<'PYEOF'
import json
import sys

path, hook_command = sys.argv[1], sys.argv[2]

with open(path) as f:
    content = f.read().strip()
settings = json.loads(content) if content else {}

hooks = settings.setdefault("hooks", {})
pre_tool_use = hooks.setdefault("PreToolUse", [])

already = any(
    entry.get("matcher") == "Bash"
    and any(h.get("command") == hook_command for h in entry.get("hooks", []))
    for entry in pre_tool_use
)
if not already:
    pre_tool_use.append({
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": hook_command}],
    })

with open(path, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
PYEOF
  then
    ok "Registered Law 32 guardrail hook in $GLOBAL_SETTINGS"
  else
    warn "Could not update $GLOBAL_SETTINGS automatically — add the PreToolUse hook manually (see .claude/settings.json in $LOCAL_DIR for the entry)."
  fi
else
  warn "python3 not found; skipped global hook registration. Install python3 and re-run, or copy the PreToolUse entry from $LOCAL_DIR/.claude/settings.json into $GLOBAL_SETTINGS yourself."
fi

# 6. Install dforge-update as a shell function
SHELL_RC=""
case "${SHELL:-}" in
  *zsh)  SHELL_RC="$HOME/.zshrc" ;;
  *bash) SHELL_RC="$HOME/.bashrc" ;;
esac

FN_BLOCK=$(cat <<'EOF'
# design-forge:fn:begin
# Design Forge — refresh the Claude rules clone.
# Installed by design-forge install.sh.
dforge-update() {
  local rules_dir="$HOME/.design-forge"

  if [ ! -d "$rules_dir/.git" ]; then
    echo "dforge: $rules_dir is not a git clone. Re-run install.sh first." >&2
    return 1
  fi

  echo "dforge: pulling latest rules from main ..."
  git -C "$rules_dir" pull --ff-only || { echo "dforge: pull failed" >&2; return 1; }

  local version
  version=$(grep -m1 -oE '\*\*Version:\*\* *[0-9]+\.[0-9]+\.[0-9]+' "$rules_dir/CLAUDE_LAWS.md" 2>/dev/null | awk '{print $2}')
  echo "dforge: ready (DESIGN_FORGE v${version:-?})."
}
# design-forge:fn:end
EOF
)

install_or_update_function() {
  local rc="$1"
  [ -z "$rc" ] && return 0

  if [ -f "$rc" ] && grep -q "$FN_MARKER_BEGIN" "$rc"; then
    tmp=$(mktemp)
    awk -v begin="$FN_MARKER_BEGIN" -v end="$FN_MARKER_END" -v block="$FN_BLOCK" '
      $0==begin { inblock=1; print block; next }
      $0==end   { inblock=0; next }
      !inblock  { print }
    ' "$rc" > "$tmp"
    mv "$tmp" "$rc"
    ok "Refreshed dforge-update function in $rc"
  else
    printf "\n%s\n" "$FN_BLOCK" >> "$rc"
    ok "Installed dforge-update function in $rc"
    warn "Reload your shell or run: source $rc"
  fi
}

if [ -n "$SHELL_RC" ]; then
  install_or_update_function "$SHELL_RC"
else
  warn "Unknown shell; skipped function install."
  warn "Update manually with: git -C $LOCAL_DIR pull --ff-only"
fi

# 7. Done
cat <<EOF

${GREEN}Done.${RESET}

Three things are now wired up:

  1. Claude global memory  →  $GLOBAL_MEMORY
     (every Claude Code session auto-loads the Design Forge rules)
  2. dforge-update         →  shell function in ${SHELL_RC:-<no rc found>}
     (refreshes the rules clone)
  3. Law 32 guardrail hook →  $GLOBAL_SETTINGS
     (mechanically blocks merge/push-to-main/bad-commit-message/secret-commit tool calls)

Verify in Claude Code:
  Rules loaded: DESIGN_FORGE v1.0.0
  Project: <repo-name>
  Persona: Frontend
  GitHub: <username>
  Ready.

Keep everything fresh:
  dforge-update

Files on disk:
  Rules clone:    $LOCAL_DIR
  Global memory:  $GLOBAL_MEMORY (between design-forge:begin / design-forge:end markers)
EOF
