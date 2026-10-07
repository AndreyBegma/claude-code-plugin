#!/usr/bin/env python3
"""Tests for `emit.py`, the writer of `events.jsonl` and `state.json`.

Run it directly:

    python3 skills/orchestrator/scripts/emit_test.py

Every case builds a throwaway `git init` repository in a temp directory and
points `emit.py` at it through `CS_REPO` (or the cwd), so nothing here touches
the repository it lives in. `CS_*` and `GIT_*` variables inherited from the
session running the tests are dropped first — a worker session carries real
ones, and they must not leak into the cases.
"""
import datetime
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
EMIT = os.path.join(HERE, "emit.py")
sys.path.insert(0, HERE)
import emit  # noqa: E402

for _name in list(os.environ):
    if _name.startswith(("CS_", "GIT_")):
        del os.environ[_name]

TS_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------

class Repo:
    """A throwaway repository with an `origin`, and its event directory."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="emit-test-")
        self.root = os.path.realpath(os.path.join(self.tmp, "repo"))
        os.makedirs(self.root)
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "git@github.com:acme/widgets.git")
        self.dir = os.path.join(self.root, ".git", "cs-orchestrator")
        self.events = os.path.join(self.dir, "events.jsonl")
        self.state = os.path.join(self.dir, "state.json")

    def run(self, *args, env=None, cwd=None, repo=True):
        full = dict(os.environ)
        if repo:
            full["CS_REPO"] = self.root
        full.update(env or {})
        return subprocess.run([sys.executable, EMIT, *args], capture_output=True,
                              text=True, timeout=60, cwd=cwd or self.tmp,
                              env=full, stdin=subprocess.DEVNULL)

    def lines(self, path=None):
        with open(path or self.events, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def load_state(self):
        with open(self.state, encoding="utf-8") as handle:
            return json.load(handle)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def expect_ok(done):
    assert done.returncode == 0 and not done.stderr, \
        f"expected a clean run, got {done.returncode}: {done.stderr.strip()}"


def expect_refused(repo, args, fragment, env=None):
    """Exit 0 with `emit:` on stderr, exit 1 with --strict, and nothing written."""
    soft = repo.run(*args, env=env)
    assert soft.returncode == 0, f"non-strict exit {soft.returncode}"
    assert soft.stderr.startswith("emit: "), f"stderr was {soft.stderr!r}"
    assert fragment in soft.stderr, f"{fragment!r} not in {soft.stderr!r}"
    assert len(soft.stderr.strip().splitlines()) == 1, "more than one stderr line"
    strict = repo.run(*args, "--strict", env=env)
    assert strict.returncode == 1, f"--strict exit {strict.returncode}"
    assert not os.path.exists(repo.events), "an event was written"


DISPATCH = ["slot.dispatched", "--slot", "i42-api", "--issue", "42",
            "branch=feat/42-api", "worktree=/w/.wt-i42", "model=opus", "base=develop",
            "brief=/w/.wt-i42/.orchestrator-brief.md", "modelWhy=new module",
            'owns:=["src/api/**"]', 'never:=["prisma/**"]', "lead:=true",
            "reusedWorktree:=false"]


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------

def test_envelope(repo):
    expect_ok(repo.run(*DISPATCH))
    [event] = repo.lines()
    assert list(event) == ["v", "eid", "ts", "type", "source", "project", "slot",
                           "issue", "session", "data"], list(event)
    assert event["v"] == 1
    assert uuid.UUID(event["eid"]).version == 4
    assert TS_RE.match(event["ts"]), event["ts"]
    assert event["type"] == "slot.dispatched"
    assert event["source"] == "code-sentinel"
    assert event["project"] == {"repo": "acme/widgets", "root": repo.root}, event["project"]
    assert event["slot"] == "i42-api" and event["issue"] == 42
    assert event["session"] == {"runtime": "claude", "name": "cs-i42-api"}
    assert event["data"]["model"] == "opus" and event["data"]["owns"] == ["src/api/**"]


def test_envelope_from_environment(repo):
    expect_ok(repo.run("slot.checkpoint", "checkpoint=picked_up", "summary=s",
                       env={"CS_SLOT": "i7-x", "CS_ISSUE": "7"}))
    expect_ok(repo.run("pane.idle", "via=watch", env={"CS_SLOT": "", "CS_ISSUE": ""}))
    first, second = repo.lines()
    assert first["slot"] == "i7-x" and first["issue"] == 7
    assert "slot" not in second and "issue" not in second and "session" not in second, \
        "an empty CS_SLOT / CS_ISSUE must be omitted, not an error"


def test_flags_override_environment(repo):
    expect_ok(repo.run("slot.checkpoint", "checkpoint=blocked", "summary=s",
                       "--slot=i9-y", "--issue=#9", env={"CS_SLOT": "zz", "CS_ISSUE": "1"}))
    [event] = repo.lines()
    assert event["slot"] == "i9-y" and event["issue"] == 9


def test_worktree_writes_to_common_dir(repo):
    git(repo.root, "commit", "-q", "--allow-empty", "-m", "init")
    worktree = os.path.join(repo.tmp, ".wt-i1")
    git(repo.root, "worktree", "add", "-q", "-b", "wt", worktree)
    expect_ok(repo.run("pane.prompt", "via=watch", cwd=worktree, repo=False))
    [event] = repo.lines()
    assert event["project"]["root"] == repo.root, \
        "a worktree must resolve the main checkout's common dir"
    assert not os.path.exists(os.path.join(worktree, ".git", "cs-orchestrator"))


def test_value_parsing(repo):
    expect_ok(repo.run("slot.checkpoint", "--slot", "s", "checkpoint=pr_open",
                       "summary=a=b", "pr:=51", "ok:=true", "none:=null",
                       'checks:=[{"cmd":"t","ok":true}]', 'obj:={"k":[1,2]}',
                       "num=51", "url=https://x/pull/51"))
    data = repo.lines()[0]["data"]
    assert data["summary"] == "a=b", "only the first `=` splits"
    assert data["pr"] == 51 and data["ok"] is True and data["none"] is None
    assert data["checks"] == [{"cmd": "t", "ok": True}] and data["obj"] == {"k": [1, 2]}
    assert data["num"] == "51", "key=value is always a string"


def test_bad_json_refused(repo):
    expect_refused(repo, ["slot.checkpoint", "--slot", "s", "checkpoint=x",
                          "summary=y", "pr:=[1,"], "not valid JSON")


def test_unknown_type_refused(repo):
    expect_refused(repo, ["slot.chekpoint", "--slot", "s"], "unknown event type")


def test_missing_required_key_refused(repo):
    expect_refused(repo, ["slot.checkpoint", "--slot", "s", "checkpoint=plan_ready"],
                   "summary")


def test_slot_event_without_slot_refused(repo):
    expect_refused(repo, ["slot.checkpoint", "checkpoint=plan_ready", "summary=x"],
                   "requires a slot")


def test_no_output_path_argument(repo):
    elsewhere = os.path.join(repo.tmp, "elsewhere.jsonl")
    base = ["pane.idle", "via=watch"]
    for extra in (["--output", elsewhere], [f"--out={elsewhere}"], ["-o", elsewhere],
                  ["--dir", repo.tmp], [elsewhere], ["./events.jsonl"]):
        expect_refused(repo, base + extra, "no output path")
        assert not os.path.exists(elsewhere), f"{extra} created {elsewhere}"
    assert not os.path.exists(repo.dir), "a refused call created the event directory"


def test_truncation_at_64k(repo):
    blob = "é" * 50_000 + "x" * 30_000          # 130 000 bytes of UTF-8
    expect_ok(repo.run("commit.trailer_found", "sha=abc", f"body={blob}",
                       "small=keep me"))
    with open(repo.events, "rb") as handle:
        raw = handle.read()
    assert len(raw) <= 64 * 1024, f"line is {len(raw)} bytes"
    data = json.loads(raw)["data"]
    assert data["_truncated"] is True
    assert data["small"] == "keep me" and data["sha"] == "abc"
    match = re.search(r"…\[truncated (\d+) bytes\]$", data["body"])
    assert match, data["body"][-40:]
    kept = data["body"][:match.start()]
    assert blob.startswith(kept), "the kept part must be a prefix, cut on a character"
    assert len(kept.encode()) + int(match.group(1)) == len(blob.encode()), \
        "the suffix must count exactly what was removed"


def test_summary_capped_at_2k(repo):
    expect_ok(repo.run("slot.checkpoint", "--slot", "s", "checkpoint=blocked",
                       "summary=" + "ж" * 3000))
    data = repo.lines()[0]["data"]
    assert len(data["summary"].encode()) <= 2048, len(data["summary"].encode())
    assert data["summary"].endswith(" bytes]") and data["_truncated"] is True


def test_short_values_untouched(repo):
    expect_ok(repo.run("slot.message_sent", "--slot", "s", "text=hello"))
    data = repo.lines()[0]["data"]
    assert data == {"text": "hello"}, data


CONCURRENT_WORKER = """
import os, sys
sys.path.insert(0, sys.argv[1])
import emit
for n in range(100):
    emit.emit("slot.checkpoint",
              {"checkpoint": "plan_ready", "summary": "w%s-%s " % (sys.argv[2], n) + "x" * 900},
              slot="w" + sys.argv[2])
