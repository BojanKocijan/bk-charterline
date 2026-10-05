#!/usr/bin/env bash
# Design Forge — Claude Code rules installer
# One-shot setup:
#   1. Clones the rules repo locally and wires it into Claude's global memory
#      (~/.claude/CLAUDE.md) so every Claude Code session auto-loads them.
#   2. Registers the Law 32 guardrail hook in ~/.claude/settings.json.
#   3. Links the agents and skills into ~/.claude/agents and ~/.claude/skills
#      so Claude Code registers them.
#   4. Installs `dforge-update` as a shell function that pulls the clone and
#      re-runs this installer. Every step is safe to re-run.
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
command -v python3 >/dev/null 2>&1 || die "python3 is not installed. Install it first: https://www.python.org/downloads/"

# Replace (or leave untouched) the block between two marker lines in a file.
# Needed because macOS's awk ("one true awk") can't handle a multi-line
# string passed via -v — it throws "newline in string" and dies.
replace_block() {
  local file="$1" begin="$2" end="$3" block="$4"
  BLOCK_REPLACE_BEGIN="$begin" BLOCK_REPLACE_END="$end" BLOCK_REPLACE_TEXT="$block" \
    python3 - "$file" <<'PYEOF'
import os
import sys

path = sys.argv[1]
begin = os.environ["BLOCK_REPLACE_BEGIN"]
end = os.environ["BLOCK_REPLACE_END"]
block = os.environ["BLOCK_REPLACE_TEXT"]

with open(path) as f:
    lines = f.read().splitlines()

# A begin marker with no end marker after it would drop every line that
# follows it, so leave the file untouched and let the caller warn.
if begin in lines and end not in lines[lines.index(begin):]:
    sys.exit(3)

out = []
in_block = False
for line in lines:
    if line == begin:
        in_block = True
        out.append(block)
        continue
    if line == end:
        in_block = False
        continue
    if not in_block:
        out.append(line)

with open(path, "w") as f:
    f.write("\n".join(out) + "\n")
PYEOF
}

# 2. Clone or pull the rules repo (dforge-update has already pulled)
if [ -n "${DFORGE_UPDATE:-}" ]; then
  :
elif [ -d "$LOCAL_DIR/.git" ]; then
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
    if replace_block "$GLOBAL_MEMORY" "$MARKER_BEGIN" "$MARKER_END" "$BLOCK"; then
      ok "Refreshed Design Forge block in $GLOBAL_MEMORY"
    else
      warn "Left $GLOBAL_MEMORY unchanged: its '$MARKER_END' line is missing. Restore it, then re-run."
    fi
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

