#!/usr/bin/env bash
# Design Forge — Claude Code rules installer
# One-shot setup:
#   1. Clones the rules repo locally and wires it into Claude's global memory
#      (~/.claude/CLAUDE.md) so every Claude Code session auto-loads them.
#   2. Registers the Law 32 guardrail hook in ~/.claude/settings.json.
#   3. Links the agents and skills into ~/.claude/agents and ~/.claude/skills
#      so Claude Code registers them.
#   4. Installs `dforge-update` as a shell function that moves the clone to the
#      newest release tag and re-runs this installer. Every step is safe to re-run.
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
elif [ -d "$LOCAL_DIR/.git" ] && ! git -C "$LOCAL_DIR" symbolic-ref -q HEAD >/dev/null; then
  # A release checkout (detached HEAD) can't be pulled; dforge-update moves it.
  ok "On release $(git -C "$LOCAL_DIR" describe --tags --exact-match 2>/dev/null || echo "(detached)"); run dforge-update to update."
elif [ -d "$LOCAL_DIR/.git" ]; then
  say "Updating existing rules clone at $LOCAL_DIR ..."
  git -C "$LOCAL_DIR" pull --quiet --ff-only || die "git pull failed in $LOCAL_DIR"
  ok "Rules repo updated."
else
  say "Cloning rules repo to $LOCAL_DIR ..."
  git clone --quiet "$RULES_REPO" "$LOCAL_DIR" || die "git clone failed. Check your network connection."
  ok "Rules repo cloned."
fi

# 2b. A clone on a branch that sits exactly on the newest release moves onto
# that tag. No files change, so one run of any dforge-update (even one from
# before tagged releases) ends on the release (#168).
if git -C "$LOCAL_DIR" symbolic-ref -q HEAD >/dev/null \
    && [ -z "$(git -C "$LOCAL_DIR" status --porcelain --untracked-files=no)" ]; then
  LATEST_TAG=$(git -C "$LOCAL_DIR" tag --list 'v*' --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1 || true)
  if [ -n "$LATEST_TAG" ] \
      && [ "$(git -C "$LOCAL_DIR" rev-parse HEAD)" = "$(git -C "$LOCAL_DIR" rev-parse "$LATEST_TAG^{commit}")" ] \
      && git -C "$LOCAL_DIR" checkout --quiet --detach "$LATEST_TAG"; then
    ok "On release $LATEST_TAG."
  fi
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

