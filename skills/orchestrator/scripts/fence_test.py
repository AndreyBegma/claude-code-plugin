#!/usr/bin/env python3
"""Regression tests for the worker fence (BUG-20260828-004).

Run it directly:

    python3 scripts/orchestrator/fence_test.py

It builds a throwaway worktree with a synthetic brief, drives `fence.py` over
stdin the way the `PreToolUse` hook does, and asserts on the decision. Nothing
here touches the repository it lives in.

It is not wired into `bun run test`: `package.json` belongs to another slot in
this wave. That is the one follow-up this fix leaves behind.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FENCE = os.path.join(HERE, "fence.py")

BRIEF = """\
# Brief — testslot

Orchestrator: test
Branch: test

## What this slot owns, and what it must not open

owns:
  - scripts/orchestrator/*
  - .claude/settings.json
  - AGENTS.md
  - .orchestrator-reply.md

never:
  - apps/**
  - packages/**
  - package.json
"""

GITIGNORE = "dist/\nnode_modules/\n"

TREE_DIRS = [
    "scripts/orchestrator", "apps/atlas/src", "apps/web", "packages/db-memory",
    "docs", ".claude", "dist",
]
TREE_FILES = [
    "AGENTS.md", "package.json", "docs/current-phase.md",
    "apps/atlas/src/index.ts", "scripts/orchestrator/fence.py",
    ".claude/settings.json", "x.txt", "packages/db-[a-z]-client.ts",
]


def build_tree(root):
    for path in TREE_DIRS:
        os.makedirs(os.path.join(root, path), exist_ok=True)
    for path in TREE_FILES:
        with open(os.path.join(root, path), "w") as handle:
            handle.write("placeholder\n")
    with open(os.path.join(root, ".gitignore"), "w") as handle:
        handle.write(GITIGNORE)
    with open(os.path.join(root, ".orchestrator-brief.md"), "w") as handle:
        handle.write(BRIEF)
    subprocess.run(["git", "init", "-q", root], check=False,
                   capture_output=True)


def install_brief(root, text):
    with open(os.path.join(root, ".orchestrator-brief.md"), "w") as handle:
        handle.write(text)


def run(root, tool, tool_input, cwd=None):
    event = {
        "tool_name": tool,
        "cwd": cwd if cwd is not None else root,
        "tool_input": tool_input,
    }
    done = subprocess.run(
        [sys.executable, FENCE], input=json.dumps(event),
        capture_output=True, text=True, timeout=30,
    )
    if done.returncode != 0:
        return "error", done.stderr.strip()
    if not done.stdout.strip():
        return "allow", ""
    payload = json.loads(done.stdout)
    if "hookSpecificOutput" not in payload:
        # An allow that still had something to say about the brief.
        return "allow", payload.get("systemMessage", "")
    decision = payload["hookSpecificOutput"]["permissionDecision"]
    return decision, payload["hookSpecificOutput"]["permissionDecisionReason"]


def bash(command):
    return "Bash", {"command": command, "description": "test"}


# (label, tool, tool_input, expected decision, substring expected in the reason)
CASES = [
    # ---- read-only Bash is untouched. Demonstrated, not assumed. ----------
    ("git status", *bash("git status --short"), "allow", ""),
    ("git log piped", *bash("git log --oneline | head -20"), "allow", ""),
    ("ls a fenced dir", *bash("ls -la apps"), "allow", ""),
    ("grep in a fenced dir", *bash('grep -rn "memory" apps/atlas/src'), "allow", ""),
    ("bun test", *bash("bun run test"), "allow", ""),
    ("bun lint, stderr dropped", *bash("bun run lint 2>/dev/null"), "allow", ""),
    ("cat an owned file", *bash("cat AGENTS.md"), "allow", ""),
    ("cat a file it does not own", *bash("cat apps/atlas/src/index.ts"), "allow", ""),
    ("a quoted angle bracket is not a redirect", *bash('echo "a > b"'), "allow", ""),
    ("command substitution, read-only",
     *bash("echo $(git branch --show-current)"), "allow", ""),
    ("fd duplication", *bash("git diff --stat 2>&1 | tail -5"), "allow", ""),
    ("find", *bash("find . -name '*.ts' -print | head"), "allow", ""),
    ("sed without -i, on a file it does not own",
     *bash("sed -n '1,20p' apps/atlas/src/index.ts"), "allow", ""),
    ("test and echo", *bash("test -f package.json && echo yes"), "allow", ""),
    ("cd then read", *bash("cd apps && ls"), "allow", ""),
    ("a heredoc body is data, not commands",
     *bash("cat <<'EOF'\n> not a redirect\nsed -i 's/x/y/' apps/atlas/gone.ts\nEOF"),
     "allow", ""),
    ("git commit writes the index, not a fenced file",
     *bash('git add -A && git commit -m "wip"'), "allow", ""),

    # ---- writes inside the fence are allowed ------------------------------
    ("redirect into an owned file",
     *bash("echo hi > scripts/orchestrator/notes.txt"), "allow", ""),
    ("sed -i on an owned file",
     *bash("sed -i 's/a/b/' scripts/orchestrator/fence.py"), "allow", ""),
    ("heredoc into the reply file",
     *bash("cat > .orchestrator-reply.md <<'EOF'\nreport\nEOF"), "allow", ""),
    ("parking a file in /tmp", *bash("echo x > /tmp/fence-test-parked.md"), "allow", ""),
    ("cd /tmp then write there",
     *bash("cd /tmp && cat > fence-test-parked.md <<'EOF'\nx\nEOF"), "allow", ""),
    ("git-ignored build output is in nobody's diff",
     *bash("mkdir -p dist/out && echo x > dist/out/bundle.js"), "allow", ""),
    ("Write to an owned file",
     "Write", {"file_path": ".orchestrator-reply.md", "content": "x"}, "allow", ""),

    # ---- BUG-20260828-015: a leading `NAME=value` word is an assignment on
    # the simple command, not its name — even when the value is a command
    # substitution. A dynamic *write target* still fails closed. ------------
    ("a leading assignment with a command substitution",
     *bash("start=$(date +%s); docker logs -f c | tail -60"), "allow", ""),
    ("a leading assignment via backticks",
     *bash("start=`date +%s`; docker logs -f c | tail -60"), "allow", ""),
    ("multiple leading assignments, one of them dynamic",
     *bash("A=1 B=$(date) docker ps"), "allow", ""),
    ("an assignment-only command, nothing left to run",
     *bash("start=$(date +%s)"), "allow", ""),
    ("a dynamic write target through an assigned variable is still refused",
     *bash('f=$(mktemp); echo x > "$f"'), "deny", "cannot tell where"),
    ("a bare command substitution as the command name is still refused",
     *bash("$(cmd) > out"), "deny", "ownership fence"),

    # ---- the bug: shell writes outside the fence --------------------------
    ("heredoc into another slot's file",
     *bash("cat > apps/atlas/src/x.ts <<'EOF'\nexport const x = 1\nEOF"),
     "deny", "never list"),
    ("redirect into another slot's package",
     *bash("echo x > packages/db-memory/y.ts"), "deny", "never list"),
    ("append into another slot's file",
     *bash("printf 'x' >> docs/a.md"), "deny", "ownership fence"),
    ("sed -i outside the fence",
     *bash("sed -i 's/a/b/' docs/current-phase.md"), "deny", "ownership fence"),
    ("tee onto a never-listed file", *bash("tee -a package.json"), "deny", "never list"),
    ("rm inside another slot", *bash("rm -rf apps/web"), "deny", "never list"),
    ("mv out of the fence",
     *bash("mv scripts/orchestrator/fence.py apps/fence.py"), "deny", "never list"),
    ("cp into a never-listed directory",
     *bash("cp x.txt packages/"), "deny", "never list"),
    ("touch outside the fence", *bash("touch docs/new.md"), "deny", "ownership fence"),
    ("dd of= outside the fence",
     *bash("dd if=/dev/zero of=docs/big bs=1 count=1"), "deny", "ownership fence"),
    ("chmod outside the fence", *bash("chmod 777 packages/db-memory"), "deny", "never list"),
    ("git checkout -- <path> outside the fence",
     *bash("git checkout -- apps/atlas/src/index.ts"), "deny", "never list"),
    ("sh -c hides nothing",
     *bash("""bash -c 'echo x > docs/y.md'"""), "deny", "ownership fence"),
    ("command substitution hides nothing",
     *bash("echo $(sed -i 's/a/b/' docs/current-phase.md)"), "deny", "ownership fence"),

    # ---- it fails closed rather than guessing -----------------------------
    ("a target built at run time",
     *bash("sed -i 's/a/b/' $TARGET"), "deny", "cannot tell where"),
    ("inline interpreter code",
     *bash("""python3 -c "open('docs/x','w').write('1')" """), "deny", "cannot tell what"),
    ("an interpreter reading its program from stdin",
     *bash("python3 - <<'EOF'\nprint(1)\nEOF"), "deny", "standard input"),
    ("patch names its targets inside the diff",
     *bash("patch -p1 -i /tmp/a.patch"), "deny", "inside the diff"),

    # ---- the worktree and the corpus boundary -----------------------------
    ("writing the corpus is the orchestrator's",
     *bash("echo x > ~/dev/denitsa-documentation/fixes/z.md"),
     "deny", "outside this worktree"),
    ("cd out of the worktree, then write",
     *bash("cd .. && echo x > outside.txt"), "deny", "outside this worktree"),
    ("the brief is not the worker's",
     *bash("echo x > .orchestrator-brief.md"), "deny", "brief is the orchestrator's"),

    # ---- the file-writing tools still behave exactly as they did ----------
    ("Edit into another slot's file",
     "Edit", {"file_path": "apps/atlas/src/index.ts", "old_string": "a",
              "new_string": "b"}, "deny", "never list"),
    ("Write outside the fence",
     "Write", {"file_path": "docs/x.md", "content": "x"}, "deny", "ownership fence"),
    ("Write outside the worktree",
     "Write", {"file_path": "../elsewhere.md", "content": "x"},
     "deny", "outside this worktree"),
]


# BUG-20260902-001 — the fence covered file writes and had no notion of
# process signals: `pkill -f "nest start --watch" -u archi` matched three
# unrelated dev servers on the host and killed them, and nothing looked at it
# because `pkill` is not a write shape. `kill` on a literal PID is the only
# form left standing; everything else in this family is refused outright.
SIGNAL_CASES = [
    ("kill on a literal PID is allowed", *bash("kill -9 1234"), "allow", ""),
    ("kill on a list of literal PIDs is allowed",
     *bash("kill -9 1234 5678"), "allow", ""),
    ("kill with a signal name and a literal PID is allowed",
     *bash("kill -s KILL 1234"), "allow", ""),
    ("kill -l lists signals; there is no target to refuse",
     *bash("kill -l"), "allow", ""),

    ("pkill is refused outright",
     *bash('pkill -f "nest start --watch"'), "deny", "PID you captured"),
    ("killall is refused outright", *bash("killall node"), "deny", "PID you captured"),
    ("pkill through sudo is still refused",
     *bash('sudo pkill -f "nest start --watch"'), "deny", "PID you captured"),
    ("pkill through sh -c is still refused",
     *bash("""bash -c 'pkill -f "nest start --watch"'"""), "deny", "PID you captured"),
    ("pkill after && is still refused",
     *bash('echo hi && pkill -f "nest start --watch"'), "deny", "PID you captured"),
    ("killall behind xargs is still refused",
     *bash("echo node | xargs -I{} killall {}"), "deny", "PID you captured"),

    ("kill by job spec is not a PID",
     *bash("kill %1"), "deny", "PID you captured"),
    ("kill -- -$PGID is dynamic and refused",
     *bash("kill -- -$PGID"), "deny", "PID you captured"),
    ("kill $(pgrep ...) is refused, same as an unresolvable write target",
     *bash("kill $(pgrep -f 'nest start --watch')"), "deny", "PID you captured"),
    ("kill $PID is refused, the same rule as a dynamic write target",
     *bash("kill $PID"), "deny", "PID you captured"),

    # the exact command from the incident (BUG-20260902-001)
    ("the incident: pkill -f \"nest start --watch\" -u archi",
     *bash('pkill -f "nest start --watch" -u archi'), "deny", "PID you captured"),
]


# BUG-20260829-003 — `Bash` persists a `cd` for the rest of the session, and
# the harness hands the hook that moved `cwd` on every later tool call, not
# only `Bash`'s own. A hook that looked for the brief only at `cwd` stopped
# seeing it the moment the shell moved one level down, and allowed everything
# silently — the failure `dn-r2guards` hit as six unrefused `Edit` calls.
# `cwd` here is a subdirectory of the worktree that holds `BRIEF`, standing in
# for `apps/api-flow`; the fence must still find the brief by walking up, and
# still deny against the worktree root's fence — not the subdirectory's.
CWD_CASES = [
    ("cwd moved by a `cd`: an Edit outside the fence is still denied",
     "Edit", {"file_path": "apps/web/index.ts", "old_string": "a",
              "new_string": "b"}, "deny", "never list"),
]


# A brief written the way `dn-f2api`'s was on 2026-08-28: the owns entry carries
# an inline note for the worker, and before this fix that note was glued onto the
# path pattern, so the entry matched nothing and the file the brief granted was
# refused. The last entry is genuinely malformed — no brackets — and must be
# named rather than silently ignored.
ANNOTATED_BRIEF = """\
# Brief — testslot

owns:
  - apps/atlas/src/index.ts   [the memory export only]
  - `scripts/orchestrator/*`  [the fence]
  - packages/db-[a-z]*
  - .orchestrator-reply.md
  - docs the current phase file

never:
  - apps/web/*   [dn-staging]
"""

ANNOTATED_CASES = [
    ("an annotated owns entry grants the bare path",
     *bash("echo x > apps/atlas/src/index.ts"), "allow", ""),
    ("a backticked, annotated owns entry grants its glob",
     *bash("sed -i 's/a/b/' scripts/orchestrator/fence.py"), "allow", ""),
    # BUG-20260904-017 — `[` is a literal character now, not an `fnmatch`
    # class, so `db-[a-z]*` only grants a path that literally contains
    # `[a-z]`; the annotation regex still has to leave that bracket alone.
    ("a glob with a character class is not mistaken for a note",
     *bash("echo x > packages/db-[a-z]-client.ts"), "allow", ""),
    ("and the same glob does not cross into a sibling directory — "
     "`[a-z]` is literal, and a bare `*` does not close that gap either",
     *bash("echo x > packages/db-memory/y.ts"), "deny", "ownership fence"),
    ("an unannotated entry still behaves exactly as before",
     "Write", {"file_path": ".orchestrator-reply.md", "content": "x"}, "allow", ""),
    ("an annotated never entry still refuses",
     *bash("echo x > apps/web/page.tsx"), "deny", "never list"),
    ("a refusal names the lines the fence could not read",
     *bash("echo x > docs/current-phase.md"), "deny", "cannot read as a path pattern"),
    ("and names the malformed line itself",
     *bash("echo x > docs/current-phase.md"), "deny", "docs the current phase file"),
]


# A brief whose `never:` list shadows one of its own `owns:` entries. Before
# BUG-20260828-010 the `never:` loop denied outright and the `owns:` check was
# never reached, so the brief granted a file the fence then refused — quoting the
# worker's own permission back at it (`dn-bootcheck`, 2026-08-28). The second
# owns entry is deliberately unshadowed: one bad line must not void the rest.
CONTRADICTORY_BRIEF = """\
# Brief — testslot

owns:
  - apps/atlas/src/index.ts
  - scripts/orchestrator/*
  - .orchestrator-reply.md

never:
  - apps/*/src/*
  - packages/**
"""

CONTRADICTION_CASES = [
    ("a write to a contradicted file says the brief contradicts itself",
     *bash("echo x > apps/atlas/src/index.ts"), "deny", "contradicts itself"),
    ("the refusal names the owns line",
     "Write", {"file_path": "apps/atlas/src/index.ts", "content": "x"},
     "deny", "owns:  apps/atlas/src/index.ts"),
    ("and the never line",
     "Write", {"file_path": "apps/atlas/src/index.ts", "content": "x"},
     "deny", "never: apps/*/src/*"),
    ("an owns entry the never list does not shadow still grants",
     *bash("sed -i 's/a/b/' scripts/orchestrator/fence.py"), "allow", ""),
    ("the contradiction is said on the way past an allowed write",
     "Write", {"file_path": ".orchestrator-reply.md", "content": "x"},
     "allow", "contradicts itself"),
    ("a never entry nothing grants is refused exactly as before",
     *bash("echo x > packages/db-memory/y.ts"), "deny", "never list"),
]


# BUG-20260904-017 — the two defects from the bug report, reproduced with the
# exact shapes it names. `fnmatch` treated `[id]` as a character class, so a
# Next.js dynamic route's own `owns:` glob never matched its own file; and
# `*` crossed `/`, so a `never:` glob one directory up silently reached two
# levels down and shadowed an exact `owns:` entry there.
ISSUE_BRIEF = """\
# Brief — testslot

owns:
  - apps/web/src/app/api/documents/[id]/export/**
  - apps/web/src/components/documents/list/drive-item.ts
  - .orchestrator-reply.md

never:
  - apps/web/src/components/documents/*
"""

ISSUE_DIRS = [
    "apps/web/src/app/api/documents/[id]/export",
    "apps/web/src/app/api/documents/[other]/export",
    "apps/web/src/components/documents/list",
]
ISSUE_FILES = [
    "apps/web/src/app/api/documents/[id]/export/route.ts",
    "apps/web/src/app/api/documents/[other]/export/route.ts",
    "apps/web/src/components/documents/toolbar.tsx",
    "apps/web/src/components/documents/list/drive-item.ts",
    ".orchestrator-reply.md",
]


def build_issue_tree(root):
    for path in ISSUE_DIRS:
        os.makedirs(os.path.join(root, path), exist_ok=True)
    for path in ISSUE_FILES:
        with open(os.path.join(root, path), "w") as handle:
            handle.write("placeholder\n")
    with open(os.path.join(root, ".orchestrator-brief.md"), "w") as handle:
        handle.write(ISSUE_BRIEF)
    subprocess.run(["git", "init", "-q", root], check=False, capture_output=True)


ISSUE_CASES = [
    # Issue 1: `[id]` is a literal directory name now, not an `fnmatch`
    # character class.
    ("issue 1: `[id]` is a literal directory name, its own export route is grantable",
     "Write", {"file_path": "apps/web/src/app/api/documents/[id]/export/route.ts",
               "content": "x"}, "allow", ""),
    ("issue 1: a sibling dynamic segment is a different literal directory, "
     "not a class hit — still outside the fence",
     "Write", {"file_path": "apps/web/src/app/api/documents/[other]/export/route.ts",
               "content": "x"}, "deny", "ownership fence"),

    # Issue 2: `*` matches one path segment, never more.
    ("issue 2: `*` still matches a direct child of the never-listed directory",
     "Write", {"file_path": "apps/web/src/components/documents/toolbar.tsx",
               "content": "x"}, "deny", "never list"),
    ("issue 2: `*` no longer crosses `/`, so the owns entry two levels down "
     "is not shadowed",
     "Write", {"file_path": "apps/web/src/components/documents/list/drive-item.ts",
               "content": "x"}, "allow", ""),
]

# The false contradiction issue 2 also caused: under the old matcher this
# brief's `--check` would have refused to launch at all, because the
# never-list glob (wrongly) covered the owns entry two directories down.
ISSUE_CHECK_CASES = [
    ("issue 2's never glob does not shadow the owns entry two levels down",
     ISSUE_BRIEF, 0, ""),
]


# BUG-20260904-017 — `**` in the middle of a pattern, not only at the end.
DOUBLESTAR_MIDDLE_BRIEF = """\
# Brief — testslot

owns:
  - apps/**/tests/*.spec.ts
  - .orchestrator-reply.md

never:
  - packages/**
"""

DOUBLESTAR_MIDDLE_DIRS = [
    "apps/tests", "apps/web/tests", "apps/web/src/tests", "apps/web/tests/nested",
]
DOUBLESTAR_MIDDLE_FILES = [
    "apps/tests/a.spec.ts",
    "apps/web/tests/b.spec.ts",
    "apps/web/src/tests/c.spec.ts",
    "apps/web/tests/b.ts",
    "apps/web/tests/nested/d.spec.ts",
    ".orchestrator-reply.md",
]


def build_doublestar_middle_tree(root):
    for path in DOUBLESTAR_MIDDLE_DIRS:
        os.makedirs(os.path.join(root, path), exist_ok=True)
    for path in DOUBLESTAR_MIDDLE_FILES:
        with open(os.path.join(root, path), "w") as handle:
            handle.write("placeholder\n")
    with open(os.path.join(root, ".orchestrator-brief.md"), "w") as handle:
        handle.write(DOUBLESTAR_MIDDLE_BRIEF)
    subprocess.run(["git", "init", "-q", root], check=False, capture_output=True)


DOUBLESTAR_MIDDLE_CASES = [
    ("`**` in the middle matches zero segments",
     "Write", {"file_path": "apps/tests/a.spec.ts", "content": "x"}, "allow", ""),
    ("`**` in the middle matches one segment",
     "Write", {"file_path": "apps/web/tests/b.spec.ts", "content": "x"}, "allow", ""),
    ("`**` in the middle matches two segments",
     "Write", {"file_path": "apps/web/src/tests/c.spec.ts", "content": "x"}, "allow", ""),
    ("the trailing segment pattern still has to match in full",
     "Write", {"file_path": "apps/web/tests/b.ts", "content": "x"},
     "deny", "ownership fence"),
    ("nothing may add another segment between `tests/` and the file",
     "Write", {"file_path": "apps/web/tests/nested/d.spec.ts", "content": "x"},
     "deny", "ownership fence"),
]


# U0 (`E-92`) — `glass-ui` is the first worktree the fence protects that is not
# shaped like `denitsa-app` at all: no `apps/`, no `packages/`, and a git
# toplevel that is not named `denitsa-app`. `fence.py` was already claimed to
# be repository-agnostic — it walks from `cwd` to the git toplevel and reads
# the brief there, never assuming a name or a layout — and this proves that
# rather than take the docstring's word for it. The tree below is what
# `dispatch.sh` seeds into a second repository's worktree: `.claude/settings.json`
# and `.claude/skills/denitsa-worker/` alongside the brief, none of it granted
# by the demo brief's `owns:` list.
SECOND_REPO_BRIEF = """\
# Brief — demo

Orchestrator: test
Branch: chore/demo

## What this slot owns, and what it must not open

owns:
  - src/components/Button.tsx
  - .orchestrator-reply.md

never:
  - package.json
"""

SECOND_REPO_DIRS = ["src/components", ".claude/skills/denitsa-worker"]
SECOND_REPO_FILES = [
    "package.json", "README.md", "biome.json",
    "src/components/Button.tsx", "src/components/Card.tsx",
]


def build_second_repo_tree(root):
    for path in SECOND_REPO_DIRS:
        os.makedirs(os.path.join(root, path), exist_ok=True)
    for path in SECOND_REPO_FILES:
        with open(os.path.join(root, path), "w") as handle:
            handle.write("placeholder\n")
    with open(os.path.join(root, ".claude", "settings.json"), "w") as handle:
        handle.write("{}\n")
    with open(os.path.join(root, ".claude", "skills", "denitsa-worker", "SKILL.md"),
              "w") as handle:
        handle.write("placeholder\n")
    with open(os.path.join(root, ".orchestrator-brief.md"), "w") as handle:
        handle.write(SECOND_REPO_BRIEF)
    subprocess.run(["git", "init", "-q", root], check=False, capture_output=True)


SECOND_REPO_CASES = [
    ("an owned file in the seeded worktree is writable",
     "Write", {"file_path": "src/components/Button.tsx", "content": "x"},
     "allow", ""),
    ("a sibling file outside owns is refused, same as in denitsa-app",
     "Write", {"file_path": "src/components/Card.tsx", "content": "x"},
     "deny", "ownership fence"),
    ("the never-listed file is refused",
     *bash("echo x > package.json"), "deny", "never list"),
    ("the seeded settings.json is not on the brief's owns list either",
     "Write", {"file_path": ".claude/settings.json", "content": "x"},
     "deny", "ownership fence"),
    ("the symlinked-in worker skill is not on the brief's owns list either",
     "Edit", {"file_path": ".claude/skills/denitsa-worker/SKILL.md",
              "old_string": "placeholder", "new_string": "x"},
     "deny", "ownership fence"),
    ("the brief itself is still the orchestrator's, in this repo too",
     *bash("echo x > .orchestrator-brief.md"),
     "deny", "brief is the orchestrator's"),
]


# `--check`: the same parse, run by `dispatch.sh` before a session exists. This
# is the half a worker cannot deliver — a refusal inside a session is visible
# only to whoever attaches to it.
SHADOWED_GLOB_BRIEF = """\
# Brief — testslot

owns:
  - scripts/orchestrator/*
  - .orchestrator-reply.md

never:
  - scripts/**
"""

# BUG-20260904-017 — `*` no longer crosses `/`, so a *single-level* never
# glob one directory up does not shadow an owns glob one level further down
# any more. Before the fix this was `SHADOWED_GLOB_BRIEF`'s own pattern
# (`scripts/*`) and it was a false contradiction — issue 2 from the bug
# report, caught here at the `--check` stage rather than mid-session.
NON_SHADOWING_SINGLE_STAR_BRIEF = """\
# Brief — testslot

owns:
  - scripts/orchestrator/*
  - .orchestrator-reply.md

never:
  - scripts/*
"""

SHADOWING_DIRECTORY_BRIEF = """\
# Brief — testslot

owns:
  - scripts/orchestrator/*
  - .orchestrator-reply.md

never:
  - scripts
"""

# owns broad, never narrow: a slot holding an application minus the one
# directory another slot has. Legitimate, common, and must stay silent.
CARVE_OUT_BRIEF = """\
# Brief — testslot

owns:
  - apps/atlas/*
  - .orchestrator-reply.md

never:
  - apps/atlas/src/auth/*
  - apps/web/*
"""

# (label, brief, expected exit code, substring expected on stderr)
CHECK_CASES = [
    ("a brief with no contradiction passes", BRIEF, 0, ""),
    ("owns naming a file a never glob denies is refused",
     CONTRADICTORY_BRIEF, 1, "apps/atlas/src/index.ts is granted by the first"),
    ("and the refusal names the never line that shadows it",
     CONTRADICTORY_BRIEF, 1, "never: apps/*/src/*"),
    ("an owns glob every path of which is denied is refused",
     SHADOWED_GLOB_BRIEF, 1, "every path `scripts/orchestrator/*` matches"),
    ("a single-level never glob one directory up no longer shadows an owns "
     "glob two levels down (BUG-20260904-017, issue 2)",
     NON_SHADOWING_SINGLE_STAR_BRIEF, 0, ""),
    ("a never entry naming a directory shadows the globs beneath it",
     SHADOWING_DIRECTORY_BRIEF, 1, "every path `scripts/orchestrator/*` matches"),
    ("owns broad with a narrow never carve-out is not a contradiction",
     CARVE_OUT_BRIEF, 0, ""),
    ("an annotated brief is read after its notes are stripped",
     ANNOTATED_BRIEF, 0, ""),
    ("an unreadable line is a warning, not a refusal",
     ANNOTATED_BRIEF, 0, "cannot be read as a path pattern"),
] + ISSUE_CHECK_CASES


def run_check(root, brief_text):
    """Drive `fence.py --check` the way `dispatch.sh` does."""
    path = os.path.join(root, "candidate-brief.md")
    with open(path, "w") as handle:
        handle.write(brief_text)
    done = subprocess.run(
        [sys.executable, FENCE, "--check", path],
        capture_output=True, text=True, timeout=30,
    )
    return done.returncode, done.stderr


def scratch_parent():
    """Somewhere to build the throwaway worktree — deliberately not `/tmp`.

    `/tmp` is the one place outside a worktree the fence allows, so a test tree
    built there would pass the out-of-worktree cases for the wrong reason.
    """
    for candidate in (os.path.expanduser("~/.cache"), os.path.expanduser("~")):
        try:
            os.makedirs(candidate, exist_ok=True)
            if os.access(candidate, os.W_OK) and not candidate.startswith("/tmp"):
                return candidate
        except OSError:
            continue
    raise SystemExit("fence_test: no writable directory outside /tmp to build in")


def run_cases(root, cases, failures, cwd=None):
    for label, tool, tool_input, expected, fragment in cases:
        decision, reason = run(root, tool, tool_input, cwd=cwd)
        ok = decision == expected and (not fragment or fragment in reason)
        print(f"{'ok  ' if ok else 'FAIL'}  {label}")
        if not ok:
            failures.append(f"{label}: expected {expected}"
                            f"{f' containing {fragment!r}' if fragment else ''}, "
                            f"got {decision} — {reason.splitlines()[0] if reason else ''}")


def main():
    root = tempfile.mkdtemp(prefix="fence-test-", dir=scratch_parent())
    failures = []
    try:
        build_tree(root)
        run_cases(root, CASES, failures)

        # BUG-20260902-001 — process signals are a shape the fence knows now.
        run_cases(root, SIGNAL_CASES, failures)

        # BUG-20260829-003 — `cwd` moved by a `cd` no longer loses the brief.
        run_cases(root, CWD_CASES, failures, cwd=os.path.join(root, "apps", "atlas"))

        # BUG-20260828-004 — an owns entry that carries an inline note.
        install_brief(root, ANNOTATED_BRIEF)
        run_cases(root, ANNOTATED_CASES, failures)

        # BUG-20260828-010 — a never pattern shadowing an owns entry.
        install_brief(root, CONTRADICTORY_BRIEF)
        run_cases(root, CONTRADICTION_CASES, failures)

        # BUG-20260828-010 — and the same contradiction refused at parse time,
        # which is what `dispatch.sh` runs before it launches a session at all.
        for label, brief_text, expected_code, fragment in CHECK_CASES:
            code, err = run_check(root, brief_text)
            ok = code == expected_code and (not fragment or fragment in err)
            print(f"{'ok  ' if ok else 'FAIL'}  {label}")
            if not ok:
                failures.append(f"{label}: expected exit {expected_code}"
                                f"{f' containing {fragment!r}' if fragment else ''}, "
                                f"got {code} — {err.splitlines()[0] if err else ''}")

        # BUG-20260829-003 — a brief that exists but cannot be read fails
        # closed, rather than running the session unfenced.
        with open(os.path.join(root, ".orchestrator-brief.md"), "wb") as handle:
            handle.write(b"owns:\n  - scripts/orchestrator/*\n\xff\xfe not valid utf-8\n")
        decision, reason = run(root, *bash("git status --short"))
        ok = decision == "deny" and "could not be read" in reason
        print(f"{'ok  ' if ok else 'FAIL'}  an unreadable brief fails closed")
        if not ok:
            failures.append("an unreadable brief fails closed: expected deny "
                            "containing 'could not be read', got "
                            f"{decision} — {reason.splitlines()[0] if reason else ''}")

        # A session with no brief is not a worker, and the hook is transparent.
        os.remove(os.path.join(root, ".orchestrator-brief.md"))
        decision, _ = run(root, *bash("echo x > apps/atlas/src/index.ts"))
        ok = decision == "allow"
        print(f"{'ok  ' if ok else 'FAIL'}  no brief means no fence")
        if not ok:
            failures.append("no brief means no fence: expected allow, "
                            f"got {decision}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # U0 — a worktree seeded into a repository that is not `denitsa-app` at
    # all. A tree of its own, so the assertion is that the fence needs nothing
    # `denitsa-app`-shaped, not that it happens to still see the first tree's
    # `apps/` and `packages/`.
    second_root = tempfile.mkdtemp(prefix="fence-test-second-repo-", dir=scratch_parent())
    try:
        build_second_repo_tree(second_root)
        run_cases(second_root, SECOND_REPO_CASES, failures)
    finally:
        shutil.rmtree(second_root, ignore_errors=True)

    # BUG-20260904-017 — the two issue shapes from the bug report, end to end.
    issue_root = tempfile.mkdtemp(prefix="fence-test-issue-017-", dir=scratch_parent())
    try:
        build_issue_tree(issue_root)
        run_cases(issue_root, ISSUE_CASES, failures)
    finally:
        shutil.rmtree(issue_root, ignore_errors=True)

    # BUG-20260904-017 — `**` in the middle of a pattern, not only at the end.
    doublestar_root = tempfile.mkdtemp(prefix="fence-test-doublestar-mid-", dir=scratch_parent())
    try:
        build_doublestar_middle_tree(doublestar_root)
        run_cases(doublestar_root, DOUBLESTAR_MIDDLE_CASES, failures)
    finally:
        shutil.rmtree(doublestar_root, ignore_errors=True)

    print()
    if failures:
        print(f"{len(failures)} failed:")
        for line in failures:
            print(f"  - {line}")
        return 1
    total = (len(CASES) + len(SIGNAL_CASES) + len(CWD_CASES) + len(ANNOTATED_CASES)
             + len(CONTRADICTION_CASES) + len(CHECK_CASES) + len(SECOND_REPO_CASES)
             + len(ISSUE_CASES) + len(DOUBLESTAR_MIDDLE_CASES) + 2)
    print(f"{total} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
