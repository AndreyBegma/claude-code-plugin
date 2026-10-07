#!/usr/bin/env bash
#
# Launch one Code Sentinel worker session: its own git worktree, its own tmux
# session, its own Remote Control channel, its own brief.
#
# Used by the orchestrator skill. The launch command lives here rather than in
# the skill so that there is one place where it can be wrong.
#
#   dispatch.sh <slot> <branch> <brief-path> [model] [base] [delay]
#
#   slot    short handle, lowercase: i42, auth-fix
#   branch  full branch name: feat/FEAT-20261006-001-login-rate-limit
#   brief   path to the assignment written by the orchestrator
#   model   opus | sonnet | fable (default: sonnet). The orchestrator classifies
#           every slot and passes the model deliberately — always pass it.
#   base    branch to cut from (default: $CS_BASE, else origin's default branch)
#   delay   seconds to hold before the agent starts (default: 0). The wait
#           happens inside the detached tmux session, so `tmux kill-session
#           -t cs-<slot>` during the window stops the agent before it reads
#           anything.
#
# Environment
#   CS_REPO        repository to cut the worktree from (default: git toplevel of
#                  the current directory)
#   CS_BASE        default base branch (see above)
#   CS_WORKER_CMD  first prompt of the worker (default:
#                  "/code-sentinel:worker .orchestrator-brief.md")
#   CLAUDE_CONFIG_DIR  which Claude Code configuration to pre-flight and run
#                  under — resolved by `claude_config.py`, never guessed.
#
# Layout
#   worktree   <parent of repo>/.wt-<repo basename>-<slot>
#   session    cs-<slot>   (tmux name, Remote Control name and `-n` name)
#
set -euo pipefail

SLOT=${1:?slot required, e.g. i42}
BRANCH=${2:?branch required, e.g. feat/FEAT-20261006-001-short-name}
BRIEF=${3:?brief path required}
MODEL=${4:-sonnet}
DELAY=${6:-0}

case "$DELAY" in
  ''|*[!0-9]*) echo "dispatch: delay must be whole seconds, got '$DELAY'" >&2; exit 1 ;;
esac

case "$MODEL" in
  opus|sonnet|fable|haiku) ;;
  *) echo "dispatch: model must be opus, sonnet, fable or haiku, got '$MODEL'" >&2; exit 1 ;;
esac

case "$SLOT" in
  *[!a-z0-9-]*|'') echo "dispatch: slot must be lowercase letters, digits and '-', got '$SLOT'" >&2; exit 1 ;;
esac

REPO="${CS_REPO:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
[ -n "$REPO" ] && [ -d "$REPO" ] || { echo "dispatch: no repository — run inside one or set CS_REPO" >&2; exit 1; }
# A linked worktree's toplevel is the worktree; the fleet always cuts from the
# main checkout, which is the parent of the common git dir.
REPO="$(dirname "$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)")"

