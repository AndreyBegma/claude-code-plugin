#!/usr/bin/env python3
"""The one writer of the orchestrator's machine-readable fleet state.

    python3 emit.py <type> [key=value …] [key:=<json> …] [--slot S] [--issue N] [--strict]
    python3 emit.py --rebuild-state [--strict]

The orchestrator's state is otherwise prose: round boards, briefs, reply-file
headings, `watch.sh` lines that vanish with the Monitor. This appends one JSON
event per call to `events.jsonl` and folds it into `state.json`, both under
`<git-common-dir>/cs-orchestrator/`. `EVENTS.md` beside the orchestrator skill
is the contract; this file is the only implementation of it.

Where it writes, and why there is no way to change that
-------------------------------------------------------

The directory is resolved from `git rev-parse --git-common-dir`, run in
`$CS_REPO` when it is set and in the current directory otherwise. The common
dir is shared by the main checkout and every `.wt-*` worktree, so every writer
— dispatcher, watch, orchestrator, fenced worker — lands in the same place.
There is deliberately no output-path argument: a worker is allowed to run this
past its ownership fence because the target is fixed here and append-only, and
an argument that could move it would make the exception a hole. Any argument
that is not a known flag or a `key=value` pair is refused.

It never fails its caller
-------------------------

A broken log must not stop a fleet. Every error — not a repository, the lock
not taken within 5 s, a full disk, an unknown type, a missing key — prints one
line prefixed `emit:` to stderr and exits 0. `--strict` exits 1 instead; only
tests use it.

Concurrency
-----------

Every write takes an exclusive `flock` on `.events.lock`. Under it: rotate the
log when it is past the threshold, append the event as one `write()` on an
`O_APPEND` descriptor, and rewrite `state.json` through a temp file and
`os.replace`. `O_APPEND` alone is atomic only in practice and only for small
writes on local filesystems; the lock is what makes it a guarantee, and it is
what keeps the snapshot consistent with the log.

`state.json` is derived
-----------------------

No caller writes it. `fold()` is a pure reducer over events; every emitted
event is folded in under the same lock that appended it, and `--rebuild-state`
replays the kept logs to regenerate it. Time inside the reducer is the event's
own `ts`, never the wall clock, so a replay reproduces the snapshot exactly.
"""
import copy
import datetime
import errno
import fcntl
import json
import os
import re
import subprocess
import sys
import time
import uuid

SCHEMA_VERSION = 1
SOURCE = "code-sentinel"
DIR_NAME = "cs-orchestrator"
EVENTS = "events.jsonl"
STATE = "state.json"
LOCK = ".events.lock"

MAX_EVENT_BYTES = 64 * 1024          # one line, newline included (D5)
MAX_TEXT_BYTES = 2 * 1024            # `summary` / `text` (catalogue)
ROTATE_BYTES = 50 * 1024 * 1024      # D6; `CS_EMIT_ROTATE_BYTES` overrides it
KEEP_ROTATED = 10
LOCK_TIMEOUT = 5.0                   # D7; `CS_EMIT_LOCK_TIMEOUT` overrides it
SLOT_RETENTION = datetime.timedelta(days=7)

ROTATED_RE = re.compile(r"^events\.(\d{8}T\d{6}Z)(?:-(\d+))?\.jsonl$")
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TRUNC_RE = re.compile(r"…\[truncated (\d+) bytes\]$")

CHECKPOINTS = ("picked_up", "plan_ready", "implementation_done", "pr_open",
               "blocked", "misclassified")
ROUND_STATES = ("READY", "IN_FLIGHT", "BLOCKED_WORK", "BLOCKED_PERSON", "NO_SPEC")

# The closed list of event types (D9) and the `data` keys each one requires.
# Extra keys are kept. A type not here is refused, so a typo cannot become a
# new kind of event. `slot.*` types also require a slot in the envelope: the
# reducer has nothing to attach them to otherwise.
TYPES = {
    "orchestrator.started": ("session", "config"),
    "orchestrator.stopped": ("reason",),
    "orchestrator.heartbeat": ("slots",),
    "round.started": ("round", "occupied", "max", "free", "board"),
    "round.decided": ("rows",),
    "slot.dispatched": ("branch", "worktree", "model", "base", "brief"),
    "slot.resumed": ("reason",),
    "slot.redispatched": ("fromModel", "toModel", "reason"),
    "slot.checkpoint": ("checkpoint", "summary"),
    "slot.message_sent": ("text",),
    "slot.fence_widened": ("added",),
    "slot.stopped": ("by", "reason"),
    "pr.merged": ("pr", "method"),
    "pr.checks_changed": ("pr", "branch", "rollup"),
    "pr.closed": ("pr", "branch"),
    "issue.blocked": ("kind", "why"),
    "person.needed": ("question", "recommendation"),
    "session.appeared": ("name",),
    "session.vanished": ("name",),
    "pane.prompt": (),
    "pane.idle": (),
    "pane.quota_hit": (),
    "commit.trailer_found": ("sha",),
}