# Bash commands, the file-editing tools so the hook can guard the
# guardrail files themselves (#117), and MCP tools for Law 38's tier 3
# and 4 asks (#138). PostToolUse on MCP tools records tier 3 approvals.
# Each entry is added once.
wanted = [
    ("PreToolUse", "Bash"),
    ("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit"),
    ("PreToolUse", "mcp__.*"),
    ("PostToolUse", "mcp__.*"),
]
for event, matcher in wanted:
    entries = hooks.setdefault(event, [])
    already = any(
        entry.get("matcher") == matcher
        and any(h.get("command") == hook_command for h in entry.get("hooks", []))
        for entry in entries
    )
    if not already:
        entries.append({
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
  warn "Could not update $GLOBAL_SETTINGS automatically — add the hook entries manually (see .claude/settings.json in $LOCAL_DIR)."
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
# Design Forge — move the Claude rules clone to the newest release and
# re-run the installer. Installed by design-forge install.sh (#116).
# A shell function, not a script in the clone, so `git checkout` never
# rewrites the code that's running. Runs in zsh and bash.
dforge-update() {
  local rules_dir="$HOME/.design-forge" mode=release approve=""
  local usage="usage: dforge-update [--main] [--approve <commit>]
  (no flag)           install the newest release tag (vX.Y.Z)
  --main              follow the main branch instead
  --approve <commit>  apply a hook change you approved in Claude's app
                      prompt; only that exact commit is installed
  A change to the hook asks first: in your own terminal, or through --approve."
  # if, not case: bash 3.2 misreads a case pattern's ")" inside this heredoc.
  while [ "$#" -gt 0 ]; do
    if [ "$1" = --main ]; then
      mode=main
    elif [ "$1" = --approve ] && [ -n "${2:-}" ]; then
      approve="$2"
      shift
    elif [ "$1" = -h ] || [ "$1" = --help ]; then
      printf '%s\n' "$usage"
      return 0
    else
      printf '%s\n' "$usage" >&2
      return 2
    fi
    shift
  done

  if [ ! -d "$rules_dir/.git" ]; then
    echo "dforge: $rules_dir is not a git clone. Re-run install.sh first." >&2
    return 1
  fi

  # Never overwrite edits to tracked files; gitignored data files don't count.
  local changed
  changed=$(command git -C "$rules_dir" status --porcelain --untracked-files=no) || return 1
  if [ -n "$changed" ]; then
    echo "dforge: $rules_dir has local changes. Nothing changed. Commit, stash or undo them first:" >&2
    printf '%s\n' "$changed" >&2
    return 1
  fi

  echo "dforge: checking for updates ..."
  if ! command git -C "$rules_dir" fetch --quiet --prune --prune-tags --force --tags origin; then
    echo "dforge: fetch failed. Nothing changed." >&2
    return 1
  fi

  local target label
  if [ "$mode" = release ]; then
    label=$(command git -C "$rules_dir" tag --list 'v*' --sort=-v:refname | command grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1 || true)
    if [ -z "$label" ]; then
      echo "dforge: no release tags yet; following main." >&2
      mode=main
    fi
  fi
  if [ "$mode" = main ]; then
    target=origin/main
    label=main
  else
    target="$label"
  fi

  local head new on_main=no
  head=$(command git -C "$rules_dir" rev-parse HEAD) || return 1
  new=$(command git -C "$rules_dir" rev-parse "$target^{commit}") || return 1
  [ "$(command git -C "$rules_dir" symbolic-ref -q --short HEAD)" = main ] && on_main=yes

  local version
  version=$(command grep -m1 -oE '\*\*Version:\*\* *[0-9]+\.[0-9]+\.[0-9]+' "$rules_dir/CLAUDE_LAWS.md" 2>/dev/null | awk '{print $2}')

  if [ "$head" = "$new" ] && { [ "$mode" = release ] || [ "$on_main" = yes ]; }; then
    if [ "$mode" = release ] && [ -n "$(command git -C "$rules_dir" symbolic-ref -q HEAD)" ]; then
      command git -C "$rules_dir" checkout --quiet --detach "$new" || return 1
    fi
    DFORGE_UPDATE=1 bash "$rules_dir/install.sh" || { echo "dforge: install.sh failed" >&2; return 1; }
    echo "dforge: already on $label (DESIGN_FORGE v${version:-?})."
    return 0
  fi

  # Never downgrade: a clone that followed main past the last release stays put.
  if [ "$mode" = release ] && command git -C "$rules_dir" merge-base --is-ancestor "$new" "$head"; then
    echo "dforge: you're ahead of the latest release, $label (on v${version:-?}). Nothing changed."
    echo "dforge: the next release tag moves you onto it; dforge-update --main follows main."
    return 0
  fi

  # --main moves the local main branch; it may only move forward to the
  # reviewed commit, never bring in commits of its own.
  # (No line continuations in this function: bash 3.2 drops them in the heredoc.)
  if [ "$mode" = main ] && command git -C "$rules_dir" rev-parse -q --verify refs/heads/main >/dev/null && ! command git -C "$rules_dir" merge-base --is-ancestor refs/heads/main "$new"; then
    echo "dforge: your local main has commits that aren't on origin/main. Nothing changed." >&2
    return 1
  fi

  # A change to anything the hook runs needs the user's yes: typed in a real
  # terminal, or clicked in the app's prompt for --approve (#170).
  if [ -n "$(command git -C "$rules_dir" diff --stat "$head" "$new" -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json)" ]; then
    echo "dforge: this update changes the Law 32 hook:"
    command git -C "$rules_dir" --no-pager diff --stat "$head" "$new" -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json
    command git -C "$rules_dir" --no-pager diff "$head" "$new" -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json
    if [ -n "$approve" ]; then
      # The app only asks when the hook is registered; without it, --approve
      # would be nobody's approval.
      if ! command grep -q 'enforce-laws.py' "$HOME/.claude/settings.json" 2>/dev/null; then
        echo "dforge: --approve needs the Law 32 hook in ~/.claude/settings.json, so the app asks you. Nothing changed. Run dforge-update in your own terminal." >&2
        return 1
      fi
      if [ "${#approve}" -lt 7 ] || [ "${new#"$approve"}" = "$new" ]; then
        echo "dforge: $approve isn't the update on offer (now $new). Nothing changed. Review the diff above, then approve that commit." >&2
        return 1
      fi
      echo "dforge: applying the hook change you approved ($new)."
    elif [ -t 0 ] && [ -t 1 ]; then
      local reply
      printf 'Apply this hook change? [y/N] '
      read -r reply
      if [ "$reply" != y ] && [ "$reply" != Y ] && [ "$reply" != yes ] && [ "$reply" != Yes ] && [ "$reply" != YES ]; then
        echo "dforge: nothing changed."
        return 1
      fi
    else
      echo "dforge: the hook changed. Nothing was applied. Run dforge-update in your own terminal to review and approve it, or approve it in Claude's app prompt: dforge-update --approve $new" >&2
      return 1
    fi
  fi

  # Check out the commit that was reviewed, by its SHA, not by a name a
  # fetch could move in the meantime.
  if [ "$mode" = main ]; then
    if ! command git -C "$rules_dir" checkout --quiet -B main "$new"; then
      echo "dforge: couldn't move to the latest main." >&2
      return 1
    fi
  elif ! command git -C "$rules_dir" checkout --quiet --detach "$new"; then
    echo "dforge: couldn't check out $label." >&2
    return 1
  fi

  # Checkout first, then run the installer, so the script never changes mid-run.
  DFORGE_UPDATE=1 bash "$rules_dir/install.sh" || { echo "dforge: install.sh failed" >&2; return 1; }

  version=$(command grep -m1 -oE '\*\*Version:\*\* *[0-9]+\.[0-9]+\.[0-9]+' "$rules_dir/CLAUDE_LAWS.md" 2>/dev/null | awk '{print $2}')
  if [ "$mode" = main ]; then
    echo "dforge: ready (DESIGN_FORGE v${version:-?}, main)."
  else
    echo "dforge: ready (DESIGN_FORGE v${version:-?}, tag $label)."
  fi
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
  warn "Update manually with: git -C $LOCAL_DIR fetch --tags && git -C $LOCAL_DIR checkout --detach <newest vX.Y.Z tag>"
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
     (installs the newest release, then re-runs this installer)
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