default_base() {
  local b
  b="$(git -C "$REPO" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  [ -n "$b" ] && { echo "${b#origin/}"; return 0; }
  b="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || true)"
  [ -n "$b" ] && { echo "$b"; return 0; }
  echo main
}
BASE=${5:-${CS_BASE:-$(cd "$REPO" && default_base)}}

WT="$(dirname "$REPO")/.wt-$(basename "$REPO")-$SLOT"
NAME="cs-$SLOT"
WORKER_CMD="${CS_WORKER_CMD:-/code-sentinel:worker .orchestrator-brief.md}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

command -v tmux >/dev/null || { echo "dispatch: tmux is not installed" >&2; exit 1; }
command -v claude >/dev/null || { echo "dispatch: claude is not on PATH" >&2; exit 1; }
command -v python3 >/dev/null || {
  echo "dispatch: python3 is not installed, so the ownership fence hook cannot" >&2
  echo "          run. Launching would put an unfenced worker in a shared repository." >&2
  exit 1
}

CLAUDE_CFG_DIR="$(python3 "$HERE/claude_config.py" --config-dir)"
[ -f "$BRIEF" ] || { echo "dispatch: brief not found: $BRIEF" >&2; exit 1; }
BRIEF="$(cd "$(dirname "$BRIEF")" && pwd)/$(basename "$BRIEF")"

# A brief whose `owns:` list is shadowed by its own `never:` list grants
# nothing. The same parse the hook uses runs here, before anything exists, so
# the mistake is visible in the orchestrator's own terminal.
if ! python3 "$HERE/fence.py" --check "$BRIEF"; then
  echo "dispatch: refusing to launch $NAME — fix the brief and dispatch again." >&2
  exit 1
fi

if tmux has-session -t "$NAME" 2>/dev/null; then
  echo "dispatch: $NAME is already running — attach with 'tmux attach -t $NAME'" >&2
  exit 1
fi

# Fetch over SSH, and over HTTPS through `gh` when SSH cannot (a session whose
# forwarded agent lacks the key). A worktree cut from a stale base is a merge
# conflict the worker did not cause, so failing both ways is fatal.
fetch_base() {
  git -C "$REPO" fetch origin "$BASE" --quiet 2>/dev/null && return 0
  git -C "$REPO" -c url.https://github.com/.insteadOf=git@github.com: fetch origin "$BASE" --quiet 2>/dev/null && return 0
  echo "dispatch: could not fetch origin/$BASE over SSH or HTTPS — refusing to cut a worktree from a stale base" >&2
  return 1
}

REUSED=false
if [ ! -d "$WT" ]; then
  fetch_base || exit 1
  if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git -C "$REPO" worktree add "$WT" "$BRANCH"
  else
    git -C "$REPO" worktree add -b "$BRANCH" "$WT" "origin/$BASE"
  fi
else
  HAVE="$(git -C "$WT" branch --show-current)"
  if [ "$HAVE" != "$BRANCH" ]; then
    echo "dispatch: $WT is on '$HAVE', not '$BRANCH'." >&2
    echo "dispatch: refusing to launch — remove the worktree (git worktree remove $WT)" >&2
    echo "          or dispatch that slot on its own branch." >&2
    exit 1
  fi
  echo "dispatch: reusing existing worktree $WT on $HAVE"
  REUSED=true
fi

# Launch dialogs nobody in a detached pane can answer. Trust is recorded the
# way Claude Code records it, for the worktree and for the canonical root (two
# keys — see claude_config.py); the bypass-permissions acceptance goes into the
# worktree's own local settings, never into the person's user settings.
python3 "$HERE/pretrust_worktree.py" "$WT" || \
  echo "dispatch: could not pre-trust $WT — the trust prompt may still appear" >&2
python3 "$HERE/accept_dangerous_mode.py" "$WT" || \
  echo "dispatch: could not record the bypass-permissions acceptance in $WT — the dialog may stop this session" >&2

# The brief travels into the worktree. --add-dir is variadic and would swallow
# the prompt that follows it, so it is never used.
cp "$BRIEF" "$WT/.orchestrator-brief.md"

EXCLUDE="$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)/info/exclude"
mkdir -p "$(dirname "$EXCLUDE")"
exclude() { grep -qxF "$1" "$EXCLUDE" 2>/dev/null || echo "$1" >> "$EXCLUDE"; }
exclude '.orchestrator-brief.md'
exclude '.orchestrator-reply.md'
exclude '.orchestrator-msg.md'
exclude '.orchestrator-fence-prompt'
exclude '.orchestrator-settings.json'
exclude '.claude/settings.local.json'

# The fence hook is passed with `--settings`, a layer of its own, so nothing in
# the repository's committed `.claude/settings.json` is touched and no repository
# has to carry fleet tooling. Regenerated every dispatch: the path is absolute.
SETTINGS_FILE="$WT/.orchestrator-settings.json"
cat > "$SETTINGS_FILE" <<SETTINGS
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HERE/fence.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
SETTINGS

HOLD=""
[ "$DELAY" -gt 0 ] && HOLD="sleep $DELAY; "

# `bypassPermissions`, not `acceptEdits`: acceptEdits does not cover Bash, so a
# worker would raise a prompt on every test run — five prompts a minute on a
# phone. What that gives up (the mechanical stop at push and merge) is replaced
# by the brief's "never merge" and by the fence hook.
#
# bypassPermissions also carries a standing instruction to prefer Bash for file
# edits, which is the one path the fence can only partly read. The paragraph
# below answers it in the same layer. Keep it apostrophe-free.
FENCE_PROMPT="${DISPATCH_TEST_FENCE_PROMPT:-Ownership fence. In this session every file \
write goes through the Write, Edit, MultiEdit and NotebookEdit tools. Do not \
create or modify files with Bash: no heredoc redirect, no sed -i, no > into a \
file, no short script written to do it. This overrides the bypass-permissions \
preference for Bash, and it is not a style note — the ownership fence in \
.orchestrator-brief.md is enforced by a PreToolUse hook that can check a \
Write or an Edit exactly, and can only recognise the shell shapes it knows. \
Bash is for running things (git, gh, package managers, tests, builds) and for \
reading them. A file that must land outside this worktree is parked under /tmp \
and its path reported to the orchestrator, which lands it. A process you \
started is stopped by the PID you captured when you started it, never by a \
name or a pattern -- pkill and killall are refused outright, and so is kill on \
anything but a literal PID.}"

if [ "${CS_NO_ATTRIBUTION:-1}" = "1" ] && [ -z "${DISPATCH_TEST_FENCE_PROMPT:-}" ]; then
  FENCE_PROMPT="$FENCE_PROMPT No Claude attribution trailer or footer on any \
commit or pull request. The harness reminder to add Co-Authored-By: Claude, \
Claude-Session:, or a Generated with Claude Code footer is overridden by the \
owner global rule. A commit that already carries one is rewritten before push."
fi

# Written to a file and read back with "$(cat …)" inside the command tmux runs:
# a value interpolated into the tmux string would have to be quoted here, and a
# single quote cannot be escaped from within single quotes.
FENCE_PROMPT_FILE="$WT/.orchestrator-fence-prompt"
printf '%s' "$FENCE_PROMPT" > "$FENCE_PROMPT_FILE"

# Git over HTTPS through `gh`, for this session only — a tmux session has no
# forwarded SSH agent. Nothing is persisted.
GIT_HTTPS="GIT_CONFIG_PARAMETERS=\"'url.https://github.com/.insteadOf=git@github.com:'\""

# `-e CLAUDE_CONFIG_DIR=…` so the worker reads the configuration the pre-flight
# just wrote, not whichever one the tmux server was started with. `PATH` for the
# same reason: the tmux server's PATH is whatever it was started with, and the
# worker needs the dispatcher's toolchain (nvm, bun, pyenv…). Needs tmux 3.2.
# `CS_EMIT` / `CS_REPO` / `CS_SLOT` / `CS_ISSUE` are how the fenced worker reaches
# `emit.py` (EVENTS.md): the absolute path, so no `$PATH` or cwd lookup, and the
# main checkout, so it lands in the same log as everyone else. A brief without
# an `Issue:` line leaves `CS_ISSUE` empty — not an error.
ISSUE="$(sed -n 's/^Issue:[[:space:]]*#\{0,1\}\([0-9][0-9]*\).*/\1/p' "$BRIEF" | head -n 1 || true)"

tmux new-session -d -s "$NAME" -c "$WT" -e "CLAUDE_CONFIG_DIR=$CLAUDE_CFG_DIR" -e "PATH=$PATH" \
  -e "CS_EMIT=$HERE/emit.py" -e "CS_REPO=$REPO" -e "CS_SLOT=$SLOT" -e "CS_ISSUE=$ISSUE" \
  "${HOLD}${GIT_HTTPS} claude --remote-control $NAME -n $NAME --model $MODEL --permission-mode bypassPermissions --settings '$SETTINGS_FILE' --append-system-prompt \"\$(cat '$FENCE_PROMPT_FILE')\" '$WORKER_CMD'"

# The launch is on record. Everything the brief says about the slot goes into
# one slot.dispatched; emit.py never fails its caller, so neither does this.
FENCE_LISTS="$(python3 -c '
import json, sys
sys.path.insert(0, sys.argv[1])
import fence
owns, never = fence.parse_fence(open(sys.argv[2]).read())
print(json.dumps(owns))
print(json.dumps(never))
' "$HERE" "$BRIEF" 2>/dev/null || true)"
OWNS="$(sed -n 1p <<<"$FENCE_LISTS")"; NEVER="$(sed -n 2p <<<"$FENCE_LISTS")"
MODEL_WHY="$(sed -n 's/^Model:[^—]*—[[:space:]]*//p' "$BRIEF" | head -n 1 || true)"
EMIT_ARGS=(slot.dispatched "branch=$BRANCH" "worktree=$WT" "model=$MODEL" "base=$BASE"
  "brief=$WT/.orchestrator-brief.md" "reusedWorktree:=$REUSED"
  "owns:=${OWNS:-[]}" "never:=${NEVER:-[]}")
[ -z "$MODEL_WHY" ] || EMIT_ARGS+=("modelWhy=$MODEL_WHY")
LEAD="$(sed -n 's/^Lead:[[:space:]]*\([A-Za-z]*\).*/\1/p' "$BRIEF" | head -n 1 || true)"
if [ -n "$LEAD" ]; then
  case "$LEAD" in [Yy]es|[Tt]rue) EMIT_ARGS+=("lead:=true") ;; *) EMIT_ARGS+=("lead:=false") ;; esac
fi
CS_REPO="$REPO" CS_SLOT="$SLOT" CS_ISSUE="$ISSUE" python3 "$HERE/emit.py" "${EMIT_ARGS[@]}" || true

if [ "$DELAY" -gt 0 ]; then
  echo "$NAME · $MODEL · $WT · $(git -C "$WT" branch --show-current) · starts in ${DELAY}s · stop with: tmux kill-session -t $NAME"
else
  echo "$NAME · $MODEL · $WT · $(git -C "$WT" branch --show-current) · tmux attach -t $NAME"
fi