# Fields capped below the event limit by the catalogue itself.
TEXT_CAPS = {
    "slot.checkpoint": ("summary",),
    "slot.message_sent": ("text",),
}

USAGE = """\
usage: emit.py <type> [key=value …] [key:=<json> …] [--slot S] [--issue N] [--strict]
       emit.py --rebuild-state [--strict]

Appends one event to <git-common-dir>/cs-orchestrator/events.jsonl and folds it
into state.json there. The repository is $CS_REPO if set, else the current
directory. There is no output-path argument. --slot / --issue default to
$CS_SLOT / $CS_ISSUE. Errors print `emit: …` and exit 0, or 1 with --strict.
See skills/orchestrator/EVENTS.md.
"""


class EmitError(Exception):
    pass


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def parse_args(argv):
    """(options, type, data) — or EmitError. Nothing is read from stdin (D8)."""
    opts = {"slot": os.environ.get("CS_SLOT") or None,
            "issue": os.environ.get("CS_ISSUE") or None,
            "rebuild": False}
    event_type, data = None, {}
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        idx += 1
        if arg == "--strict":
            continue
        if arg == "--rebuild-state":
            opts["rebuild"] = True
            continue
        if arg in ("--slot", "--issue"):
            if idx >= len(argv):
                raise EmitError(f"{arg} needs a value")
            opts[arg[2:]] = argv[idx] or None
            idx += 1
            continue
        if arg.startswith("--slot=") or arg.startswith("--issue="):
            name, value = arg[2:].split("=", 1)
            opts[name] = value or None
            continue
        if arg.startswith("-"):
            raise EmitError(f"unknown option {arg!r} — emit.py takes no output "
                            f"path or other options; see --help")
        if event_type is None:
            event_type = arg
            continue
        key, value = parse_pair(arg)
        data[key] = value

    if opts["rebuild"]:
        if event_type is not None or data:
            raise EmitError("--rebuild-state takes no event")
        return opts, None, None
    if event_type is None:
        raise EmitError("no event type given")
    if event_type not in TYPES:
        raise EmitError(f"unknown event type {event_type!r}")
    return opts, event_type, data


def parse_pair(arg):
    """`key=value` is a string, `key:=<json>` a JSON literal."""
    eq = arg.find("=")
    if eq <= 0:
        raise EmitError(f"unrecognised argument {arg!r}: expected key=value or "
                        f"key:=<json> (emit.py takes no output path)")
    if arg[eq - 1] == ":":
        key, raw = arg[:eq - 1], arg[eq + 1:]
        if not KEY_RE.match(key):
            raise EmitError(f"bad key in {arg!r}")
        try:
            return key, json.loads(raw)
        except ValueError as exc:
            raise EmitError(f"{key}:= is not valid JSON: {exc}") from None
    key = arg[:eq]
    if not KEY_RE.match(key):
        raise EmitError(f"bad key in {arg!r}")
    return key, arg[eq + 1:]


def parse_issue(value):
    if value is None:
        return None
    text = str(value).strip().lstrip("#")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        raise EmitError(f"issue must be a number, got {value!r}") from None


# --------------------------------------------------------------------------
# Where the files are (D1, D2)
# --------------------------------------------------------------------------

