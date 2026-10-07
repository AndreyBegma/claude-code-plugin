#!/usr/bin/env python3
"""Tests for the worker environment `dispatch.sh` builds (telemetry, launcher).

Run it directly:

    python3 skills/orchestrator/scripts/dispatch_test.py

Every case runs `CS_DISPATCH_DRY_RUN=1 dispatch.sh` in a throwaway repository
whose `origin` is a fake URL, with `tmux` and `claude` stubbed on PATH. The
dry run prints the tmux command and exits before a worktree exists, so nothing
here launches anything. `OTEL_*`, `AGENTDOCK_*`, `CS_*` and `CLAUDE_*` variables
inherited from the session running the tests are dropped first.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DISPATCH = os.path.join(HERE, "dispatch.sh")

BRIEF = """# Brief — i1

Orchestrator: plugin-orchestrator
Issue: #7 — https://example.invalid/issues/7
Kind: feature
Model: sonnet — test

## What this slot owns, and what it must not open

owns:
  - src/**
  - .orchestrator-reply.md

never:
  - docs/**
"""

failures = 0


def check(name, ok, detail=""):
    global failures
    if ok:
        print(f"ok   {name}")
    else:
        failures += 1
        print(f"FAIL {name}\n     {detail}")


def make_fixture():
    root = tempfile.mkdtemp(prefix="dispatch_test_")
    bin_dir = os.path.join(root, "bin")
    os.makedirs(bin_dir)
    for name, body in (("tmux", "#!/bin/sh\nexit 1\n"), ("claude", "#!/bin/sh\nexit 0\n")):
        path = os.path.join(bin_dir, name)
        with open(path, "w") as f:
            f.write(body)
        os.chmod(path, 0o755)
    repo = os.path.join(root, "proj")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
    subprocess.run(git + ["init", "-q", "-b", "main", repo], check=True)
    subprocess.run(git + ["-C", repo, "commit", "-q", "--allow-empty", "-m", "root"], check=True)
    subprocess.run(["git", "-C", repo, "remote", "add", "origin", "git@github.com:acme/widgets.git"], check=True)
    brief = os.path.join(root, "brief.md")
    with open(brief, "w") as f:
        f.write(BRIEF)
    cfg = os.path.join(root, "cfg")
    os.makedirs(cfg)
    return root, repo, brief, cfg, bin_dir


def run(fx, extra=None, slot="i1", dry=True):
    root, repo, brief, cfg, bin_dir = fx
    env = {k: v for k, v in os.environ.items()
           if not re.match(r"(OTEL_|AGENTDOCK_|CS_|CLAUDE|GIT_)", k)}
    env.update(PATH=bin_dir + os.pathsep + env["PATH"], CS_REPO=repo,
               CLAUDE_CONFIG_DIR=cfg, HOME=root)
    if dry:
        env["CS_DISPATCH_DRY_RUN"] = "1"
    env.update(extra or {})
    return subprocess.run(["bash", DISPATCH, slot, "feat/1-x", brief, "sonnet", "main"],
                          env=env, capture_output=True, text=True, cwd=repo)


def main():
    fx = make_fixture()
    try:
        cfg = fx[3]

        # 1. Nothing set: no new -e flags.
        r = run(fx)
        base = r.stdout
        check("plain dry run exits 0", r.returncode == 0, r.stderr)
        e_names = re.findall(r"-e (\w+)=", base)
        check("plain dry run adds no -e flags beyond the fixed ones",
              e_names == ["CLAUDE_CONFIG_DIR", "PATH", "CS_EMIT", "CS_REPO", "CS_SLOT", "CS_ISSUE"],
              str(e_names))
        check("plain dry run says telemetry off", "telemetry off" in base, base)
        check("plain dry run launches plain claude", " claude --remote-control cs-i1 " in base, base)
        check("no worktree is created by a dry run",
              not os.path.exists(os.path.join(os.path.dirname(fx[1]), ".wt-proj-i1")))
        check("no event is emitted by a dry run",
              not os.path.exists(os.path.join(fx[1], ".git", "cs-orchestrator", "events.jsonl")))

        # 2. Endpoint switches telemetry on and tags the worker.
        r = run(fx, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:4318"})
        out = r.stdout
        for want in ("-e CLAUDE_CODE_ENABLE_TELEMETRY=1", "-e OTEL_LOGS_EXPORTER=otlp",
                     "-e OTEL_METRICS_EXPORTER=otlp", "agentdock.slot=i1",
                     "agentdock.issue=1", "agentdock.project=acme/widgets",
                     "telemetry on → 127.0.0.1:4318"):
            check(f"endpoint set: {want}", want in out, out)
        check("endpoint set: run id is slot-timestamp",
              re.search(r"agentdock\.run=i1-\d{14}", out) is not None, out)

        # 3. Inherited resource attributes survive.
        r = run(fx, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://h:1", "OTEL_RESOURCE_ATTRIBUTES": "team=x"})
        check("inherited OTEL_RESOURCE_ATTRIBUTES kept, ours appended",
              "OTEL_RESOURCE_ATTRIBUTES=team=x,agentdock.project=acme/widgets,agentdock.slot=i1" in r.stdout,
              r.stdout)

        # 4. AGENTDOCK_* overrides, with percent-encoding.
        r = run(fx, {"AGENTDOCK_RUN": "r42", "AGENTDOCK_PROJECT": "o/r"})
        check("AGENTDOCK_RUN and AGENTDOCK_PROJECT override",
              "agentdock.run=r42" in r.stdout and "agentdock.project=o/r" in r.stdout, r.stdout)
        check("AGENTDOCK_* is forwarded", "-e AGENTDOCK_RUN=r42" in r.stdout, r.stdout)
        r = run(fx, {"AGENTDOCK_RUN": "a b,c=d"})
        check("values are percent-encoded", "agentdock.run=a%20b%2Cc%3Dd" in r.stdout, r.stdout)

        # 5. Issue from the brief when the slot has no leading i<n>.
        r = run(fx, {"AGENTDOCK_RUN": "r"}, slot="auth-fix")
        check("issue falls back to the brief", "agentdock.issue=7" in r.stdout, r.stdout)

        # 6. Allowlist: unrelated secrets never leave.
        r = run(fx, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://h:1", "AWS_SECRET_ACCESS_KEY": "topsecret"})
        check("non-allowlisted variable is not forwarded",
              "AWS_SECRET_ACCESS_KEY" not in r.stdout and "topsecret" not in r.stdout, r.stdout)

        # 7. Headers forwarded to tmux but never printed.
        r = run(fx, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://h:1",
                     "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Bearer abc"})
        check("headers are redacted in the dry run",
              "abc" not in r.stdout and "OTEL_EXPORTER_OTLP_HEADERS=<redacted>" in r.stdout, r.stdout)

        # 8. Launcher override.
        fake = os.path.join(fx[0], "opt", "claude")
        os.makedirs(os.path.dirname(fake))
        shutil.copy(os.path.join(fx[4], "claude"), fake)
        r = run(fx, {"CS_CLAUDE_BIN": fake})
        check("CS_CLAUDE_BIN appears in the launch string", f" {fake} --remote-control " in r.stdout, r.stdout)
        r = run(fx, {"CS_CLAUDE_BIN": "claude rc"})
        check("CS_CLAUDE_BIN with a space is refused",
              r.returncode != 0 and "CS_CLAUDE_BIN" in r.stderr, f"{r.returncode} {r.stderr}")
        r = run(fx, {"CS_CLAUDE_BIN": "/no/such/claude"})
        check("CS_CLAUDE_BIN that is not executable is refused", r.returncode != 0, r.stderr)

        # 9. Profile inheritance.
        r = run(fx, {"CLAUDE_CONFIG_DIR": "/tmp/p"})
        check("CLAUDE_CONFIG_DIR is passed through", "-e CLAUDE_CONFIG_DIR=/tmp/p" in r.stdout, r.stdout)

        # 10. Explicit opt-out wins over the endpoint.
        r = run(fx, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://h:1", "CLAUDE_CODE_ENABLE_TELEMETRY": "0"})
        check("CLAUDE_CODE_ENABLE_TELEMETRY=0 keeps telemetry off",
              "telemetry off" in r.stdout and "OTEL_LOGS_EXPORTER=otlp" not in r.stdout, r.stdout)
        del cfg
    finally:
        shutil.rmtree(fx[0], ignore_errors=True)
    print(f"\n{failures} failure(s)" if failures else "\nall passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
