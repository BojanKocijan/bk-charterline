#!/usr/bin/env bash
# BK Charterline — Claude Code rules installer (renamed from Design Forge, #199)
# One-shot setup:
#   0. Moves an install from before the rename (~/.design-forge) to
#      ~/.bk-charterline, with its data files, and links the old name to it.
#   1. Clones the rules repo locally and wires it into Claude's global memory
#      (~/.claude/CLAUDE.md) so every Claude Code session auto-loads them.
#   2. Registers the Law 32 guardrail hook in ~/.claude/settings.json.
#   3. Links the agents, skills and output styles into ~/.claude/agents, ~/.claude/skills
#      and ~/.claude/output-styles (a style stays off until the user picks it)
#      so Claude Code registers them.
#   4. Installs `charterline-update` as a shell function that moves the clone to
#      the newest release tag and re-runs this installer. Every step is safe to re-run.
#
# Run once:
#   curl -fsSL https://raw.githubusercontent.com/BojanKocijan/bk-charterline/main/install.sh | bash
#
# Update anytime: type `update rules` in Claude Code, or run charterline-update

set -euo pipefail

RULES_REPO="https://github.com/BojanKocijan/bk-charterline.git"
LOCAL_DIR="${HOME}/.bk-charterline"
GLOBAL_MEMORY="${HOME}/.claude/CLAUDE.md"
IMPORT_LINE="@${HOME}/.bk-charterline/CLAUDE.md"
MARKER_BEGIN="<!-- bk-charterline:begin -->"
MARKER_END="<!-- bk-charterline:end -->"

# Shell-rc function markers
FN_MARKER_BEGIN="# bk-charterline:fn:begin"
FN_MARKER_END="# bk-charterline:fn:end"

# The names from before v3.0.0, which step 1b moves away from (#199)
OLD_DIR="${HOME}/.design-forge"
OLD_MARKER_BEGIN="<!-- design-forge:begin -->"
OLD_MARKER_END="<!-- design-forge:end -->"
OLD_FN_MARKER_BEGIN="# design-forge:fn:begin"
OLD_FN_MARKER_END="# design-forge:fn:end"

# Set when the update function runs this installer: the new one sets
# CHARTERLINE_UPDATE, the update function from before v3.0.0 DFORGE_UPDATE.
UPDATING="${CHARTERLINE_UPDATE:-}${DFORGE_UPDATE:-}"

