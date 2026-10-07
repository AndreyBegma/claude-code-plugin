# Orchestrator events — `events.jsonl` and `state.json`

The fleet's machine-readable state. The markdown board, the briefs and the reply
files stay exactly as they are; this is a second, stable channel for anything
that wants to show or record the fleet without scraping prose (AgentDock first).

`scripts/emit.py` is the only writer. This file is its contract.

## Files

All three live in `<git-common-dir>/cs-orchestrator/`. The common dir is shared
by the main checkout and every `.wt-*` worktree, so every writer resolves the
same place. Nothing here is ever committed.

| File | What it is |
|---|---|
| `events.jsonl` | Append-only log, one JSON event per line, UTF-8 |
| `events.<UTC yyyymmddTHHMMSSZ>[-N].jsonl` | Rotated logs. `-N` appears only when several rotations land in the same second |
| `state.json` | Snapshot derived from the log. Never written by anything but `emit.py` |
| `.events.lock` | `flock` target serialising every write |

- **Location.** `emit.py` resolves the directory itself, using
  `git rev-parse --path-format=absolute --git-common-dir`. It runs that in
  `$CS_REPO` when set, and in the current directory otherwise. There is no
  output-path argument, and any argument that could be read as one is refused.
  That is why a fenced worker may call it: the target cannot be redirected.
- **Atomic append.** A writer takes an exclusive `flock` on `.events.lock`,
  then appends the whole line with one `write()` on an `O_APPEND` descriptor.
  The lock is the guarantee; `O_APPEND` alone is atomic only in practice. The
  same lock covers rotation and the `state.json` rewrite (temp file +
  `os.replace`), so the snapshot always matches the log at the moment the lock
  is released. There is no `fsync`.
- **Size.** One event is at most 64 KiB, newline included. If it would be
  longer, the longest strings in `data` are cut, on a character boundary, and
  get the suffix `…[truncated N bytes]`; `data._truncated` is set to `true`.
  N is the exact number of bytes removed. `slot.checkpoint.summary` and
  `slot.message_sent.text` are capped at 2 KiB the same way.
- **Rotation.** Before an append, under the lock, a log larger than 50 MB is
  renamed to `events.<UTC>.jsonl` and a new one is started. Only the newest 10
  rotated files are kept; older ones are deleted.
- **Order.** File order is event order. `ts` is informational: every writer is
  on one host, but sessions' clocks are not compared.

## The envelope

AgentDock event schema v1 without `seq` (consumers assign it), plus `eid`.

```json
{
  "v": 1,
  "eid": "8b1c…-uuid4",
  "ts": "2026-10-07T21:07:12.345Z",
  "type": "slot.checkpoint",
  "source": "code-sentinel",
  "project": { "repo": "owner/name", "root": "/abs/path/to/main/checkout" },
  "slot": "i42-api",
  "issue": 42,
  "session": { "runtime": "claude", "name": "cs-i42-api" },
  "data": { "checkpoint": "plan_ready", "summary": "…" }
}
```

| Field | Notes |
|---|---|
| `v` | Schema version, `1` |
| `eid` | uuid4. Use it to deduplicate on re-reads |
| `ts` | UTC, ISO-8601, milliseconds, `Z` |
| `project.repo` | `owner/name` parsed from the `origin` remote; `null` without one |
| `project.root` | The main checkout (the parent of the common dir), even when the writer ran in a worktree |
| `slot`, `issue` | Present only when known: `--slot` / `--issue`, else `$CS_SLOT` / `$CS_ISSUE`. An empty value is omitted. `issue` is an integer |
| `session` | Present whenever `slot` is: `{ runtime: "claude", name: "cs-<slot>" }` |
| `data` | Per type, below. Required keys are checked; extra keys are kept |

## Catalogue

The list is closed. An unknown type is refused, so a typo cannot become a new
kind of event. Required `data` keys are in **bold**. Every `slot.*` type also
requires `slot` in the envelope.

