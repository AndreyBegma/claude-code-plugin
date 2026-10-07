#!/usr/bin/env bash
#
# The orchestrator's alarm clock. Run it under the `Monitor` tool, persistent.
#
#   scripts/orchestrator/watch.sh [poll-seconds] [heartbeat-seconds]
#
# Every stdout line is an event that wakes the orchestrator. It emits on exactly
# the things Phase 8 acts on, and nothing else:
#
#   PR-CHANGED <n> <branch> <checks>   a pull request appeared, or its checks moved
#   PR-GONE <n> <branch>               a pull request left the open list (merged or closed)
#   REPLY-CHANGED <slot>: <last h2>    a worker wrote to .orchestrator-reply.md
#   PROMPT <slot>                      a pane is sitting on a Claude Code launch dialog
#                                      (trust-folder, or the bypass-permissions acceptance)
#   IDLE <slot>                        a worker's prompt has sat empty for three polls
#   SESSIONS-CHANGED was[...] now[...] a cs-* session appeared or died
#   QUOTA-HIT <slot>                   the weekly-limit banner is on a worker's pane
#   TRAILER <slot> <sha>               a slot's branch head carries a Claude
#                                      attribution trailer (BUG-20260905-015)
#   HEARTBEAT <HH:MM> slots[...]       nothing happened for a while — go and look anyway
#
# Why this exists: on 2026-08-27 the peer channel (`SendMessage`,
# `notify_when_idle`) was held for approval in every direction and the person
# had to ask "what's happening?" to make the fleet move. Silence is not
# progress. This script is what makes the orchestrator exist between messages.
#
# Slots are discovered from `tmux ls` (`cs-*`); nothing is configured.
#
# The repository is $CS_REPO, else the git toplevel of the current directory.
# A slot's worktree is `<parent of repo>/.wt-<repo basename>-<slot>` —
# `dispatch.sh`'s own rule.
REPO_DIR=""
resolve_repo() {
  local top
  top="${CS_REPO:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
  [ -n "$top" ] || return 0
  dirname "$(git -C "$top" rev-parse --path-format=absolute --git-common-dir)"
}

resolve_wt() {
  local slot="$1" candidate
  candidate="$(dirname "$REPO_DIR")/.wt-$(basename "$REPO_DIR")-$slot"
  [ -d "$candidate" ] && printf '%s\n' "$candidate"
  return 0
}

set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Every stdout line above is also written to the event log (EVENTS.md), beside
# the echo and never instead of it. Synchronous: emit.py is fast, one call per
# real event, and a background job would outlive the poll that raised it.
# emit.py never fails its caller, and nothing here may reach stdout — stdout is
# the orchestrator's alarm and stays exactly as documented in the header.
emit() {
  CS_REPO="$REPO_DIR" python3 "$HERE/emit.py" "$@" </dev/null >/dev/null 2>&1 || true
}

# Several fleets can share one tmux server, so `tmux ls` lists other projects'
# `cs-*` sessions too. The stdout lines keep reporting them; the log, which is
# this repository's, does not. A slot is this repository's when its worktree
# (`<parent>/.wt-<repo>-<slot>`) exists. `own_seen` remembers slots that had
# one, so a slot whose worktree is removed in the same wake it dies still gets
# its `session.vanished`.
declare -A own_seen
is_own_slot() {
  [ -n "${own_seen[$1]:-}" ] && return 0
  [ -n "$(resolve_wt "$1")" ] && { own_seen[$1]=1; return 0; }
  return 1
}

# `["a","b"]` of this repository's slots among the names given. Slot names are
# lowercase letters, digits and '-' (dispatch.sh), so nothing needs escaping.
own_slots_json() {
  local s out=""
  for s in "$@"; do is_own_slot "$s" && out="${out:+$out,}\"$s\""; done
  printf '[%s]' "$out"
}

# The rollup of the comma-separated check states `gh pr list` prints.
rollup_of() {
  local checks="$1" c state=green
  [ -n "$checks" ] || { echo pending; return; }
  for c in ${checks//,/ }; do
    case "$c" in
      FAILURE|ERROR|CANCELLED|TIMED_OUT|STARTUP_FAILURE|ACTION_REQUIRED|STALE) echo red; return ;;
      PENDING|IN_PROGRESS|QUEUED|EXPECTED|WAITING|REQUESTED) state=pending ;;
    esac
  done
  # A check still running prints an empty conclusion: ",SUCCESS" has one.
  case ",$checks," in *,,*) state=pending ;; esac
  echo "$state"
}

slots() { tmux ls 2>/dev/null | cut -d: -f1 | grep '^cs-' | sed 's/^cs-//' | sort; }

