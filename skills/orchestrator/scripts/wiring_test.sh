#!/usr/bin/env bash
#
# Tests for the events wiring in watch.sh and dispatch.sh. No GitHub, no real
# tmux, no real claude: all three are stubbed on PATH inside a throwaway repo.
#
#   bash skills/orchestrator/scripts/wiring_test.sh            run every test
#   bash wiring_test.sh watch-stdout <watch.sh> <dir>          print the stdout of the scripted watch run
#
# What it proves
#   watch     the stdout of a scripted run matches `wiring_test.watch.expected`
#             byte for byte (the file was captured from the watch.sh that had no
#             emit calls, so the wiring changed no output); the events written
#             beside it are the expected ones; and a `cs-*` session with no
#             worktree in this repository — another project's slot on a shared
#             tmux server — produces no event.
#   dispatch  a dispatch appends exactly one slot.dispatched carrying the
#             brief's issue, model, reason and fence globs, and the environment
#             handed to `tmux new-session` carries CS_EMIT, CS_REPO, CS_SLOT and
#             CS_ISSUE.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------- fixtures

git_quiet() { git -c user.name=t -c user.email=t@example.com -c commit.gpgsign=false "$@"; }

# stubs <dir>: gh, tmux, date and claude in <dir>/bin, driven by files in $STUB.
# A scripted value is the file with the highest suffix <= the current poll n.
make_stubs() {
  local bin="$1/bin"
  mkdir -p "$bin"
  cat > "$bin/_lib" <<'LIB'
n=$(cat "$STUB/n" 2>/dev/null || echo 0)
pick() { local k=$n; while [ "$k" -ge 1 ]; do [ -f "$STUB/$1.$k" ] && { echo "$STUB/$1.$k"; return 0; }; k=$((k-1)); done; return 0; }
LIB
  cat > "$bin/gh" <<'STUB'
#!/usr/bin/env bash
. "$(dirname "$0")/_lib"
case "$1 $2" in
  "repo view") echo o/proj ;;
  "pr list")
    n=$((n+1)); echo "$n" > "$STUB/n"
    [ -f "$STUB/hook.$n" ] && . "$STUB/hook.$n"
    [ "$n" -ge "${STOP_AT:-999}" ] && kill "$PPID"
    f="$(pick prs)"; [ -n "$f" ] && cat "$f"
    ;;
esac
exit 0
STUB
  cat > "$bin/tmux" <<'STUB'
#!/usr/bin/env bash
. "$(dirname "$0")/_lib"
case "$1" in
  ls) f="$(pick sessions)"; [ -n "$f" ] && while read -r s; do echo "$s: 1 windows (created x)"; done < "$f" ;;
  capture-pane) f="$(pick "pane.${@: -1}")"; [ -n "$f" ] && cat "$f" ;;
  has-session) exit 1 ;;
  new-session) printf '%s\n' "$@" > "$STUB/tmux-new-session.args"; env > "$STUB/tmux-env" ;;
esac
exit 0
STUB
  cat > "$bin/date" <<'STUB'
#!/usr/bin/env bash
. "$(dirname "$0")/_lib"
case "$1" in
  +%s) echo $((n*100)) ;;
  +%H:%M) echo 12:00 ;;
  *) exec "$REAL_DATE" "$@" ;;
esac
STUB
  printf '#!/usr/bin/env bash\nexit 0\n' > "$bin/claude"
  chmod +x "$bin"/gh "$bin"/tmux "$bin"/date "$bin"/claude
}

# scripted <dir> <name> <content>: write a scripted value file.
scripted() { printf '%s' "$3" > "$1/stub/$2"; }

# watch_fixture <dir>: a repository with worktrees for slots s1 and s2 (and s3,
# cut mid-run), plus the scripted gh / tmux behaviour for 14 polls.
watch_fixture() {
  local T="$1"
  mkdir -p "$T/stub" "$T/tmp"
  make_stubs "$T"
  git init -q -b main "$T/proj"
  git -C "$T/proj" remote add origin git@github.com:o/proj.git
  git_quiet -C "$T/proj" commit -q --allow-empty -m root
  git -C "$T/proj" worktree add -q "$T/.wt-proj-s1" -b b1
  git -C "$T/proj" worktree add -q "$T/.wt-proj-s2" -b b2
  git_quiet -C "$T/.wt-proj-s2" commit -q --allow-empty -m "work

Co-Authored-By: Claude <x@example.com>"
  printf '## picked up\n' > "$T/.wt-proj-s1/.orchestrator-reply.md"
  touch -d 2000-01-01 "$T/.wt-proj-s1/.orchestrator-reply.md"

  scripted "$T" prs.1 $'7 b1 SUCCESS\n'
  scripted "$T" prs.2 $'7 b1 FAILURE\n8 b2 \n'
  scripted "$T" prs.3 $'8 b2 PENDING\n'
  scripted "$T" sessions.1 $'cs-foreign\ncs-s1\ncs-s2\n'
  scripted "$T" sessions.4 $'cs-foreign\ncs-s1\ncs-s3\n'
  scripted "$T" sessions.8 $'cs-foreign\ncs-late\ncs-s1\ncs-s3\n'
  scripted "$T" sessions.14 $'cs-s1\ncs-s3\n'
  scripted "$T" pane.cs-s1.1 $'esc to interrupt\n'
  scripted "$T" pane.cs-s1.2 $'Quick safety check\n'
  scripted "$T" pane.cs-s1.3 $'esc to interrupt\n'
  scripted "$T" pane.cs-s1.5 $'waiting >\n'
  scripted "$T" pane.cs-s1.8 $'esc to interrupt\n'
  scripted "$T" pane.cs-s1.9 $'esc to interrupt\nhit your weekly limit\n'
  scripted "$T" pane.cs-s1.11 $'esc to interrupt\n'
  scripted "$T" pane.cs-s2.1 $'esc to interrupt\n'
  scripted "$T" pane.cs-s2.3 $'esc to interrupt\nhit your weekly limit\n'
  scripted "$T" pane.cs-foreign.1 $'esc to interrupt\n'
  scripted "$T" pane.cs-foreign.2 $'Quick safety check\n'
  scripted "$T" pane.cs-foreign.3 $'\n'
  scripted "$T" hook.4 "git -C '$T/proj' worktree add -q '$T/.wt-proj-s3' -b b3"
  scripted "$T" hook.5 "printf '## plan ready\n' >> '$T/.wt-proj-s1/.orchestrator-reply.md'"
}