| Type | Emitted by | `data` |
|---|---|---|
| `orchestrator.started` | orchestrator SKILL (Phase 0, end) | **session** (ListAgents name), **config** (resolved base, maxSlots, readyLabel, specDir, checks, mergeMethod, autoMerge) |
| `orchestrator.stopped` | orchestrator SKILL (`stop all`, or the person ends it) | **reason** |
| `orchestrator.heartbeat` | watch.sh on `HEARTBEAT` | **slots** (array) |
| `round.started` | orchestrator SKILL (Phase 5, after writing the board) | **round** (`HHMM`), **occupied**, **max**, **free**, **board** (path) |
| `round.decided` | orchestrator SKILL (Phase 5) | **rows**: `[{ issue, state: READY\|IN_FLIGHT\|BLOCKED_WORK\|BLOCKED_PERSON\|NO_SPEC, why, clears? }]` |
| `slot.dispatched` | dispatch.sh, after `tmux new-session` succeeds | **branch**, **worktree**, **model**, **base**, **brief** (path), reusedWorktree, modelWhy, owns[], never[], lead |
| `slot.resumed` | orchestrator SKILL (Phase 7c, before dispatch.sh) | **reason** |
| `slot.redispatched` | orchestrator SKILL (misclassified) | **fromModel**, **toModel**, **reason** |
| `slot.checkpoint` | worker SKILL, at each checkpoint, right after appending to the reply file | **checkpoint** (`picked_up` · `plan_ready` · `implementation_done` · `pr_open` · `blocked` · `misclassified`), **summary** (≤ 2 KiB), pr?, url?, checks? (`[{cmd, ok}]`) |
| `slot.message_sent` | orchestrator SKILL (Phase 6.5) | **text** (≤ 2 KiB) |
| `slot.fence_widened` | orchestrator SKILL | **added** (globs) |
| `slot.stopped` | orchestrator SKILL (`stop <slot>`, after merge cleanup) | **by** (`person` \| `orchestrator`), **reason** |
| `pr.merged` | orchestrator SKILL (Phase 8, after `gh pr merge` succeeds) | **pr**, **method** |
| `pr.checks_changed` | watch.sh on `PR-CHANGED` | **pr**, **branch**, **rollup** (`pending` \| `green` \| `red`), raw |
| `pr.closed` | watch.sh on `PR-GONE` | **pr**, **branch** |
| `issue.blocked` | orchestrator SKILL (Phase 2 / 7) | **kind** (`work` \| `person`), **why** |
| `person.needed` | orchestrator SKILL (standing obligation 5) | **question**, **recommendation** |
| `session.appeared` / `session.vanished` | watch.sh on `SESSIONS-CHANGED` (one event per session in the diff) | **name**, via |
| `pane.prompt` / `pane.idle` / `pane.quota_hit` | watch.sh on `PROMPT` / `IDLE` / `QUOTA-HIT` | via |
| `commit.trailer_found` | watch.sh on `TRAILER` | **sha**, via |

`watch.sh` writes per-slot events (`session.*`, `pane.*`, `commit.trailer_found`)
and its heartbeat's `slots` only for this repository's slots — those whose
worktree `<parent>/.wt-<repo>-<slot>` exists — because other projects' `cs-*`
sessions share the tmux server; its stdout still reports them all.
`pane.quota_hit` is written when the banner appears, not on every poll it stays up.