"""


def test_concurrent_appends(repo):
    script = os.path.join(repo.tmp, "worker.py")
    with open(script, "w") as handle:
        handle.write(CONCURRENT_WORKER)
    env = {**os.environ, "CS_REPO": repo.root}
    procs = [subprocess.Popen([sys.executable, script, HERE, str(n)], env=env,
                              stderr=subprocess.PIPE, text=True)
             for n in range(20)]
    for proc in procs:
        _, err = proc.communicate(timeout=300)
        assert proc.returncode == 0, err
    events = repo.lines()                 # every line parses, or this raises
    assert len(events) == 2000, len(events)
    assert len({e["eid"] for e in events}) == 2000, "duplicate eid"
    seen = {}
    for event in events:
        tag = event["data"]["summary"].split()[0]
        seen[tag] = seen.get(tag, 0) + 1
    assert len(seen) == 2000, "an event was lost or doubled"
    state = repo.load_state()
    assert len(state["slots"]) == 20, "state.json missed a writer's fold"
    assert state == emit.replay(repo.dir), "the live snapshot disagrees with the log"


def test_rotation_keeps_ten(repo):
    os.environ["CS_REPO"] = repo.root
    os.environ["CS_EMIT_ROTATE_BYTES"] = "1500"
    try:
        for n in range(60):
            emit.emit("pane.idle", {"via": "watch", "n": n, "pad": "x" * 400})
    finally:
        del os.environ["CS_REPO"], os.environ["CS_EMIT_ROTATE_BYTES"]
    rotated = sorted(n for n in os.listdir(repo.dir) if emit.ROTATED_RE.match(n))
    assert len(rotated) == 10, rotated
    assert os.path.getsize(repo.events) <= 1500 + 1024
    kept = [e["data"]["n"] for path in emit.rotated_logs(repo.dir) + [repo.events]
            for e in repo.lines(path)]
    assert kept == list(range(60 - len(kept), 60)), \
        "rotated files must replay oldest first and keep the newest events"


def ts(minutes):
    base = datetime.datetime(2026, 10, 7, 21, 0, tzinfo=datetime.timezone.utc)
    stamp = base + datetime.timedelta(minutes=minutes)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def test_reducer_sequence(repo):
    """dispatch → checkpoints → pr_open → pr.merged, end to end through the CLI."""
    steps = [
        ["orchestrator.started", "session=plugin-orchestrator",
         'config:={"base":"develop","maxSlots":5}'],
        ["round.started", "round=2107", "occupied:=1", "max:=5", "free:=4",
         "board=/r/.git/cs-orchestrator/round-2107.md"],
        ["round.decided", 'rows:=[{"issue":42,"state":"READY","why":"spec"}]'],
        DISPATCH,
        ["slot.checkpoint", "--slot", "i42-api", "--issue", "42",
         "checkpoint=picked_up", "summary=picked up"],
        ["slot.checkpoint", "--slot", "i42-api", "--issue", "42",
         "checkpoint=plan_ready", "summary=the plan"],
        ["person.needed", "--slot", "i42-api", "--issue", "42",
         "question=which tenant?", "recommendation=per-org"],
        ["round.decided", 'rows:=[{"issue":42,"state":"BLOCKED_PERSON","why":"q"}]'],
        ["slot.checkpoint", "--slot", "i42-api", "--issue", "42",
         "checkpoint=implementation_done", "summary=green"],
        ["slot.checkpoint", "--slot", "i42-api", "--issue", "42",
         "checkpoint=pr_open", "summary=opened", "pr:=51", "url=https://x/pull/51"],
        ["pr.checks_changed", "pr:=51", "branch=feat/42-api", "rollup=green", "via=watch"],
        ["orchestrator.heartbeat", 'slots:=["i42-api"]'],
    ]
    for step in steps:
        expect_ok(repo.run(*step))
    events = repo.lines()
    at = {e["type"]: e["ts"] for e in events}
    checkpoints = [e for e in events if e["type"] == "slot.checkpoint"]
    state = repo.load_state()

    assert state["personNeeded"] == [{
        "issue": 42, "slot": "i42-api", "question": "which tenant?",
        "recommendation": "per-org", "ts": at["person.needed"]}], \
        "a checkpoint or a BLOCKED_PERSON round must not clear a person-held question"
    assert state["slots"]["i42-api"]["status"] == "pr_open"

    expect_ok(repo.run("pr.merged", "pr:=51", "method=merge"))
    merged_at = repo.lines()[-1]["ts"]
    state = repo.load_state()
    assert state == {
        "v": 1,
        "updatedAt": merged_at,
        "repo": "acme/widgets",
        "orchestrator": {"session": "plugin-orchestrator", "running": True,
                         "config": {"base": "develop", "maxSlots": 5},
                         "lastHeartbeat": at["orchestrator.heartbeat"]},
        "round": {"label": "2107", "occupied": 1, "max": 5, "free": 4,
                  "board": "/r/.git/cs-orchestrator/round-2107.md",
                  "decided": [{"issue": 42, "state": "BLOCKED_PERSON", "why": "q"}]},
        "slots": {"i42-api": {
            "issue": 42, "branch": "feat/42-api", "worktree": "/w/.wt-i42",
            "model": "opus", "modelWhy": "new module", "status": "merged",
            "lastCheckpoint": {"checkpoint": "pr_open", "ts": checkpoints[-1]["ts"],
                               "summary": "opened"},
            "pr": {"number": 51, "rollup": "green", "url": "https://x/pull/51"},
            "dispatchedAt": at["slot.dispatched"], "endedAt": merged_at,
        }},
        "personNeeded": [],
    }, json.dumps(state, indent=2)

    # --rebuild-state reproduces the same snapshot from the log alone.
    os.remove(repo.state)
    expect_ok(repo.run("--rebuild-state"))
    assert repo.load_state() == state, "--rebuild-state disagrees with the live fold"

    # A corrupt snapshot heals itself on the next emit, from the log.
    with open(repo.state, "w") as handle:
        handle.write("{not json")
    expect_ok(repo.run("orchestrator.heartbeat", "slots:=[]"))
    healed = repo.load_state()
    assert healed["slots"] == state["slots"] and healed["round"] == state["round"]


def test_rebuild_spans_rotated_logs(repo):
    os.environ["CS_REPO"] = repo.root
    os.environ["CS_EMIT_ROTATE_BYTES"] = "800"
    try:
        emit.emit("slot.dispatched", {"branch": "b", "worktree": "w", "model": "m",
                                      "base": "d", "brief": "f"}, slot="s1", issue="3")
        for n in range(8):
            emit.emit("slot.checkpoint", {"checkpoint": "plan_ready",
                                          "summary": f"step {n} " + "x" * 300}, slot="s1")
    finally:
        del os.environ["CS_REPO"], os.environ["CS_EMIT_ROTATE_BYTES"]
    assert emit.rotated_logs(repo.dir), "the test needs at least one rotation"
    live = repo.load_state()
    expect_ok(repo.run("--rebuild-state"))
    rebuilt = repo.load_state()
    assert rebuilt == live and rebuilt["slots"]["s1"]["branch"] == "b"


def test_reducer_person_needed_rules(_repo):
    def ev(etype, minute, data=None, slot=None, issue=None):
        out = {"v": 1, "type": etype, "ts": ts(minute), "data": data or {}}
        if slot:
            out["slot"] = slot
        if issue is not None:
            out["issue"] = issue
        return out

    state = emit.empty_state()
    for event in (
        ev("person.needed", 1, {"question": "a"}, slot="s1", issue=1),
        ev("person.needed", 2, {"question": "b"}, issue=2),
        ev("person.needed", 3, {"question": "c"}),
        ev("person.needed", 4, {"question": "d"}, issue=4),
    ):
        state = emit.fold(state, event)
    before = json.dumps(state, sort_keys=True)
    after = emit.fold(state, ev("round.decided", 5, {"rows": [
        {"issue": 2, "state": "READY", "why": "answered"},
        {"issue": "#4", "state": "BLOCKED_PERSON", "why": "still"}]}))
    assert json.dumps(state, sort_keys=True) == before, "fold must not mutate its input"
    assert [p["question"] for p in after["personNeeded"]] == ["a", "c", "d"], \
        "a non-BLOCKED_PERSON row clears that issue's entry; BLOCKED_PERSON keeps it"
    after = emit.fold(after, ev("slot.stopped", 6, {"by": "person", "reason": "x"},
                                slot="s1"))
    assert [p["question"] for p in after["personNeeded"]] == ["c", "d"], \
        "a slot's entries go when the slot ends"
    after = emit.fold(after, ev("orchestrator.stopped", 7, {"reason": "stop all"}))
    assert [p["question"] for p in after["personNeeded"]] == ["d"], \
        "entries with neither slot nor issue go on orchestrator.stopped"
    assert after["orchestrator"]["running"] is False


def test_reducer_retention_and_blocking(_repo):
    def ev(etype, minute, slot, data=None):
        return {"v": 1, "type": etype, "ts": ts(minute), "slot": slot, "data": data or {}}

    dispatch = {"branch": "b", "worktree": "w", "model": "sonnet", "base": "d", "brief": "f"}
    state = emit.empty_state()
    state = emit.fold(state, ev("slot.dispatched", 0, "a", dispatch))
    state = emit.fold(state, ev("slot.dispatched", 0, "b", dispatch))
    state = emit.fold(state, ev("issue.blocked", 1, "b", {"kind": "work", "why": "dep"}))
    assert state["slots"]["b"]["status"] == "blocked"
    state = emit.fold(state, ev("slot.redispatched", 2, "b",
                                {"fromModel": "sonnet", "toModel": "opus", "reason": "x"}))
    assert state["slots"]["b"]["model"] == "opus"
    assert state["slots"]["b"]["status"] == "running"
    state = emit.fold(state, ev("slot.stopped", 3, "a", {"by": "orchestrator", "reason": "x"}))
    week = 7 * 24 * 60
    state = emit.fold(state, ev("orchestrator.heartbeat", 3 + week, None, {"slots": []}))
    assert "a" in state["slots"], "kept for exactly 7 days"
    state = emit.fold(state, ev("orchestrator.heartbeat", 4 + week, None, {"slots": []}))
    assert "a" not in state["slots"], "dropped once 7 days after endedAt have passed"
    assert "b" in state["slots"], "a running slot is never pruned"


def test_lock_timeout(repo):
    os.makedirs(repo.dir)
    fd = os.open(os.path.join(repo.dir, ".events.lock"), os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        expect_refused(repo, ["pane.idle", "via=watch"], "lock not taken",
                       env={"CS_EMIT_LOCK_TIMEOUT": "0.2"})
    finally:
        os.close(fd)


def test_outside_a_repository(repo):
    plain = os.path.join(repo.tmp, "plain")
    os.makedirs(plain)
    env = {"GIT_CEILING_DIRECTORIES": repo.tmp}
    for args in (["pane.idle", "via=watch"], ["--rebuild-state"]):
        done = repo.run(*args, env=env, cwd=plain, repo=False)
        assert done.returncode == 0 and done.stderr.startswith("emit: "), done
        assert "not inside a git repository" in done.stderr, done.stderr
        strict = repo.run(*args, "--strict", env=env, cwd=plain, repo=False)
        assert strict.returncode == 1
    assert os.listdir(plain) == [], "nothing may be written outside a repository"
    assert not os.path.exists(repo.dir)


def test_repo_slug(_repo):
    for url, slug in [
        ("git@github.com:acme/widgets.git", "acme/widgets"),
        ("git@github.com:AndreyBegma/claude-code-plugin", "AndreyBegma/claude-code-plugin"),
        ("https://github.com/acme/widgets.git", "acme/widgets"),
        ("https://github.com/acme/widgets/", "acme/widgets"),
        ("ssh://git@github.com/acme/widgets.git", "acme/widgets"),
        ("", None),
    ]:
        assert emit.repo_slug(url) == slug, (url, emit.repo_slug(url))


# --------------------------------------------------------------------------

CASES = [
    test_envelope,
    test_envelope_from_environment,
    test_flags_override_environment,
    test_worktree_writes_to_common_dir,
    test_value_parsing,
    test_bad_json_refused,
    test_unknown_type_refused,
    test_missing_required_key_refused,
    test_slot_event_without_slot_refused,
    test_no_output_path_argument,
    test_truncation_at_64k,
    test_summary_capped_at_2k,
    test_short_values_untouched,
    test_concurrent_appends,
    test_rotation_keeps_ten,
    test_reducer_sequence,
    test_rebuild_spans_rotated_logs,
    test_reducer_person_needed_rules,
    test_reducer_retention_and_blocking,
    test_lock_timeout,
    test_outside_a_repository,
    test_repo_slug,
]


def main():
    failures = []
    for case in CASES:
        label = case.__name__
        repo = Repo()
        try:
            case(repo)
            print(f"ok    {label}")
        except AssertionError as exc:
            print(f"FAIL  {label}")
            failures.append(f"{label}: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  {label}")
            failures.append(f"{label}: {type(exc).__name__}: {exc}")
        finally:
            repo.close()
    print()
    if failures:
        for failure in failures:
            print(f"  {failure}")
        print(f"\n{len(failures)} failed")
        return 1
    print(f"{len(CASES)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