# watch_stdout <watch.sh> <dir>: run the scripted fleet and print what watch.sh
# wrote to stdout. The sha in a TRAILER line is the only part that varies.
watch_stdout() {
  local watch="$1" T="$2"
  watch_fixture "$T"
  export STUB="$T/stub" REAL_DATE
  REAL_DATE="$(command -v date)"
  { (
    cd "$T/proj"
    PATH="$T/bin:$PATH" TMPDIR="$T/tmp" CS_REPO="$T/proj" STOP_AT=15 \
      bash "$watch" 0 300 2>/dev/null
  ) | sed -E 's/^(TRAILER [a-z0-9]+ )[0-9a-f]{40}$/\1<sha>/' || true; } 2>/dev/null
}

# --------------------------------------------------------------- the tests

fail=0
check() { # check <label> <expected> <actual>
  if [ "$2" = "$3" ]; then echo "ok    $1"; else
    echo "FAIL  $1"; diff <(printf '%s\n' "$2") <(printf '%s\n' "$3") | sed 's/^/        /'; fail=1
  fi
}

# events_of <dir>: "type slot" for every event in the repository's log.
events_of() {
  python3 -I - "$1/proj/.git/cs-orchestrator/events.jsonl" <<'PY'
import json, sys
for line in open(sys.argv[1]):
    e = json.loads(line)
    tail = e["data"].get("rollup") or e["data"].get("via")
    print(" ".join(x for x in (e["type"], e.get("slot", "-"), tail) if x))
PY
}

test_watch() {
  local T; T="$(mktemp -d)"
  local out; out="$(watch_stdout "$HERE/watch.sh" "$T")"
  check "watch.sh stdout is byte-identical to the pre-wiring capture" \
    "$(cat "$HERE/wiring_test.watch.expected")" "$out"

  local got; got="$(events_of "$T")"
  check "watch.sh events: this repository's slots only, one per occurrence" \
    "$(cat "$HERE/wiring_test.watch.events")" "$got"
  rm -rf "$T"
}

test_dispatch() {
  local T; T="$(mktemp -d)"
  mkdir -p "$T/stub" "$T/cfg"
  make_stubs "$T"
  git init -q --bare -b main "$T/origin.git"
  git clone -q "$T/origin.git" "$T/proj" 2>/dev/null
  git_quiet -C "$T/proj" commit -q --allow-empty -m root
  git -C "$T/proj" push -q origin HEAD:main
  cat > "$T/brief.md" <<'BRIEF'
# Brief — i42-api

Orchestrator: plugin-orchestrator
Issue: #42 — https://example.invalid/issues/42
Kind: feature
Branch: feat/42-api
Model: sonnet — executes a contract already written

## What this slot owns, and what it must not open

owns:
  - src/api/**
  - .orchestrator-reply.md

never:
  - src/web/**
BRIEF
  (
    cd "$T/proj"
    export STUB="$T/stub" CLAUDE_CONFIG_DIR="$T/cfg"
    PATH="$T/bin:$PATH" CS_REPO="$T/proj" \
      bash "$HERE/dispatch.sh" i42-api feat/42-api "$T/brief.md" sonnet main >/dev/null 2>&1
  )
  local log="$T/proj/.git/cs-orchestrator/events.jsonl"
  check "dispatch appends exactly one slot.dispatched" "1" \
    "$(grep -c '"type": *"slot.dispatched"' "$log")"
  local fields
  fields="$(python3 -I - "$log" <<'PY'
import json, sys
e = json.loads(open(sys.argv[1]).readline())
d = e["data"]
print(e["slot"], e["issue"], d["model"], d["modelWhy"], d["base"], d["reusedWorktree"],
      d["owns"], d["never"], "lead" in d)
PY
)"
  check "slot.dispatched carries issue, model, reason and fence globs" \
    "i42-api 42 sonnet executes a contract already written main False ['src/api/**', '.orchestrator-reply.md'] ['src/web/**'] False" \
    "$fields"
  local want
  for want in "CS_EMIT=$HERE/emit.py" "CS_REPO=$T/proj" "CS_SLOT=i42-api" "CS_ISSUE=42"; do
    check "tmux session environment has $want" "$want" \
      "$(grep -Fx -- "$want" "$T/stub/tmux-new-session.args" || true)"
  done
  rm -rf "$T"
}

case "${1:-test}" in
  watch-stdout) watch_stdout "$2" "$3" ;;
  test) test_watch; test_dispatch; exit "$fail" ;;
  *) echo "usage: wiring_test.sh [test | watch-stdout <watch.sh> <dir>]" >&2; exit 2 ;;
esac