# Colors (skip if not a TTY)
if [ -t 1 ]; then
  BLUE=$'\033[0;34m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; RED=$'\033[0;31m'; RESET=$'\033[0m'
else
  BLUE=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi

say() { printf "%s[bk-charterline]%s %s\n" "$BLUE" "$RESET" "$1"; }
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

# 1b. Move an install from before the rename (#199). One rename on the same
# disk, so the data files inside (projects.yaml, the hook log, the Law 38
# registry and approvals, the patterns) move untouched. The old name stays
# as a link for v3.0.0, so anything still pointing at it keeps working.
# bash keeps reading this script through its open file, so moving the folder
# it runs from is safe; everything below uses the new path.
if [ -d "$OLD_DIR" ] && [ ! -L "$OLD_DIR" ]; then
  if [ -e "$LOCAL_DIR" ] || [ -L "$LOCAL_DIR" ]; then
    die "Both $OLD_DIR and $LOCAL_DIR exist, so nothing moved. Keep the one with your data files (projects.yaml, hook-log.jsonl, ai-tools.json), remove the other, then run the update again."
  fi
  if [ -d "$OLD_DIR/.git" ] && [ -n "$(git -C "$OLD_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    die "$OLD_DIR has local changes, so nothing moved. Commit, stash or undo them, then run the update again."
  fi
  mv "$OLD_DIR" "$LOCAL_DIR" || die "Couldn't move $OLD_DIR to $LOCAL_DIR. Nothing changed; the old name still works."
  ln -s "$LOCAL_DIR" "$OLD_DIR" || warn "Moved, but couldn't link $OLD_DIR to $LOCAL_DIR; anything still using the old path needs updating by hand."
  if [ -d "$LOCAL_DIR/.git" ]; then
    git -C "$LOCAL_DIR" remote set-url origin "$RULES_REPO" || warn "Couldn't point the clone at $RULES_REPO; run: git -C $LOCAL_DIR remote set-url origin $RULES_REPO"
  fi
  ok "Design Forge is now BK Charterline: moved $OLD_DIR to $LOCAL_DIR, and the old name links to it."
fi

# 2. Clone or pull the rules repo (the update function has already pulled)
FIRST_INSTALL=""  # set when this run makes the clone; one-time hints show only then
if [ -n "$UPDATING" ]; then
  :
elif [ -d "$LOCAL_DIR/.git" ] && ! git -C "$LOCAL_DIR" symbolic-ref -q HEAD >/dev/null; then
  # A release checkout (detached HEAD) can't be pulled; the update function moves it.
  ok "On release $(git -C "$LOCAL_DIR" describe --tags --exact-match 2>/dev/null || echo "(detached)"); type 'update rules' in Claude Code to update."
elif [ -d "$LOCAL_DIR/.git" ]; then
  say "Updating existing rules clone at $LOCAL_DIR ..."
  git -C "$LOCAL_DIR" pull --quiet --ff-only || die "git pull failed in $LOCAL_DIR"
  ok "Rules repo updated."
else
  say "Cloning rules repo to $LOCAL_DIR ..."
  git clone --quiet "$RULES_REPO" "$LOCAL_DIR" || die "git clone failed. Check your network connection."
  ok "Rules repo cloned."
  FIRST_INSTALL=1
fi

# 2b. A clone on a branch that sits exactly on the newest release moves onto
# that tag. No files change, so one run of any update function (even one from
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
# BK Charterline governance — auto-installed
# Edit ~/.bk-charterline/ to change rules (update with: update rules, or charterline-update)
$IMPORT_LINE
$MARKER_END
EOF
)

if [ -f "$GLOBAL_MEMORY" ]; then
  if grep -q "$MARKER_BEGIN" "$GLOBAL_MEMORY"; then
    if replace_block "$GLOBAL_MEMORY" "$MARKER_BEGIN" "$MARKER_END" "$BLOCK"; then
      ok "Refreshed BK Charterline block in $GLOBAL_MEMORY"
    else
      warn "Left $GLOBAL_MEMORY unchanged: its '$MARKER_END' line is missing. Restore it, then re-run."
    fi
  elif grep -q "$OLD_MARKER_BEGIN" "$GLOBAL_MEMORY"; then
    if replace_block "$GLOBAL_MEMORY" "$OLD_MARKER_BEGIN" "$OLD_MARKER_END" "$BLOCK"; then
      ok "Replaced the Design Forge block in $GLOBAL_MEMORY with BK Charterline's"
    else
      warn "Left $GLOBAL_MEMORY unchanged: its '$OLD_MARKER_END' line is missing. Restore it, then re-run."
    fi
  else
    printf "\n%s\n" "$BLOCK" >> "$GLOBAL_MEMORY"
    ok "Appended BK Charterline block to $GLOBAL_MEMORY"
  fi
else
  printf "%s\n" "$BLOCK" > "$GLOBAL_MEMORY"
  ok "Created $GLOBAL_MEMORY with BK Charterline block"
fi

# 5. Register the Law 32 guardrail hook globally (~/.claude/settings.json)
GLOBAL_SETTINGS="${HOME}/.claude/settings.json"
HOOK_SCRIPT="${LOCAL_DIR}/.claude/hooks/enforce-laws.py"
HOOK_COMMAND="python3 \"${HOOK_SCRIPT}\""
OLD_HOOK_COMMAND="python3 \"${OLD_DIR}/.claude/hooks/enforce-laws.py\""
PERSONA_COMMAND="python3 \"${LOCAL_DIR}/.claude/hooks/persona_log.py\""

mkdir -p "$(dirname "$GLOBAL_SETTINGS")"
[ -f "$GLOBAL_SETTINGS" ] || printf '{}\n' > "$GLOBAL_SETTINGS"
if python3 - "$GLOBAL_SETTINGS" "$HOOK_COMMAND" "$OLD_HOOK_COMMAND" "$PERSONA_COMMAND" <<'PYEOF'
import json
import sys

path, hook_command, old_command, persona_command = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

with open(path) as f:
    original = f.read()
settings = json.loads(original) if original.strip() else {}

hooks = settings.setdefault("hooks", {})

# Re-point our hook from the folder's old name (#199). Only entries whose
# command is exactly our old hook change; a backup comes first.
moved = 0
for entries in hooks.values():
    for entry in entries if isinstance(entries, list) else []:
        for h in entry.get("hooks", []) if isinstance(entry, dict) else []:
            if isinstance(h, dict) and h.get("command") == old_command:
                h["command"] = hook_command
                moved += 1
if moved:
    with open(path + ".bk-charterline.bak", "w") as f:
        f.write(original)

# Bash commands, the file-editing tools so the hook can guard the
# guardrail files themselves (#117), and MCP tools for Law 38's tier 3
# and 4 asks (#138). PostToolUse on MCP tools records tier 3 approvals.
# UserPromptSubmit logs mode commands for the dashboard (#256); it has no
# matcher. Each entry is added once.
wanted = [
    ("PreToolUse", "Bash", hook_command),
    ("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit", hook_command),
    ("PreToolUse", "mcp__.*", hook_command),
    ("PostToolUse", "mcp__.*", hook_command),
    ("UserPromptSubmit", None, persona_command),
]
for event, matcher, command in wanted:
    entries = hooks.setdefault(event, [])
    already = any(
        entry.get("matcher") == matcher
        and any(h.get("command") == command for h in entry.get("hooks", []))
        for entry in entries
    )
    if not already:
        entry = {"hooks": [{"type": "command", "command": command}]}
        if matcher is not None:
            entry = {"matcher": matcher, **entry}
        entries.append(entry)

text = json.dumps(settings, indent=2) + "\n"
if text != original:  # a second run writes nothing
    with open(path, "w") as f:
        f.write(text)
PYEOF
then
  ok "Registered Law 32 guardrail hook in $GLOBAL_SETTINGS"
else
  warn "Could not update $GLOBAL_SETTINGS automatically — add the hook entries manually (see .claude/settings.json in $LOCAL_DIR)."
fi

# 6. Link agents and skills into ~/.claude so Claude Code registers them.
#    Only links that point into the clone (under its new or old name) are
#    ever replaced or removed; the
#    user's own agents and skills with the same name are left alone.
AGENTS_DIR="${HOME}/.claude/agents"
SKILLS_DIR="${HOME}/.claude/skills"
STYLES_DIR="${HOME}/.claude/output-styles"
SKIPPED=""

link_into() {
  local src="$1" dest="$2"
  if [ -L "$dest" ]; then
    case "$(readlink "$dest")" in
      "$LOCAL_DIR"/*|"$OLD_DIR"/*) ln -sfn "$src" "$dest"; return 0 ;;
    esac
  fi
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    SKIPPED="$SKIPPED $(basename "$dest")"
    return 1
  fi
  ln -s "$src" "$dest"
}

# Remove links into the clone whose agent, skill or style was deleted upstream.
prune_dangling() {
  local link
  for link in "$1"/*; do
    if [ -L "$link" ] && [ ! -e "$link" ]; then
      case "$(readlink "$link")" in
        "$LOCAL_DIR"/*|"$OLD_DIR"/*) rm "$link" ;;
      esac
    fi
  done
}

mkdir -p "$AGENTS_DIR" "$SKILLS_DIR" "$STYLES_DIR"
prune_dangling "$AGENTS_DIR"
prune_dangling "$SKILLS_DIR"
prune_dangling "$STYLES_DIR"

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

# Output styles (#229): linked, never switched on. The user picks one with /output-style.
STYLE_COUNT=0
for src in "$LOCAL_DIR"/output-styles/*.md; do
  [ -f "$src" ] || continue
  if link_into "$src" "$STYLES_DIR/$(basename "$src")"; then
    STYLE_COUNT=$((STYLE_COUNT + 1))
  fi
done

ok "Linked $AGENT_COUNT agents, $SKILL_COUNT skills and $STYLE_COUNT output styles into ${HOME}/.claude"
# One-time hints, on the run that made the clone only (#229, #231).
if [ -n "$FIRST_INSTALL" ]; then
  [ "$STYLE_COUNT" -eq 0 ] || say "Want a coworker with a sense of humor? Type /output-style coworker in Claude Code; /output-style default turns it off."
  # Anthropic's own plugins join the team when installed (TEAM_WORKFLOW §8); never installed for you.
  say "Optional: Anthropic's design, engineering and frontend-design plugins join the team. How to add them: https://github.com/BojanKocijan/bk-charterline#installation"
fi
[ -z "$SKIPPED" ] || warn "Skipped, because your own file or link already uses the name:$SKIPPED"

# 7. Install charterline-update as a shell function
SHELL_RC=""
case "${SHELL:-}" in
  *zsh)  SHELL_RC="$HOME/.zshrc" ;;
  *bash) SHELL_RC="$HOME/.bashrc" ;;
esac

FN_BLOCK=$(cat <<'EOF'
# bk-charterline:fn:begin
# BK Charterline — move the Claude rules clone to the newest release and
# re-run the installer. Installed by bk-charterline install.sh (#116, #199).
# A shell function, not a script in the clone, so `git checkout` never
# rewrites the code that's running. Runs in zsh and bash.
charterline-update() {
  local rules_dir="$HOME/.bk-charterline" mode=release approve=""
  local usage="usage: charterline-update [--main] [--approve <commit>]
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
    echo "charterline: $rules_dir is not a git clone. Re-run install.sh first." >&2
    return 1
  fi

  # Never overwrite edits to tracked files; gitignored data files don't count.
  local changed
  changed=$(command git -C "$rules_dir" status --porcelain --untracked-files=no) || return 1
  if [ -n "$changed" ]; then
    echo "charterline: $rules_dir has local changes. Nothing changed. Commit, stash or undo them first:" >&2
    printf '%s\n' "$changed" >&2
    return 1
  fi

  echo "charterline: checking for updates ..."
  if ! command git -C "$rules_dir" fetch --quiet --prune --prune-tags --force --tags origin; then
    echo "charterline: fetch failed. Nothing changed." >&2
    return 1
  fi

  local target label
  if [ "$mode" = release ]; then
    label=$(command git -C "$rules_dir" tag --list 'v*' --sort=-v:refname | command grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1 || true)
    if [ -z "$label" ]; then
      echo "charterline: no release tags yet; following main." >&2
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
    CHARTERLINE_UPDATE=1 bash "$rules_dir/install.sh" || { echo "charterline: install.sh failed" >&2; return 1; }
    echo "charterline: already on $label (BK CHARTERLINE v${version:-?})."
    return 0
  fi

  # Never downgrade: a clone that followed main past the last release stays put.
  if [ "$mode" = release ] && command git -C "$rules_dir" merge-base --is-ancestor "$new" "$head"; then
    echo "charterline: you're ahead of the latest release, $label (on v${version:-?}). Nothing changed."
    echo "charterline: the next release tag moves you onto it; charterline-update --main follows main."
    return 0
  fi

  # --main moves the local main branch; it may only move forward to the
  # reviewed commit, never bring in commits of its own.
  # (No line continuations in this function: bash 3.2 drops them in the heredoc.)
  if [ "$mode" = main ] && command git -C "$rules_dir" rev-parse -q --verify refs/heads/main >/dev/null && ! command git -C "$rules_dir" merge-base --is-ancestor refs/heads/main "$new"; then
    echo "charterline: your local main has commits that aren't on origin/main. Nothing changed." >&2
    return 1
  fi

  # A change to anything the hook runs needs the user's yes: typed in a real
  # terminal, or clicked in the app's prompt for --approve (#170).
  if [ -n "$(command git -C "$rules_dir" diff --stat "$head" "$new" -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json)" ]; then
    echo "charterline: this update changes the Law 32 hook:"
    command git -C "$rules_dir" --no-pager diff --stat "$head" "$new" -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json
    command git -C "$rules_dir" --no-pager diff "$head" "$new" -- .claude/hooks scripts/ai_tools.py install.sh .claude/settings.json
    if [ -n "$approve" ]; then
      # The app only asks when the hook is registered; without it, --approve
      # would be nobody's approval.
      if ! command grep -q 'enforce-laws.py' "$HOME/.claude/settings.json" 2>/dev/null; then
        echo "charterline: --approve needs the Law 32 hook in ~/.claude/settings.json, so the app asks you. Nothing changed. Run charterline-update in your own terminal." >&2
        return 1
      fi
      if [ "${#approve}" -lt 7 ] || [ "${new#"$approve"}" = "$new" ]; then
        echo "charterline: $approve isn't the update on offer (now $new). Nothing changed. Review the diff above, then approve that commit." >&2
        return 1
      fi
      echo "charterline: applying the hook change you approved ($new)."
    elif [ -t 0 ] && [ -t 1 ]; then
      local reply
      printf 'Apply this hook change? [y/N] '
      read -r reply
      if [ "$reply" != y ] && [ "$reply" != Y ] && [ "$reply" != yes ] && [ "$reply" != Yes ] && [ "$reply" != YES ]; then
        echo "charterline: nothing changed."
        return 1
      fi
    else
      echo "charterline: the hook changed. Nothing was applied. Run charterline-update in your own terminal to review and approve it, or approve it in Claude's app prompt: charterline-update --approve $new" >&2
      return 1
    fi
  fi

  # Check out the commit that was reviewed, by its SHA, not by a name a
  # fetch could move in the meantime.
  if [ "$mode" = main ]; then
    if ! command git -C "$rules_dir" checkout --quiet -B main "$new"; then
      echo "charterline: couldn't move to the latest main." >&2
      return 1
    fi
  elif ! command git -C "$rules_dir" checkout --quiet --detach "$new"; then
    echo "charterline: couldn't check out $label." >&2
    return 1
  fi

  # Checkout first, then run the installer, so the script never changes mid-run.
  CHARTERLINE_UPDATE=1 bash "$rules_dir/install.sh" || { echo "charterline: install.sh failed" >&2; return 1; }

  version=$(command grep -m1 -oE '\*\*Version:\*\* *[0-9]+\.[0-9]+\.[0-9]+' "$rules_dir/CLAUDE_LAWS.md" 2>/dev/null | awk '{print $2}')
  if [ "$mode" = main ]; then
    echo "charterline: ready (BK CHARTERLINE v${version:-?}, main)."
  else
    echo "charterline: ready (BK CHARTERLINE v${version:-?}, tag $label)."
  fi
}
# Design Forge's old command, for v3.0.0 only (#199).
dforge-update() {
  echo "Design Forge is now BK Charterline: running charterline-update." >&2
  charterline-update "$@"
}
# bk-charterline:fn:end
EOF
)

install_or_update_function() {
  local rc="$1"
  [ -z "$rc" ] && return 0

  if [ -f "$rc" ] && grep -q "$FN_MARKER_BEGIN" "$rc"; then
    if replace_block "$rc" "$FN_MARKER_BEGIN" "$FN_MARKER_END" "$FN_BLOCK"; then
      ok "Refreshed charterline-update function in $rc"
    else
      warn "Left $rc unchanged: its '$FN_MARKER_END' line is missing. Restore it, then re-run."
    fi
  elif [ -f "$rc" ] && grep -q "$OLD_FN_MARKER_BEGIN" "$rc"; then
    if replace_block "$rc" "$OLD_FN_MARKER_BEGIN" "$OLD_FN_MARKER_END" "$FN_BLOCK"; then
      ok "Replaced dforge-update in $rc with charterline-update (dforge-update points to it for v3.0.0)"
    else
      warn "Left $rc unchanged: its '$OLD_FN_MARKER_END' line is missing. Restore it, then re-run."
    fi
  else
    printf "\n%s\n" "$FN_BLOCK" >> "$rc"
    ok "Installed charterline-update function in $rc"
    warn "Reload your shell or run: source $rc"
  fi
}

if [ -n "$SHELL_RC" ]; then
  install_or_update_function "$SHELL_RC"
else
  warn "Unknown shell; skipped function install."
  warn "Update manually with: git -C $LOCAL_DIR fetch --tags && git -C $LOCAL_DIR checkout --detach <newest vX.Y.Z tag>"
fi

# 7b. Build the private dashboard (#120): what the rules did for you, in
# $LOCAL_DIR/dashboard/ (gitignored, never sent). It never fails the install.
if [ -f "$LOCAL_DIR/scripts/my_metrics.py" ]; then
  if DASH_OUT=$(python3 "$LOCAL_DIR/scripts/my_metrics.py" 2>&1); then
    ok "Built your dashboard: $LOCAL_DIR/dashboard/index.html"
  else
    warn "Couldn't build your dashboard this time; type 'my metrics' in Claude Code to try again. ($(printf '%s\n' "$DASH_OUT" | tail -n 1))"
  fi
fi

# 8. Done (the update function prints its own one-line summary instead)
[ -n "$UPDATING" ] && exit 0

INSTALLED_VERSION=$(grep -m1 -oE '\*\*Version:\*\* *[0-9]+\.[0-9]+\.[0-9]+' "$LOCAL_DIR/CLAUDE_LAWS.md" 2>/dev/null | awk '{print $2}' || true)

cat <<EOF

${GREEN}Done.${RESET}

Five things are now wired up:

  1. Claude global memory  →  $GLOBAL_MEMORY
     (every Claude Code session auto-loads the BK Charterline rules)
  2. charterline-update    →  shell function in ${SHELL_RC:-<no rc found>}
     (installs the newest release, then re-runs this installer)
  3. Law 32 guardrail hook →  $GLOBAL_SETTINGS
     (mechanically blocks merge/push-to-main/bad-commit-message/secret-commit tool calls)
  4. Agents                →  $AGENTS_DIR ($AGENT_COUNT linked)
  5. Skills                →  $SKILLS_DIR ($SKILL_COUNT linked)

Verify in a new Claude Code session:
  Rules loaded: BK CHARTERLINE v${INSTALLED_VERSION:-?}
  Project: <repo-name>
  Persona: Frontend
  GitHub: <username>
  Ready.

List the registered agents:
  claude agents

Keep everything fresh: type 'update rules' in Claude Code, or run
  charterline-update

Files on disk:
  Rules clone:    $LOCAL_DIR
  Global memory:  $GLOBAL_MEMORY (between bk-charterline:begin / bk-charterline:end markers)
EOF