# Pure classifier, so a fixture pane capture can drive it without a real tmux
# session (`dispatch_test.sh` for the fixture shape this follows). A pane
# sitting on one of Claude Code's launch dialogs carries no "esc to interrupt"
# either, so without checking for it first the dialog reads as three polls of
# silence and reports IDLE — nothing tells the orchestrator someone has to
# press Enter (BUG-20260902-003). Prints "<event> <idle_count> <prompt_seen>";
# event is NONE, PROMPT or IDLE. PROMPT fires once per occurrence, on the poll
# the dialog first appears, rather than waiting out the three-poll idle count
# — nobody else can dismiss it, so the sooner it is reported the better.
#
# Four dialogs, one event. The trust-folder one (BUG-20260902-003) and the
# bypass-permissions acceptance (BUG-20260903-001); `dispatch.sh` now records
# both before launching, so reaching either means the pre-flight did not take
# and a person is needed. That is the point of keeping the report here even
# after the fix: if a further dialog appears, the orchestrator should be woken
# rather than reading IDLE and waiting out a slot.
#
# Two further ones did appear, both while verifying that fix, and neither can be
# recorded away by a pre-flight — which is the argument for this classifier
# rather than against it.
#
# The third is the one that proved the point, an hour after the line above was
# written. Verifying BUG-20260903-001 with a throwaway dispatch on `fable` — the
# model this script *defaults* to — launched cleanly past both recorded dialogs
# and stopped dead on "Fable 5.1 now uses usage credits · you have $0.00 in
# credits", waiting on a two-option menu. Nothing in the pre-flight can record
# that one away; it is a billing state, not a preference, so reporting it is the
# whole remedy. Without this alternation every `fable` slot on an account out of
# credits reports IDLE for as long as anyone leaves it.
#
# The fourth turned up the same way, dispatching against a *fresh*
# `CLAUDE_CONFIG_DIR`: a variant of the trust dialog, raised because this
# repository's `.claude/settings.json` pre-approves a tool permission —
#
#   Quick safety check: Is this a project you created or one you trust?
#   ⚠ This folder pre-approves 1 tool permission in .claude/settings.json:
#     Bash(gh pr merge:*)
#   ❯ No, continue without these permissions
#     Yes, I trust this folder
#
# It is *not* caught by the trust pattern above — different wording entirely.
# `hasTrustDialogAccepted: true` for the worktree path does not suppress it:
# Claude Code reads a *second* key for this one, the repository's canonical root,
# and `pretrust_worktree.py` now writes both (BUG-20260903-002, and see
# README.md's two-key table). The pattern stays regardless — a pre-flight that
# silently fails is exactly the case being woken is for.
# Two patterns because they fail differently: `Quick safety check` is the
# opening line, and `pre-approves` is the ⚠ line, which is the part least likely
# to be reworded and also covers Claude Code's "This directory pre-approves"
# phrasing.
#
# The patterns are the dialogs' own wording, and they are deliberately loose
# enough to survive a pane wrap — which means a worker whose pane happens to be
# *displaying* this text (the bug report that produced this line, for one) is
# reported as PROMPT. That trade is on purpose: a false PROMPT costs the
# orchestrator one look at a pane, and a missed one costs a slot that sits on a
# dialog reporting IDLE until somebody wonders why it never finished.
DIALOG_PATTERNS='Do you trust the files in this folder|Quick safety check|pre-approves|Bypass Permissions mode, Claude Code will not ask|WARNING: Claude Code running in Bypass Permissions mode|now uses usage credits|Manage usage credits on claude\.ai'

classify_pane() {
  local pane="$1" idle_count="$2" prompt_seen="$3" event=NONE
  if grep -qE "$DIALOG_PATTERNS" <<<"$pane"; then
    [ "$prompt_seen" = "1" ] || event=PROMPT
    prompt_seen=1
    idle_count=0
  elif grep -q "esc to interrupt" <<<"$pane"; then
    idle_count=0
    prompt_seen=0
  else
    prompt_seen=0
    idle_count=$((idle_count + 1))
    [ "$idle_count" -eq 3 ] && event=IDLE
  fi
  printf '%s %s %s\n' "$event" "$idle_count" "$prompt_seen"
}

# Pure, so `watch_test.sh` can drive it on a commit message fixture without a
# real git history — same reason `classify_pane` is separated from `main`.
# BUG-20260905-015: the harness's own attribution reminder, not the worker's.
trailer_in_message() {
  grep -qiE '^(Co-Authored-By: Claude|Claude-Session:)' <<<"$1"
}