Pane and session events from `watch.sh` duplicate what an external observer
(AgentDock's runner) also sees. They carry `data.via: "watch"` so a consumer can
prefer its own observation.

## Writing an event

```sh
python3 emit.py <type> [key=value …] [key:=<json> …] [--slot S] [--issue N] [--strict]
python3 emit.py --rebuild-state [--strict]
```

- `key=value` is always a string. `key:=<json>` takes a JSON literal: a
  number, boolean, `null`, array or object. Keys are identifiers. Only the
  first `=` splits, so `summary=a=b` is the string `a=b`.
- Nothing is read from stdin.
- A dispatched worker calls it through the absolute path that `dispatch.sh`
  exports into its session:
  `python3 "$CS_EMIT" slot.checkpoint checkpoint=plan_ready summary=…`.
  `CS_REPO` (main checkout), `CS_SLOT` and `CS_ISSUE` are exported beside it.
  The fence allows this call without an exception, and `fence_test.py` keeps
  it that way.
- **It never fails its caller.** Any error prints one line starting `emit:` to
  stderr and exits 0. That covers: not a repository, the lock not taken
  within 5 s, a full disk, an unknown type, a missing key. A broken log must not
  stop a fleet. `--strict` exits 1 instead; only tests use it. Outside a git
  repository nothing is written at all.

| Variable | Meaning |
|---|---|
| `CS_REPO` | Repository to resolve the directory in; default the current directory |
| `CS_SLOT`, `CS_ISSUE` | Envelope defaults for `--slot` / `--issue` |
| `CS_EMIT` | Absolute path to `emit.py`, exported into worker sessions |
| `CS_EMIT_ROTATE_BYTES` | Rotation threshold override (tests) |
| `CS_EMIT_LOCK_TIMEOUT` | Lock timeout override in seconds (tests) |

## `state.json`

```json
{
  "v": 1,
  "updatedAt": "…",
  "repo": "owner/name",
  "orchestrator": { "session": "…", "running": true, "config": { }, "lastHeartbeat": "…" },
  "round": { "label": "2107", "occupied": 2, "max": 5, "free": 3, "board": "…", "decided": [ ] },
  "slots": {
    "i42-api": {
      "issue": 42, "branch": "…", "worktree": "…", "model": "opus", "modelWhy": "…",
      "status": "running | blocked | pr_open | merged | stopped",
      "lastCheckpoint": { "checkpoint": "plan_ready", "ts": "…", "summary": "…" },
      "pr": { "number": 51, "rollup": "green", "url": "…" },
      "dispatchedAt": "…", "endedAt": null
    }
  },
  "personNeeded": [ { "issue": 42, "slot": "i42-api", "question": "…", "recommendation": "…", "ts": "…" } ]
}
```

`round` is `null` until the first `round.started`; `pr` is `null` until a PR is
known.

### It is derived

`emit.py` folds every event it writes into the snapshot with a pure reducer,
under the same lock as the append. No caller writes it, and there is no extra
step to forget. If it is missing or unreadable, the next `emit.py` call rebuilds
it from the logs before folding in its own event.
`python3 emit.py --rebuild-state` replays the rotated logs (oldest first) and
then `events.jsonl`, and regenerates it explicitly.

The reducer uses the event's `ts` as its clock, never the wall clock, so a
replay reproduces the live snapshot exactly. A replay can only see the 10
rotated files that are kept. That is accepted: 500 MB of events is far more
than the 7-day window the snapshot shows.

### Reducer rules

- Every event sets `updatedAt` to its `ts`, and `repo` from `project.repo`.
- `orchestrator.started` sets `session`, `config` and `running: true`.
  `orchestrator.stopped` sets `running: false`. `orchestrator.heartbeat` sets
  `lastHeartbeat`.
- `round.started` replaces `round` and empties `decided`. `round.decided` sets
  `round.decided` to the rows.
- `slot.dispatched` creates or refreshes the slot: branch, worktree, model,
  modelWhy and issue; `status: running`, `dispatchedAt`, `endedAt: null`. A
  resumed slot keeps its `lastCheckpoint` and `pr`.
- `slot.checkpoint` sets `lastCheckpoint`. On a slot that has not ended, it also
  sets the status:

  | Checkpoint | Status |
  |---|---|
  | `blocked`, `misclassified` | `blocked` |
  | `pr_open` | `pr_open` |
  | anything else | `running` |

  `pr` / `url` in its data set `pr.number` / `pr.url`.
- `slot.resumed` sets `running` and clears `endedAt`. `slot.redispatched` sets
  the model to `toModel` and the status to `running`.
- `slot.stopped` sets `stopped` and `endedAt`. `pr.merged` sets `merged` and
  `endedAt`.
- `issue.blocked` with a slot in the envelope marks that slot `blocked`.
- `pr.checks_changed` sets `pr.rollup`. `pr.closed` sets `pr.closed: true`.
- **Finding the slot for a `pr.*` event.** The envelope's slot if it is known;
  otherwise the slot whose `pr.number` matches `data.pr`; otherwise the slot
  whose `branch` matches `data.branch`.
- `slot.message_sent`, `slot.fence_widened`, and the session, pane and commit
  events are logged only. They do not change the snapshot.
- **`personNeeded`.** `person.needed` appends
  `{ issue, slot, question, recommendation, ts }`. An entry stays visible while
  the worker does other work: neither a checkpoint nor anything else from the
  worker clears it. An entry is dropped only when:
  - it has a slot, and that slot ends (`pr.merged` or `slot.stopped`);
  - it has an issue, and a later `round.decided` lists that issue in any state
    other than `BLOCKED_PERSON`;
  - it has neither a slot nor an issue, and an `orchestrator.stopped` arrives.
- **Retention.** Merged and stopped slots stay in `slots` for 7 days after
  `endedAt`, measured against the `ts` of the event being folded. After that
  they drop out of the snapshot; they remain in the log.

## Consuming

- **Tail by inode.** Hold `events.jsonl` open and follow it. When the name
  starts pointing at a new inode, the old file has been rotated. Drain the old
  descriptor to its end, then open the new file from the start.
- **Read whole lines only.** A line is written in one `write()` under the lock,
  but a reader without the lock can still see a partial final line. Buffer
  until the `\n`.
- **Deduplicate on `eid`** when re-reading files after a restart, or when
  reading a rotated file and the current one around a rotation.
- **Assign `seq` yourself**, in the order you read lines.
- **Read `state.json` whole.** It is replaced atomically, never rewritten in
  place. If you need it consistent with a position in the log, fold the events
  yourself with the rules above, or run `emit.py --rebuild-state`.
- **Detecting a dead orchestrator.** `orchestrator.stopped` is emitted only on
  an explicit stop. A session that dies shows up as `orchestrator.heartbeat`
  going silent.

## Compatibility

- **`v: 1` stays for additive changes**: a new event type, a new optional
  `data` key, a new field in `state.json`. Consumers must ignore what they do
  not know.
- **A breaking change bumps `v`**: removing or renaming a type or a key,
  changing a value's meaning or type, or changing the file contract above.
  `emit.py` ignores events of another version when it replays.