def _git(cwd, *args):
    try:
        done = subprocess.run(["git", "-C", cwd, *args], capture_output=True,
                              text=True, timeout=10, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        raise EmitError(f"git could not run: {exc}") from None
    return done.returncode, done.stdout.strip()


def locate():
    """(directory, project) for the repository at $CS_REPO or the cwd."""
    start = os.environ.get("CS_REPO") or os.getcwd()
    if not os.path.isdir(start):
        raise EmitError(f"CS_REPO is not a directory: {start}")
    code, common = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if code != 0 or not common:
        raise EmitError(f"not inside a git repository: {start}")
    common = os.path.realpath(common)
    root = os.path.dirname(common) if os.path.basename(common) == ".git" else common
    _, url = _git(start, "remote", "get-url", "origin")
    return os.path.join(common, DIR_NAME), {"repo": repo_slug(url), "root": root}


def repo_slug(url):
    """`owner/name` from any GitHub-style remote URL, or None."""
    if not url:
        return None
    path = re.sub(r"^[a-z+]+://[^/]+/", "", url.strip())   # scheme://host/
    path = re.sub(r"^[^/:@]+@[^:]+:", "", path)              # user@host:
    path = re.sub(r"\.git$", "", path.rstrip("/"))
    parts = [p for p in path.split("/") if p]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


# --------------------------------------------------------------------------
# The event
# --------------------------------------------------------------------------

def now_iso():
    stamp = datetime.datetime.now(datetime.timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{stamp.microsecond // 1000:03d}Z"


def build_event(event_type, data, opts, project, ts=None):
    missing = [k for k in TYPES[event_type] if k not in data]
    if missing:
        raise EmitError(f"{event_type} requires data key(s): {', '.join(missing)}")
    slot = opts.get("slot")
    issue = parse_issue(opts.get("issue"))
    if event_type.startswith("slot.") and not slot:
        raise EmitError(f"{event_type} requires a slot (--slot or $CS_SLOT)")

    event = {"v": SCHEMA_VERSION, "eid": str(uuid.uuid4()), "ts": ts or now_iso(),
             "type": event_type, "source": SOURCE, "project": project}
    if slot:
        event["slot"] = slot
    if issue is not None:
        event["issue"] = issue
    if slot:
        event["session"] = {"runtime": "claude", "name": f"cs-{slot}"}
    event["data"] = dict(data)

    for key in TEXT_CAPS.get(event_type, ()):
        value = event["data"].get(key)
        if isinstance(value, str) and len(value.encode()) > MAX_TEXT_BYTES:
            event["data"][key] = truncate(value, MAX_TEXT_BYTES)
            event["data"]["_truncated"] = True
    return event


def encode(event):
    return json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"


def truncate(value, limit):
    """`value` cut to at most `limit` UTF-8 bytes, suffix included.

    A value that already carries a truncation suffix is cut from what is left,
    and the suffix reports the total removed, so a second pass does not stack
    two suffixes.
    """
    removed = 0
    found = TRUNC_RE.search(value)
    if found:
        removed = int(found.group(1))
        value = value[:found.start()]
    raw = value.encode()
    keep = len(raw)
    while True:
        # Cut on a character boundary, then check the suffix still fits: the
        # count in it can gain a digit as the cut grows.
        head = raw[:keep].decode("utf-8", errors="ignore")
        result = head + f"…[truncated {removed + len(raw) - len(head.encode())} bytes]"
        over = len(result.encode()) - limit
        if over <= 0 or not head:
            return result
        keep = max(len(head.encode()) - over, 0)


def _string_leaves(node, path=()):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _string_leaves(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _string_leaves(value, path + (index,))


def _set(node, path, value):
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value


def fit(event):
    """Truncate the longest strings in `data` until the line is ≤ 64 KiB (D5)."""
    line = encode(event)
    while len(line.encode()) > MAX_EVENT_BYTES:
        excess = len(line.encode()) - MAX_EVENT_BYTES
        leaves = sorted(_string_leaves(event["data"]),
                        key=lambda leaf: len(json.dumps(leaf[1], ensure_ascii=False).encode()),
                        reverse=True)
        leaves = [leaf for leaf in leaves if len(leaf[1].encode()) > 64]
        if not leaves:
            raise EmitError(f"event is {len(line.encode())} bytes and has no string "
                            f"in data long enough to truncate")
        path, value = leaves[0]
        _set(event["data"], path, truncate(value, len(value.encode()) - excess - 32))
        event["data"]["_truncated"] = True
        line = encode(event)
    return line


# --------------------------------------------------------------------------
# State reducer (D10)
# --------------------------------------------------------------------------

def empty_state():
    return {
        "v": SCHEMA_VERSION,
        "updatedAt": None,
        "repo": None,
        "orchestrator": {"session": None, "running": False, "config": {},
                         "lastHeartbeat": None},
        "round": None,
        "slots": {},
        "personNeeded": [],
    }


def parse_ts(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def _int(value):
    try:
        return int(str(value).strip().lstrip("#"))
    except (TypeError, ValueError):
        return None


def _find_slot(state, event):
    slots = state["slots"]
    if event.get("slot") in slots:
        return event["slot"]
    data = event.get("data", {})
    number = _int(data.get("pr"))
    if number is not None:
        for name, slot in slots.items():
            if (slot.get("pr") or {}).get("number") == number:
                return name
    branch = data.get("branch")
    if branch:
        for name, slot in slots.items():
            if slot.get("branch") == branch:
                return name
    return None


def _slot(state, event):
    name = event["slot"]
    slot = state["slots"].get(name)
    if slot is None:
        slot = state["slots"][name] = {
            "issue": event.get("issue"), "branch": None, "worktree": None,
            "model": None, "modelWhy": None, "status": "running",
            "lastCheckpoint": None, "pr": None, "dispatchedAt": None, "endedAt": None,
        }
    return slot


def _end(state, name, status, ts):
    slot = state["slots"][name]
    slot["status"] = status
    slot["endedAt"] = ts
    state["personNeeded"] = [p for p in state["personNeeded"] if p.get("slot") != name]


def apply(state, event):
    """Fold one event into `state` in place. `fold` is the pure form."""
    etype, data, ts = event.get("type"), event.get("data") or {}, event.get("ts")
    state["updatedAt"] = ts
    repo = (event.get("project") or {}).get("repo")
    if repo:
        state["repo"] = repo
    orch = state["orchestrator"]

    if etype == "orchestrator.started":
        orch.update(session=data.get("session"), running=True,
                    config=data.get("config") or {})
    elif etype == "orchestrator.stopped":
        orch["running"] = False
        state["personNeeded"] = [p for p in state["personNeeded"]
                                 if p.get("slot") or p.get("issue") is not None]
    elif etype == "orchestrator.heartbeat":
        orch["lastHeartbeat"] = ts
    elif etype == "round.started":
        state["round"] = {"label": data.get("round"), "occupied": data.get("occupied"),
                          "max": data.get("max"), "free": data.get("free"),
                          "board": data.get("board"), "decided": []}
    elif etype == "round.decided":
        if state["round"] is None:
            state["round"] = {"label": None, "occupied": None, "max": None,
                              "free": None, "board": None, "decided": []}
        rows = data.get("rows") or []
        state["round"]["decided"] = rows
        cleared = {_int(r.get("issue")) for r in rows
                   if isinstance(r, dict) and r.get("state") != "BLOCKED_PERSON"}
        cleared.discard(None)
        state["personNeeded"] = [p for p in state["personNeeded"]
                                 if p.get("issue") not in cleared]
    elif etype == "slot.dispatched":
        slot = _slot(state, event)
        slot.update(branch=data.get("branch"), worktree=data.get("worktree"),
                    model=data.get("model"), modelWhy=data.get("modelWhy"),
                    status="running", dispatchedAt=ts, endedAt=None)
        if event.get("issue") is not None:
            slot["issue"] = event["issue"]
    elif etype == "slot.checkpoint":
        slot = _slot(state, event)
        checkpoint = data.get("checkpoint")
        slot["lastCheckpoint"] = {"checkpoint": checkpoint, "ts": ts,
                                  "summary": data.get("summary")}
        if slot.get("endedAt") is None:
            if checkpoint in ("blocked", "misclassified"):
                slot["status"] = "blocked"
            elif checkpoint == "pr_open":
                slot["status"] = "pr_open"
            else:
                slot["status"] = "running"
        number = _int(data.get("pr"))
        if number is not None:
            pr = slot["pr"] = dict(slot.get("pr") or {}, number=number)
            pr.setdefault("rollup", None)
            if data.get("url"):
                pr["url"] = data["url"]
    elif etype == "slot.resumed":
        slot = _slot(state, event)
        slot.update(status="running", endedAt=None)
    elif etype == "slot.redispatched":
        slot = _slot(state, event)
        slot.update(model=data.get("toModel"), status="running", endedAt=None)
    elif etype == "slot.stopped":
        _slot(state, event)
        _end(state, event["slot"], "stopped", ts)
    elif etype in ("pr.merged", "pr.checks_changed", "pr.closed"):
        name = _find_slot(state, event)
        if name is not None:
            slot = state["slots"][name]
            pr = slot["pr"] = dict(slot.get("pr") or {})
            number = _int(data.get("pr"))
            if number is not None:
                pr["number"] = number
            pr.setdefault("rollup", None)
            if etype == "pr.checks_changed":
                pr["rollup"] = data.get("rollup")
            elif etype == "pr.closed":
                pr["closed"] = True
            else:
                _end(state, name, "merged", ts)
    elif etype == "issue.blocked":
        if event.get("slot") in state["slots"]:
            state["slots"][event["slot"]]["status"] = "blocked"
    elif etype == "person.needed":
        state["personNeeded"].append({
            "issue": event.get("issue"), "slot": event.get("slot"),
            "question": data.get("question"),
            "recommendation": data.get("recommendation"), "ts": ts,
        })

    # Ended slots stay visible for 7 days after `endedAt`, measured on the
    # event clock so that a replay drops exactly what the live fold dropped.
    now = parse_ts(ts)
    if now is not None:
        for name in list(state["slots"]):
            ended = parse_ts(state["slots"][name].get("endedAt"))
            if ended is not None and now - ended > SLOT_RETENTION:
                del state["slots"][name]
    return state


def fold(state, event):
    """The pure reducer: a new state, `state` untouched."""
    return apply(copy.deepcopy(state), event)


# --------------------------------------------------------------------------
# Files (D4, D6)
# --------------------------------------------------------------------------

class Lock:
    def __init__(self, directory):
        self.path = os.path.join(directory, LOCK)
        self.fd = None

    def __enter__(self):
        timeout = float(os.environ.get("CS_EMIT_LOCK_TIMEOUT") or LOCK_TIMEOUT)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EACCES):
                    raise
            if time.monotonic() >= deadline:
                os.close(self.fd)
                self.fd = None
                raise EmitError(f"lock not taken within {timeout:g} s: {self.path}")
            time.sleep(0.01)

    def __exit__(self, *exc):
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)


def rotated_logs(directory):
    """Rotated logs, oldest first."""
    found = []
    for name in os.listdir(directory):
        match = ROTATED_RE.match(name)
        if match:
            found.append(((match.group(1), int(match.group(2) or 0)), name))
    return [os.path.join(directory, name) for _, name in sorted(found)]


def rotate_if_needed(directory):
    current = os.path.join(directory, EVENTS)
    limit = int(os.environ.get("CS_EMIT_ROTATE_BYTES") or ROTATE_BYTES)
    try:
        if os.path.getsize(current) <= limit:
            return
    except FileNotFoundError:
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Several rotations in one second take a counter suffix. It continues past
    # the highest one already used — never refilling a name that pruning freed,
    # which would sort the newest file as the oldest.
    used = [int(m.group(2) or 0) for m in map(ROTATED_RE.match, os.listdir(directory))
            if m and m.group(1) == stamp]
    name = f"events.{stamp}-{max(used) + 1}.jsonl" if used else f"events.{stamp}.jsonl"
    os.rename(current, os.path.join(directory, name))
    for old in rotated_logs(directory)[:-KEEP_ROTATED]:
        os.remove(old)


def append(directory, line):
    fd = os.open(os.path.join(directory, EVENTS),
                 os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        data = line.encode()
        written = os.write(fd, data)
        if written != len(data):
            raise EmitError(f"short write: {written} of {len(data)} bytes")
    finally:
        os.close(fd)


def replay(directory):
    state = empty_state()
    for path in rotated_logs(directory) + [os.path.join(directory, EVENTS)]:
        try:
            handle = open(path, encoding="utf-8")
        except FileNotFoundError:
            continue
        with handle:
            for raw in handle:
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("v") == SCHEMA_VERSION:
                    apply(state, event)
    return state


def load_state(directory):
    try:
        with open(os.path.join(directory, STATE), encoding="utf-8") as handle:
            state = json.load(handle)
        if isinstance(state, dict) and state.get("v") == SCHEMA_VERSION:
            return state
    except (OSError, ValueError):
        pass
    return replay(directory)


def write_state(directory, state):
    path = os.path.join(directory, STATE)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def emit(event_type, data, slot=None, issue=None):
    """Append one event and fold it into the snapshot. Raises EmitError."""
    if event_type not in TYPES:
        raise EmitError(f"unknown event type {event_type!r}")
    directory, project = locate()
    event = build_event(event_type, data, {"slot": slot, "issue": issue}, project)
    line = fit(event)
    os.makedirs(directory, exist_ok=True)
    with Lock(directory):
        rotate_if_needed(directory)
        state = load_state(directory)   # before the append: a rebuild must not see it twice
        append(directory, line)
        write_state(directory, apply(state, event))
    return event


def rebuild_state():
    directory, _ = locate()
    if not os.path.isdir(directory):
        raise EmitError(f"no event log yet: {directory}")
    with Lock(directory):
        state = replay(directory)
        write_state(directory, state)
    return state


def main(argv):
    strict = "--strict" in argv
    if "-h" in argv or "--help" in argv:
        sys.stdout.write(USAGE)
        return 0
    try:
        opts, event_type, data = parse_args(argv)
        if opts["rebuild"]:
            rebuild_state()
        else:
            emit(event_type, data, slot=opts["slot"], issue=opts["issue"])
    except EmitError as exc:
        print(f"emit: {exc}", file=sys.stderr)
        return 1 if strict else 0
    except Exception as exc:  # noqa: BLE001 — D7: a broken log never stops a fleet
        print(f"emit: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1 if strict else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