main() {
POLL=${1:-45}
HEARTBEAT=${2:-1200}
REPO_DIR="$(resolve_repo)"
[ -n "$REPO_DIR" ] || { echo "watch: no repository — run inside one or set CS_REPO" >&2; exit 1; }
REPO=$(cd "$REPO_DIR" && gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) || REPO=""
[ -n "$REPO" ] || { echo "watch: gh cannot resolve the GitHub repository of $REPO_DIR" >&2; exit 1; }
STATE=${TMPDIR:-/tmp}/cs-watch.$$
mkdir -p "$STATE"
trap 'rm -rf "$STATE"' EXIT

declare -A reply_mtime idle_count prompt_seen head_sha quota_seen
prev_sessions=""
last_event=$(date +%s)

while true; do
  fired=0

  # --- pull requests: appeared, checks moved, left the open list
  gh pr list --repo "$REPO" --state open --limit 30 \
    --json number,headRefName,statusCheckRollup \
    -q '.[] | "\(.number) \(.headRefName) \([.statusCheckRollup[]?|.conclusion // .state]|join(","))"' \
    > "$STATE/prs.now" 2>/dev/null || cp "$STATE/prs.prev" "$STATE/prs.now" 2>/dev/null || : > "$STATE/prs.now"
  if [ -f "$STATE/prs.prev" ]; then
    while read -r line; do
      [ -n "$line" ] && {
        echo "PR-CHANGED $line"; fired=1
        read -r pr_n pr_branch pr_checks <<<"$line"
        emit pr.checks_changed "pr:=$pr_n" "branch=$pr_branch" "rollup=$(rollup_of "$pr_checks")" "raw=$pr_checks"
      }
    done < <(comm -13 <(sort "$STATE/prs.prev") <(sort "$STATE/prs.now"))
    while read -r line; do
      [ -n "$line" ] && {
        echo "PR-GONE $line"; fired=1
        read -r pr_n pr_branch <<<"$line"
        emit pr.closed "pr:=$pr_n" "branch=$pr_branch"
      }
    done < <(comm -23 <(cut -d' ' -f1,2 "$STATE/prs.prev" | sort) <(cut -d' ' -f1,2 "$STATE/prs.now" | sort))
  fi
  cp "$STATE/prs.now" "$STATE/prs.prev"

  # --- sessions
  cur=$(slots | tr '\n' ' ')
  if [ "$cur" != "$prev_sessions" ] && [ -n "$prev_sessions$cur" ]; then
    [ -n "$prev_sessions" ] && {
      echo "SESSIONS-CHANGED was[$prev_sessions] now[$cur]"; fired=1
      for s in $prev_sessions; do
        case " $cur " in *" $s "*) ;; *) is_own_slot "$s" && emit session.vanished "name=cs-$s" via=watch --slot "$s" ;; esac
      done
      for s in $cur; do
        case " $prev_sessions " in *" $s "*) ;; *) is_own_slot "$s" && emit session.appeared "name=cs-$s" via=watch --slot "$s" ;; esac
      done
    }
  fi
  prev_sessions=$cur

  for s in $cur; do
    wt="$(resolve_wt "$s")"
    [ -n "$wt" ] && own_seen[$s]=1

    # --- reply files
    if [ -n "$wt" ]; then
      f="$wt/.orchestrator-reply.md"
      if [ -f "$f" ]; then
        m=$(stat -c %Y "$f")
        if [ -n "${reply_mtime[$s]:-}" ] && [ "$m" != "${reply_mtime[$s]}" ]; then
          echo "REPLY-CHANGED $s: $(grep -E '^##+ ' "$f" | tail -1)"; fired=1
        fi
        reply_mtime[$s]=$m
      fi

      # --- attribution trailer on the branch head: a slot that followed the
      # harness's own reminder rather than the owner's rule is caught here,
      # before the pull request is green rather than at merge.
      sha=$(git -C "$wt" rev-parse HEAD 2>/dev/null || true)
      if [ -n "$sha" ] && [ "$sha" != "${head_sha[$s]:-}" ]; then
        msg=$(git -C "$wt" log --format=%B -1 HEAD 2>/dev/null || true)
        trailer_in_message "$msg" && { echo "TRAILER $s $sha"; fired=1; emit commit.trailer_found "sha=$sha" via=watch --slot "$s"; }
        head_sha[$s]=$sha
      fi
    fi

    # --- pane: quota banner, and an idle prompt
    pane=$(tmux capture-pane -p -t "cs-$s" 2>/dev/null || true)
    if grep -q "hit your weekly limit" <<<"$pane"; then
      echo "QUOTA-HIT $s"; fired=1
      # The banner stays up for hours and stdout repeats on every poll; the log
      # records the moment it appeared.
      [ -n "${quota_seen[$s]:-}" ] || { quota_seen[$s]=1; is_own_slot "$s" && emit pane.quota_hit via=watch --slot "$s"; }
    else
      quota_seen[$s]=""
    fi
    read -r event ic ps < <(classify_pane "$pane" "${idle_count[$s]:-0}" "${prompt_seen[$s]:-0}")
    idle_count[$s]=$ic
    prompt_seen[$s]=$ps
    case "$event" in
      PROMPT) echo "PROMPT $s"; fired=1; is_own_slot "$s" && emit pane.prompt via=watch --slot "$s" ;;
      IDLE)   echo "IDLE $s"; fired=1; is_own_slot "$s" && emit pane.idle via=watch --slot "$s" ;;
    esac
  done

  # --- heartbeat
  now=$(date +%s)
  if [ "$fired" -eq 1 ]; then last_event=$now
  elif [ $((now - last_event)) -ge "$HEARTBEAT" ]; then
    echo "HEARTBEAT $(date +%H:%M) slots[$cur]"; last_event=$now
    emit orchestrator.heartbeat "slots:=$(own_slots_json $cur)"
  fi

  sleep "$POLL"
done
}

# Sourceable for tests (`classify_pane`, `trailer_in_message`), and still a plain script for
# everyone else — `main` only runs when this file is executed, not sourced.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