# Bash commands, plus the file-editing tools so the hook can guard the
# guardrail files themselves (#117). Each entry is added once.
for matcher in ("Bash", "Edit|Write|MultiEdit|NotebookEdit"):
    already = any(
        entry.get("matcher") == matcher
        and any(h.get("command") == hook_command for h in entry.get("hooks", []))
        for entry in pre_tool_use
    )
    if not already:
        pre_tool_use.append({
            "matcher": matcher,
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

# 6. Link agents and skills into ~/.claude so Claude Code registers them.
#    Only links that point into the clone are ever replaced or removed; the
#    user's own agents and skills with the same name are left alone.
AGENTS_DIR="${HOME}/.claude/agents"
SKILLS_DIR="${HOME}/.claude/skills"
SKIPPED=""

link_into() {
  local src="$1" dest="$2"
  if [ -L "$dest" ]; then
    case "$(readlink "$dest")" in
      "$LOCAL_DIR"/*) ln -sfn "$src" "$dest"; return 0 ;;
    esac
  fi
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    SKIPPED="$SKIPPED $(basename "$dest")"
    return 1
  fi
  ln -s "$src" "$dest"
}

# Remove links into the clone whose agent or skill was deleted upstream.
prune_dangling() {
  local link
  for link in "$1"/*; do
    if [ -L "$link" ] && [ ! -e "$link" ]; then
      case "$(readlink "$link")" in
        "$LOCAL_DIR"/*) rm "$link" ;;
      esac
    fi
  done
}

mkdir -p "$AGENTS_DIR" "$SKILLS_DIR"
prune_dangling "$AGENTS_DIR"
prune_dangling "$SKILLS_DIR"

AGENT_COUNT=0
for src in "$LOCAL_DIR"/agents/*.md; do
  [ -f "$src" ] || continue
  if link_into "$src" "$AGENTS_DIR/$(basename "$src")"; then
    AGENT_COUNT=$((AGENT_COUNT + 1))
  fi
done

SKILL_COUNT=0
for src in "$LOCAL_DIR"/skills/*; do
  [ -f "$src/SKILL.md" ] || continue
  if link_into "$src" "$SKILLS_DIR/$(basename "$src")"; then
    SKILL_COUNT=$((SKILL_COUNT + 1))
  fi
done

ok "Linked $AGENT_COUNT agents and $SKILL_COUNT skills into ${HOME}/.claude"
[ -z "$SKIPPED" ] || warn "Skipped, because your own file or link already uses the name:$SKIPPED"

# 7. Install dforge-update as a shell function
SHELL_RC=""
case "${SHELL:-}" in
  *zsh)  SHELL_RC="$HOME/.zshrc" ;;
  *bash) SHELL_RC="$HOME/.bashrc" ;;
esac

FN_BLOCK=$(cat <<'EOF'
# design-forge:fn:begin
# Design Forge — refresh the Claude rules clone and re-run the installer.
# Installed by design-forge install.sh.
dforge-update() {
  local rules_dir="$HOME/.design-forge"

  if [ ! -d "$rules_dir/.git" ]; then
    echo "dforge: $rules_dir is not a git clone. Re-run install.sh first." >&2
    return 1
  fi

  echo "dforge: pulling latest rules from main ..."
  git -C "$rules_dir" pull --ff-only || { echo "dforge: pull failed" >&2; return 1; }

  # Pull first, then run the installer, so the script never changes mid-run.
  DFORGE_UPDATE=1 bash "$rules_dir/install.sh" || { echo "dforge: install.sh failed" >&2; return 1; }

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
    if replace_block "$rc" "$FN_MARKER_BEGIN" "$FN_MARKER_END" "$FN_BLOCK"; then
      ok "Refreshed dforge-update function in $rc"
    else
      warn "Left $rc unchanged: its '$FN_MARKER_END' line is missing. Restore it, then re-run."
    fi
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

# 8. Done (dforge-update prints its own one-line summary instead)
[ -n "${DFORGE_UPDATE:-}" ] && exit 0

INSTALLED_VERSION=$(grep -m1 -oE '\*\*Version:\*\* *[0-9]+\.[0-9]+\.[0-9]+' "$LOCAL_DIR/CLAUDE_LAWS.md" 2>/dev/null | awk '{print $2}' || true)

cat <<EOF

${GREEN}Done.${RESET}

Five things are now wired up:

  1. Claude global memory  →  $GLOBAL_MEMORY
     (every Claude Code session auto-loads the Design Forge rules)
  2. dforge-update         →  shell function in ${SHELL_RC:-<no rc found>}
     (pulls the clone, then re-runs this installer)
  3. Law 32 guardrail hook →  $GLOBAL_SETTINGS
     (mechanically blocks merge/push-to-main/bad-commit-message/secret-commit tool calls)
  4. Agents                →  $AGENTS_DIR ($AGENT_COUNT linked)
  5. Skills                →  $SKILLS_DIR ($SKILL_COUNT linked)

Verify in a new Claude Code session:
  Rules loaded: DESIGN_FORGE v${INSTALLED_VERSION:-?}
  Project: <repo-name>
  Persona: Frontend
  GitHub: <username>
  Ready.

List the registered agents:
  claude agents

Keep everything fresh:
  dforge-update

Files on disk:
  Rules clone:    $LOCAL_DIR
  Global memory:  $GLOBAL_MEMORY (between design-forge:begin / design-forge:end markers)
EOF
