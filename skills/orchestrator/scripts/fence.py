#!/usr/bin/env python3
"""PreToolUse fence for dispatched Code Sentinel workers.

Up to five workers run in parallel worktrees off one repository. Each brief
names the files that worker owns; this refuses every write outside them, so the
boundary is a fact rather than a paragraph the worker was asked to remember.

No brief anywhere from the session's current directory up to its git toplevel
means this is not a worker session — the orchestrator's checkout, or a
person's — and the hook allows everything. A brief that exists but cannot be
read or parsed is the opposite case, and is refused rather than treated as no
brief (BUG-20260829-003): a fence that cannot read its own boundary must not
pretend there is none.

`cwd` moves, the brief does not (BUG-20260829-003)
---------------------------------------------------

`Bash` persists a `cd` for the rest of the session, and the harness hands this
hook the session's *current* directory as `cwd` on every later tool call — not
only `Bash`'s own. Looking for the brief only there meant one `cd` into a
subdirectory made every later call, of every tool, find no brief and allow
silently. The hook now walks up from `cwd` to find it, bounded by the git
toplevel, and computes every `rel` against the directory that holds it — never
against `cwd`, which would make a granted file look outside the fence from a
subdirectory.

`Bash` (BUG-20260828-004)
------------------------

The hook used to see `Edit`, `Write`, `MultiEdit` and `NotebookEdit` only, and
a heredoc, a `sed -i` or a `>` walked past it. That was not a careless worker's
exception: `bypassPermissions`, which every dispatched session runs under,
carries a standing instruction to prefer `Bash` over the file-writing tools. The
hole was the default.

So `Bash` is matched too, and the honest limits are these.

**What it sees.** A quoting- and heredoc-aware scan splits the command into
simple commands — through `;` `&&` `||` `|` and newlines, and into `$( )`,
backticks and `sh -c` — and takes the *explicit* write targets out of each:
output redirections, and the argument positions of a fixed list of commands that
write where they are told (`tee`, `sed -i`, `cp`, `mv`, `rm`, `touch`, `dd of=`,
`git apply`, …). Each target is then checked exactly as an `Edit` is, and
refused with the same words.

**Where it fails closed.** A write whose target it cannot resolve — a `$VAR`, a
substitution, a `cd` to somewhere it could not follow — is refused rather than
guessed at, and so is inline interpreter code (`python -c`, `node -e`), which is
undecidable and is not needed for read-only work.

**What it cannot see, and no shell parsing ever will.** A program that writes on
its own behalf: `bun run build`, `prisma generate`, `git checkout <branch>`, a
script committed in this repository. "What does this program write" is the
undecidable half of the problem. The mitigation for that half is not here — it
is `dispatch.sh` telling every worker, in the same layer the contrary
instruction arrives in, that file writes go through `Write`/`Edit`. This hook is
what stops that instruction from being prose again.

Process signals (BUG-20260902-001)
-----------------------------------

A worker cleaning up a process it started reaches for `pkill`/`killall` by name
or pattern, and a pattern matches whatever else on the host happens to answer
to it -- on 2026-09-02 `pkill -f "nest start --watch" -u archi` killed three dev
servers belonging to an unrelated project, because they matched the same
pattern. Nothing in the fence looked at `pkill`, `killall` or `kill`: they are
not write shapes.

They are a shape of their own now, checked the same way and through the same
scanner as a write -- past `;`, `&&`, `|`, `$( )` and `sh -c`. `pkill` and
`killall` are refused outright, in every form: there is no literal target for
either to check. `kill` is refused unless every argument that is not a signal
flag is a literal numeral -- the PID a worker captured when it started the
process -- because a job spec (`%1`), a substitution (`$(pgrep ...)`) or a
variable (`$PID`) all resolve to something the fence cannot itself verify, the
same reason a `$VAR` write target is refused.
"""
import json
import os
import re
import subprocess
import sys
from glob import glob as expand_glob

FILE_WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
BRIEF = ".orchestrator-brief.md"

# Everything outside the worktree is refused, and that includes any
# documentation repository next to it (BUG-20260828-004). A worker that could amend
# its own specification to match what it built leaves nobody able to tell a
# decision from a drift; on 2026-08-28 three lead slots found five specification
# defects between them and every one of them arrived as a report because none of
# them could reach the document. The corpus round trip goes through the
# orchestrator by design.
#
# A scratch directory is the exception, and it is the mechanism that makes the
# refusal cheap: a worker parks the fix summary in `/tmp` and reports the path.
SCRATCH_ROOTS = ("/tmp", "/var/tmp", "/dev/shm")

# Writing to these is not writing to a file.
NULL_SINKS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/fd"}


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }))
    sys.exit(0)


def allow(note=None):
    # A brief with an unreadable line is a fence that is quietly not protecting
    # what it says it protects — on the `never:` side there is no refusal to
    # carry the diagnosis, so it is said on the way past. Noisy on purpose, and
    # it stops the moment the line is fixed.
    if note:
        print(json.dumps({"systemMessage": note}))
    sys.exit(0)


# A brief may annotate an entry — `apps/web/src/lib/gql/root-fields.ts
# [RECIPES_ROOT_FIELDS only]` — and that note is written for the worker, not for
# this parser. Until BUG-20260828-004 it was kept as part of the pattern, so the
# entry matched nothing and the file its own brief granted was refused, quoting
# the worker's own permission back at it (2026-08-28). Only a
# bracket that follows whitespace is a note: `packages/db-[a-z]*` is a glob.
ANNOTATION_RE = re.compile(r"\s+\[[^\]]*\]$")


def clean_entry(raw):
    entry = raw.strip().strip("`").strip()
    entry = ANNOTATION_RE.sub("", entry)
    return entry.strip().strip("`").strip()


def unreadable(patterns):
    """Entries that cannot match any path, whatever the worker does.

    A pattern with whitespace left in it is prose, or a note whose brackets went
    missing — never a filename in this repository. Silently keeping it is a
    fence lying about its own contents, so it is named in the refusal it causes.
    """
    return [p for p in patterns if not p or re.search(r"\s", p)]


def parse_fence(text):
    """Read `owns:` and `never:` glob lists out of the brief."""
    owns, never, section = [], [], None
    for line in text.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("owns:"):
            section = owns
            continue
        if low.startswith("never:"):
            section = never
            continue
        if stripped.startswith("- ") and section is not None:
            section.append(clean_entry(stripped[2:]))
            continue
        if stripped.startswith("#") or not stripped:
            section = None
    return owns, never


def _segment_match(text, pattern_segment):
    """One path segment against one pattern segment.

    `*` matches any run of characters within the segment; everything else —
    brackets included — is literal, so `[id]` names a literal directory, not
    a character class (BUG-20260904-017).
    """
    if "*" not in pattern_segment:
        return text == pattern_segment
    regex = ".*".join(re.escape(part) for part in pattern_segment.split("*"))
    return re.fullmatch(regex, text) is not None


def _segments_match(rel_segs, pat_segs):
    """Does `rel_segs` match `pat_segs`?

    A pattern segment of exactly `**` stands for zero or more whole path
    segments; any other `*` never crosses a `/` (BUG-20260904-017) — it is
    confined to `_segment_match`, one segment at a time.
    """
    n, m = len(rel_segs), len(pat_segs)
    memo = {}

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if j == m:
            out = i == n
        elif pat_segs[j] == "**":
            out = go(i, j + 1) or (i < n and go(i + 1, j))
        elif i == n:
            out = False
        else:
            out = _segment_match(rel_segs[i], pat_segs[j]) and go(i + 1, j + 1)
        memo[key] = out
        return out

    return go(0, 0)


def matches(rel, pattern):
    # A pattern with no wildcard names a file or a directory prefix, at any
    # depth beneath it — the one rule the workaround briefs lean on, and it
    # is untouched by the rest of this function.
    if "*" not in pattern:
        return rel == pattern or rel.startswith(pattern.rstrip("/") + "/")
    return _segments_match(rel.split("/"), pattern.split("/"))


# --------------------------------------------------------------------------
# Contradictions between the two lists (BUG-20260828-010)
#
# `check` consults `never` first and denies outright, so an `owns:` entry that a
# `never:` pattern shadows grants nothing at all. The brief then tells a worker
# it holds a file the fence will refuse it — the fence quoting the worker's own
# permission back at it, which is the most expensive shape of refusal there is:
# the worker correctly stops and asks, the orchestrator correctly checks the
# fence, and both spend a round on what was never a boundary question
# (2026-08-28).
#
# Precedence is deliberately left alone. A specificity comparison between globs,
# prefixes and exact paths has to be right in every direction, and getting it
# right would still only make a silent contradiction resolve differently instead
# of not existing. So the contradiction is named instead — at parse time by
# `--check`, which `dispatch.sh` runs before it launches anything, and on the way
# past every tool call of a session already running one. Whether a deliberate
# contradiction should resolve to `owns:` stays open; nobody can create one by
# accident now.
# --------------------------------------------------------------------------

def is_glob(pattern):
    return "*" in pattern


def _as_globs(pattern):
    """The glob or globs a fence entry stands for.

    `matches` gives a wildcard-free entry directory semantics — it covers the
    path itself and everything beneath it, at any depth — so for containment
    it is two globs, and the second ends `/**` rather than `/*`: `*` no
    longer crosses a `/` (BUG-20260904-017), so `/*` would only be one level
    deep and `covers` would miss a `never:` that shadows a nested file.
    """
    if is_glob(pattern):
        return [pattern]
    return [pattern, pattern.rstrip("/") + "/**"]


def _segment_covers(outer, inner):
    """Does every string `inner` (one path segment, `*` the only wildcard)
    matches also match `outer`? Sound rather than complete, the same bias as
    `covers` below — brackets are ordinary characters here, same as `matches`.
    """
    n, m = len(outer), len(inner)
    memo = {}

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if j == m:
            # `inner` is spent; `outer` must be able to match nothing more.
            out = all(c == "*" for c in outer[i:])
        elif i == n:
            # `outer` is spent and `inner` can still produce a character.
            out = False
        elif outer[i] == "*":
            # Match nothing, or swallow one element of `inner` whole — including
            # an `inner` `*`, since `outer`'s matches any string too.
            out = go(i + 1, j) or go(i, j + 1)
        elif inner[j] == "*":
            # `inner` can produce arbitrary text here and `outer` cannot take it.
            out = False
        else:
            out = outer[i] == inner[j] and go(i + 1, j + 1)
        memo[key] = out
        return out

    return go(0, 0)


def covers(outer, inner):
    """Does every path `inner` matches also match `outer`?

    Segment-aware, the same model as `matches`: `**` stands for zero or more
    whole path segments, and any other `*` is confined to one segment via
    `_segment_covers`. Sound rather than complete: where containment cannot
    be proved it says no, so an undecided pair is never reported as a
    contradiction.
    """
    outer_segs, inner_segs = outer.split("/"), inner.split("/")
    n, m = len(outer_segs), len(inner_segs)
    memo = {}

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if j == m:
            # `inner` is spent; every remaining `outer` segment must be able
            # to match zero segments, which only `**` can.
            out = all(s == "**" for s in outer_segs[i:])
        elif i == n:
            out = False
        elif outer_segs[i] == "**":
            # Match zero segments, or swallow one whole segment of `inner` —
            # including an `inner` `**`, since `outer`'s matches any segment.
            out = go(i + 1, j) or go(i, j + 1)
        elif inner_segs[j] == "**":
            # `inner` can produce arbitrarily many segments here and a single
            # `outer` segment cannot take them.
            out = False
        else:
            out = (_segment_covers(outer_segs[i], inner_segs[j])
                   and go(i + 1, j + 1))
        memo[key] = out
        return out

    return go(0, 0)


def contradictions(owns, never):
    """`(owns entry, never entry)` pairs where the brief disagrees with itself.

    Two shapes are reported, and only these two, because every other overlap is
    a legitimate carve-out: `owns: apps/atlas/*` alongside
    `never: apps/atlas/src/auth/*` is a slot holding an application minus the one
    directory another slot has, and it behaves exactly as written.

    - An entry naming a path — the common shape, and the one this bug was filed
      for — that a `never:` pattern denies outright.
    - A glob every one of whose paths a single `never:` pattern denies.
    """
    broken = set(unreadable(owns) + unreadable(never))
    live_never = [n for n in never if n and n not in broken]
    found = []
    for entry in owns:
        if not entry or entry in broken:
            continue
        if is_glob(entry):
            shadow = next(
                (n for n in live_never
                 if any(covers(outer, inner)
                        for outer in _as_globs(n) for inner in _as_globs(entry))),
                None,
            )
        else:
            shadow = next((n for n in live_never if matches(entry, n)), None)
        if shadow:
            found.append((entry, shadow))
    return found


def contradiction_report(pairs):
    """The refusal, naming both lines and the file they disagree about."""
    blocks = []
    for entry, pattern in pairs:
        subject = f"every path `{entry}` matches" if is_glob(entry) else entry
        blocks.append(f"  owns:  {entry}\n"
                      f"  never: {pattern}\n"
                      f"  -> {subject} is granted by the first line and denied "
                      f"by the second.")
    return ("This brief contradicts itself. The `never:` list is checked first, "
            "so each of these `owns:` lines grants nothing at all:\n\n"
            + "\n\n".join(blocks)
            + "\n\nNarrow the `never:` pattern or drop the `owns:` line. Until "
              "one of the two changes, the fence refuses a file the brief says "
              "this slot holds (BUG-20260828-010).")


# --------------------------------------------------------------------------
# Shell scanning
#
# Not a shell parser, and it does not pretend to be one. It recovers the two
# things the fence needs — where a command has been told to write, and whether
# it can be sure — and refuses when it cannot be sure.
# --------------------------------------------------------------------------

class Word:
    """One shell word, with what the scanner could not resolve about it."""

    __slots__ = ("text", "dynamic", "globby")

    def __init__(self, text, dynamic=False, globby=False):
        self.text = text
        self.dynamic = dynamic
        self.globby = globby

    def __repr__(self):  # pragma: no cover - debugging only
        return f"Word({self.text!r}, dynamic={self.dynamic})"


REDIR_RE = re.compile(r"(\d*)(&>>|&>|>&|<&|>>|>\||>|<<-|<<<|<<|<)")
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WORD_BREAK = set(" \t\n;|&()<>")


def _read_balanced(text, i, opener, closer):
    """From just inside an opener, return (content, index after the closer)."""
    depth, start, n = 1, i, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = text.find("'", i + 1)
            i = n if j == -1 else j + 1
            continue
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    return text[start:n], n


def _read_word(text, i, subs):
    """Read one word from `i`. Appends any command substitutions to `subs`."""
    out, dynamic, globby, n = [], False, False, len(text)
    while i < n:
        c = text[i]
        if c in WORD_BREAK:
            break
        if c == "\\":
            if i + 1 < n:
                out.append(text[i + 1])
                i += 2
            else:
                i += 1
            continue
        if c == "'":
            j = text.find("'", i + 1)
            j = n if j == -1 else j
            out.append(text[i + 1:j])
            i = j + 1
            continue
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if text.startswith("$(", i):
                    sub, i = _read_balanced(text, i + 2, "(", ")")
                    subs.append(sub)
                    dynamic = True
                    continue
                if text[i] == "`":
                    sub, i = _read_balanced(text, i + 1, "\0", "`")
                    subs.append(sub)
                    dynamic = True
                    continue
                if text[i] == "$":
                    dynamic = True
                out.append(text[i])
                i += 1
            i += 1
            continue
        if text.startswith("$(", i):
            sub, i = _read_balanced(text, i + 2, "(", ")")
            subs.append(sub)
            dynamic = True
            continue
        if c == "`":
            sub, i = _read_balanced(text, i + 1, "\0", "`")
            subs.append(sub)
            dynamic = True
            continue
        if c == "$":
            dynamic = True
            out.append(c)
            i += 1
            continue
        if c in "*?[":
            globby = True
        out.append(c)
        i += 1
    return Word("".join(out), dynamic, globby), i


def _skip_heredoc(text, i, delim, strip_tabs):
    """From the start of a heredoc body, return the index past its terminator."""
    n = len(text)
    while i < n:
        end = text.find("\n", i)
        end = n if end == -1 else end
        line = text[i:end]
        if (line.lstrip("\t") if strip_tabs else line).strip() == delim:
            return min(end + 1, n)
        i = end + 1
    return n


def scan(command):
    """Split a command string into simple commands.

    Returns a list of dicts: `words` (the argv, as `Word`s) and `writes` (the
    targets of output redirections). Command substitutions are scanned too and
    appear as further simple commands in the same list.
    """
    cmds, subs = [], []
    cur = {"words": [], "writes": [], "stdin": False}
    heredocs = []
    i, n = 0, len(command)
    at_word_start = True

    def flush():
        nonlocal cur
        if cur["words"] or cur["writes"] or cur["stdin"]:
            cmds.append(cur)
        cur = {"words": [], "writes": [], "stdin": False}

    while i < n:
        c = command[i]
        if c in " \t":
            i += 1
            at_word_start = True
            continue
        if c == "\n":
            i += 1
            for delim, strip_tabs in heredocs:
                i = _skip_heredoc(command, i, delim, strip_tabs)
            heredocs = []
            flush()
            at_word_start = True
            continue
        if c == "#" and at_word_start:
            end = command.find("\n", i)
            i = n if end == -1 else end
            continue
        if command.startswith("&&", i) or command.startswith("||", i) or command.startswith(";;", i):
            i += 2
            flush()
            at_word_start = True
            continue
        if c in ";|&" or c in "()":
            i += 1
            flush()
            at_word_start = True
            continue

        m = REDIR_RE.match(command, i)
        if m:
            op = m.group(2)
            i = m.end()
            while i < n and command[i] in " \t":
                i += 1
            word, i = _read_word(command, i, subs)
            at_word_start = False
            if op in ("<<", "<<-"):
                heredocs.append((word.text, op == "<<-"))
                if not m.group(1):
                    cur["stdin"] = True
            elif op in (">&", "<&"):
                # `2>&1` and friends duplicate a descriptor. `>&file` is a write.
                if not re.fullmatch(r"\d+|-", word.text):
                    cur["writes"].append(word)
            elif op in ("<", "<<<"):
                # Reading, or a here-string — but which matters when the reader
                # is an interpreter taking its program that way.
                if not m.group(1):
                    cur["stdin"] = True
            else:
                cur["writes"].append(word)
            continue

        if c in "{}" and at_word_start and (i + 1 >= n or command[i + 1] in " \t\n"):
            i += 1
            flush()
            continue

        word, i = _read_word(command, i, subs)
        at_word_start = False
        if word.text or word.dynamic:
            cur["words"].append(word)

    for delim, strip_tabs in heredocs:
        i = _skip_heredoc(command, i, delim, strip_tabs)
    flush()

    for sub in subs:
        cmds.extend(scan(sub))
    return cmds


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

# Commands whose arguments name what they write.
WRITE_ALL_ARGS = {
    "tee", "rm", "rmdir", "unlink", "shred", "touch", "mkdir", "truncate",
    "mktemp",
}
WRITE_LAST_ARG = {"cp", "mv", "install", "ln", "rsync"}
WRITE_SKIP_FIRST = {"chmod", "chown", "chgrp", "setfacl"}

# Flags that swallow the argument after them, so it is not a path.
FLAG_TAKES_VALUE = {
    "truncate": {"-s", "--size", "-r", "--reference"},
    "install": {"-m", "--mode", "-o", "--owner", "-g", "--group", "-t",
                "--target-directory", "-S", "--suffix"},
    "cp": {"-t", "--target-directory", "-S", "--suffix"},
    "mv": {"-t", "--target-directory", "-S", "--suffix"},
    "ln": {"-t", "--target-directory", "-S", "--suffix"},
    "rsync": {"-e", "--rsh", "--exclude", "--include", "--files-from"},
    "mktemp": {"--suffix", "--tmpdir", "-p"},
    "kill": {"-s", "--signal"},
}

# `pkill`/`killall` name their target by pattern; there is no literal form for
# either, so both are refused outright rather than classified further.
PROCESS_SIGNAL_BY_NAME = {"pkill", "killall"}

# Prefixes that are not the command.
WRAPPERS = {"sudo", "env", "nice", "ionice", "nohup", "time", "command",
            "builtin", "exec", "stdbuf", "setsid"}
WRAPPERS_WITH_ARG = {"timeout": 1, "xargs": 0}

SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}

# Interpreters given code on the command line. What that code writes is not
# decidable, and a fenced worker has no read-only need for one.
INLINE_INTERPRETERS = {"python", "python2", "python3", "perl", "ruby", "node",
                       "bun", "deno", "php", "Rscript"}
INLINE_FLAGS = {"-c", "-e", "-E", "--eval", "--exec", "-p"}

# `git` writes the index and the object store constantly; only these touch
# working-tree files at paths the command names.
GIT_WRITERS = {"apply", "restore", "rm", "mv", "clean"}


def _strip_wrappers(words):
    idx = 0
    while idx < len(words):
        text = words[idx].text
        if ASSIGNMENT_RE.match(text):
            idx += 1
            continue
        head = os.path.basename(text)
        if head in WRAPPERS:
            idx += 1
            continue
        if head in WRAPPERS_WITH_ARG:
            idx += 1 + WRAPPERS_WITH_ARG[head]
            # skip xargs' own flags
            while idx < len(words) and words[idx].text.startswith("-"):
                idx += 1
            continue
        break
    return words[idx:]


def _positional(words, head):
    """Arguments that are not flags, and not a flag's value."""
    takes = FLAG_TAKES_VALUE.get(head, set())
    out, skip, seen_ddash = [], False, False
    for word in words[1:]:
        if skip:
            skip = False
            continue
        if not seen_ddash and word.text == "--":
            seen_ddash = True
            continue
        if not seen_ddash and word.text.startswith("-") and len(word.text) > 1:
            if word.text.split("=")[0] in takes and "=" not in word.text:
                skip = True
            continue
        out.append(word)
    return out


def _sed_in_place(words):
    """`sed -i` / `perl -i` targets, or None when it is not editing in place."""
    in_place = any(
        w.text == "--in-place" or w.text.startswith("--in-place=")
        or (w.text.startswith("-") and not w.text.startswith("--") and "i" in w.text[1:])
        for w in words[1:]
    )
    if not in_place:
        return None
    has_script_flag = any(
        w.text in ("-e", "-f", "--expression", "--file") for w in words[1:]
    )
    args = _positional(words, "sed")
    return args if has_script_flag else args[1:]


def write_targets(cmd, cwd):
    """(targets, undecidable_reason) for one simple command."""
    words = _strip_wrappers(cmd["words"])
    targets = list(cmd["writes"])
    if not words:
        return targets, None

    head_word = words[0]
    if head_word.dynamic:
        return targets, f"the command name itself is built at run time: {head_word.text!r}"
    head = os.path.basename(head_word.text)

    if head in SHELLS or head in INLINE_INTERPRETERS:
        # `python3 - <<'EOF'`, `bash <<EOF`, `node -` — the program arrives on
        # stdin, so it is not on the command line to be read at all.
        if cmd.get("stdin") or any(w.text == "-" for w in words[1:]):
            return targets, (
                f"`{head}` is taking its program from standard input, so what it "
                f"writes is not on the command line"
            )

    if head in SHELLS:
        for idx, word in enumerate(words[1:], 1):
            if word.text == "-c":
                if idx + 1 >= len(words):
                    return targets, "`-c` with nothing after it"
                inner = words[idx + 1]
                if inner.dynamic:
                    return targets, "a `-c` script assembled at run time"
                for sub in scan(inner.text):
                    sub_targets, reason = write_targets(sub, cwd)
                    if reason:
                        return targets, reason
                    targets.extend(sub_targets)
                return targets, None
        return targets, None

    if head in INLINE_INTERPRETERS:
        for word in words[1:]:
            if word.text in INLINE_FLAGS:
                return targets, (
                    f"`{head} {word.text}` runs code given on the command line, "
                    f"and what that code writes cannot be read off the command"
                )

    if head in ("sed", "perl"):
        edited = _sed_in_place(words)
        if edited is not None:
            targets.extend(edited)
        return targets, None

    if head == "patch":
        return targets, (
            "`patch` writes the files named inside the diff, which are not on "
            "the command line"
        )

    if head == "dd":
        for word in words[1:]:
            if word.text.startswith("of="):
                targets.append(Word(word.text[3:], word.dynamic, word.globby))
        return targets, None

    if head == "git":
        args = [w for w in words[1:] if not w.text.startswith("-")]
        if not args:
            return targets, None
        sub = args[0].text
        if sub in GIT_WRITERS:
            targets.extend(args[1:])
        elif sub in ("checkout", "switch"):
            # Only `git checkout -- <paths>` names files; a branch checkout does
            # not, and is one of the misses this hook documents.
            texts = [w.text for w in words[1:]]
            if "--" in texts:
                targets.extend(words[1:][texts.index("--") + 1:])
        return targets, None

    if head in WRITE_ALL_ARGS:
        targets.extend(_positional(words, head))
        return targets, None

    if head in WRITE_SKIP_FIRST:
        targets.extend(_positional(words, head)[1:])
        return targets, None

    if head in WRITE_LAST_ARG:
        args = _positional(words, head)
        if len(args) < 2:
            targets.extend(args)
            return targets, None
        dest = args[-1]
        dest_abs = None if (dest.dynamic or cwd is None) else os.path.join(cwd, os.path.expanduser(dest.text))
        if dest_abs is not None and os.path.isdir(dest_abs):
            for src in args[:-1]:
                targets.append(Word(
                    os.path.join(dest.text, os.path.basename(src.text)),
                    src.dynamic or dest.dynamic,
                    src.globby,
                ))
        else:
            targets.append(dest)
        return targets, None

    return targets, None


# `stop a process you started by the PID you captured` is repeated in every
# refusal below on purpose (BUG-20260902-001): it is the rule, not commentary.
STOP_BY_PID = "Stop a process you started by the PID you captured"


def signal_violation(cmd):
    """The reason this simple command is a refused process signal, or `None`.

    Mirrors `write_targets`' `sh -c` recursion, because the shape hides behind
    a shell exactly as a write does: `bash -c 'pkill -f x'` is on the command
    line and has to be read the same way `bash -c 'echo x > y'` is.
    """
    words = _strip_wrappers(cmd["words"])
    if not words:
        return None

    head_word = words[0]
    if head_word.dynamic:
        # A dynamic command name already fails the whole `Bash` call closed
        # through `write_targets`; nothing more to say about it here.
        return None
    head = os.path.basename(head_word.text)

    if head in SHELLS:
        for idx, word in enumerate(words[1:], 1):
            if word.text == "-c":
                if idx + 1 >= len(words) or words[idx + 1].dynamic:
                    return None
                for sub in scan(words[idx + 1].text):
                    reason = signal_violation(sub)
                    if reason:
                        return reason
                return None
        return None

    if head in PROCESS_SIGNAL_BY_NAME:
        return (f"This `Bash` command runs `{head}`, which signals processes by "
                f"name or pattern. A pattern matches whatever else on the host "
                f"happens to answer to it, not only what this session started "
                f"(BUG-20260902-001), so the fence refuses `pkill` and "
                f"`killall` outright. {STOP_BY_PID}.")

    if head == "kill":
        for word in _positional(words, "kill"):
            if word.dynamic:
                return (f"This `Bash` command runs `kill` on a target built at "
                        f"run time, not a literal PID -- the same reason the "
                        f"fence refuses a dynamic write target. {STOP_BY_PID}.")
            if not re.fullmatch(r"[0-9]+", word.text):
                return (f"This `Bash` command runs `kill` on `{word.text}`, "
                        f"which is not a literal numeric PID. The fence "
                        f"allows only a literal PID or a list of them. "
                        f"{STOP_BY_PID}.")
        return None

    return None


def resolve(word, cwd):
    """Absolute paths a target word names, or None when it cannot be resolved."""
    if word.dynamic or cwd is None:
        return None
    text = os.path.expanduser(word.text)
    if not text:
        return None
    if word.globby:
        hits = expand_glob(os.path.join(cwd, text) if not os.path.isabs(text) else text)
        if hits:
            return [os.path.realpath(h) for h in hits]
    return [os.path.realpath(os.path.join(cwd, text))]


# --------------------------------------------------------------------------
# The fence itself
# --------------------------------------------------------------------------

def git_ignored(root, rels):
    """Which of `rels` git ignores. On any failure, none of them — fail closed."""
    if not rels:
        return set()
    probes = []
    for rel in rels:
        probes.append(rel)
        if os.path.isdir(os.path.join(root, rel)):
            probes.append(rel.rstrip("/") + "/")
    try:
        done = subprocess.run(
            ["git", "-C", root, "check-ignore", "--stdin"],
            input="\n".join(probes), capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return set()
    return {line.strip().rstrip("/") for line in done.stdout.splitlines() if line.strip()}


def check(abs_target, root_real, brief_real, owns, never, what):
    """Deny if `abs_target` is outside the fence. `what` names the tool for the
    message when the shell is involved."""
    if abs_target == brief_real:
        deny("The brief is the orchestrator's. Report what is wrong with it "
             "instead of editing it.")

    if not abs_target.startswith(root_real + os.sep):
        for scratch in SCRATCH_ROOTS:
            if abs_target.startswith(scratch + os.sep):
                return
        deny(f"{what}{abs_target} is outside this worktree. Another worker is "
             f"in there right now, and anything outside this worktree is the "
             f"orchestrator's to land. Park the file under /tmp and report the "
             f"path; do not reach across.")

    rel = os.path.relpath(abs_target, root_real)

    for pattern in never:
        if matches(rel, pattern):
            granted = next((p for p in owns if matches(rel, p)), None)
            if granted is not None:
                # Both lists claim this file. The refusal stands — `never` names
                # live contention and is not overridden by a parse this hook
                # cannot be sure of — but it is not the worker's boundary to
                # argue, and saying "another slot owns it" would be quoting the
                # worker's own permission back at it (BUG-20260828-010).
                deny(f"{what}{rel} is on **both** of this brief's lists, so the "
                     f"brief contradicts itself:\n\n"
                     f"  owns:  {granted}\n"
                     f"  never: {pattern}\n\n"
                     f"The `never:` list is checked first, so the `owns:` line "
                     f"grants nothing and this write is refused. That is a "
                     f"defect in the brief, not a boundary you have crossed: "
                     f"report both lines to the orchestrator and let it decide "
                     f"which one is wrong. Do not work around it.")
            deny(f"{what}{rel} is on this slot's never list. It belongs to "
                 f"another slot in this wave. Report it to the orchestrator.")

    if owns and not any(matches(rel, p) for p in owns):
        # Files git does not track are in nobody's diff, so they are in nobody's
        # fence either — build output, `node_modules`, a local `.env`. The
        # never-list is not softened this way: that one names live contention.
        first = rel.split(os.sep, 1)[0]
        if first != ".git" and rel in git_ignored(root_real, [rel]):
            return
        owned = "\n".join(f"  - {p}" for p in owns)
        broken = unreadable(owns) + unreadable(never)
        note = ""
        if broken:
            lines = "\n".join(f"  - {p!r}" for p in broken)
            note = (f"\n\n**This brief also has {len(broken)} line(s) the fence "
                    f"cannot read as a path pattern:**\n{lines}\nEach of those "
                    f"matches nothing. If one of them was meant to grant this "
                    f"file, that is the bug — say so to the orchestrator rather "
                    f"than arguing the boundary.")
        deny(f"{what}{rel} is outside this slot's ownership fence.\n\nThis slot "
             f"owns only:\n{owned}\n\nAnother worker may be in that file right "
             f"now. If you genuinely need it, that is a message to the "
             f"orchestrator, not an edit.{note}")


def check_bash(command, root, root_real, brief_real, owns, never):
    cwd = root
    for cmd in scan(command):
        words = _strip_wrappers(cmd["words"])

        signal_reason = signal_violation(cmd)
        if signal_reason:
            deny(signal_reason)

        targets, reason = write_targets(cmd, cwd)
        for word in targets:
            if word.text in NULL_SINKS or word.text.startswith("/dev/fd/"):
                continue
            paths = resolve(word, cwd)
            if paths is None:
                deny(
                    f"This `Bash` command writes to `{word.text}`, and the fence "
                    f"cannot tell where that is — it is built at run time, or it "
                    f"follows a `cd` the fence could not follow.\n\nThe fence "
                    f"refuses what it cannot check. Write files with `Write` or "
                    f"`Edit`, which it can check exactly; if you need this "
                    f"command, tell the orchestrator what it writes."
                )
            for path in paths:
                check(path, root_real, brief_real, owns, never, "`Bash` writes: ")

        if reason:
            deny(
                f"The fence cannot tell what this `Bash` command writes: "
                f"{reason}.\n\nIt refuses what it cannot check. Use `Write` or "
                f"`Edit` for file writes — they are checked against this slot's "
                f"ownership fence exactly — or ask the orchestrator."
            )

        # Follow `cd` so a later relative path resolves where it really lands.
        if words and os.path.basename(words[0].text) == "cd":
            args = [w for w in words[1:] if not w.text.startswith("-")]
            if not args:
                cwd = os.path.expanduser("~")
            elif args[0].dynamic or args[0].text == "-" or cwd is None:
                cwd = None
            else:
                cwd = os.path.realpath(os.path.join(cwd, os.path.expanduser(args[0].text)))


# --------------------------------------------------------------------------
# Finding the brief (BUG-20260829-003)
#
# `Bash` persists a `cd` for the rest of the session, and the harness hands
# this hook the session's *current* directory as `cwd` on every later tool
# call — not only `Bash`'s own. A hook that looked for the brief only there
# stopped seeing it the moment a worker's shell moved one level down, and
# `allow()` fired silently, for every tool. The brief lives at the worktree
# root; a moved `cwd` is still somewhere under it, so the fix is to walk up
# and find it.
#
# The walk is bounded by the git toplevel, not the filesystem root: a
# worker's worktree *is* a git toplevel (`dispatch.sh` creates one per slot),
# so this stops exactly at the boundary a `cd` can never carry a session past,
# and a session with no brief anywhere in its own repository — the
# orchestrator, a person — is never mistaken for a fenced one.
# --------------------------------------------------------------------------

def git_toplevel(start):
    """The git toplevel `start` is inside, or None outside any repository."""
    try:
        done = subprocess.run(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    if done.returncode != 0 or not done.stdout.strip():
        return None
    return os.path.realpath(done.stdout.strip())


def find_brief(start):
    """Walk up from `start` for the nearest `.orchestrator-brief.md`.

    Returns `(root, brief_path)` for the directory that holds it, or
    `(None, None)` when there is none between `start` and the git toplevel
    (inclusive) — or between `start` and the filesystem root, when `start` is
    not inside a git repository at all.
    """
    current = os.path.realpath(start)
    toplevel = git_toplevel(current)
    while True:
        candidate = os.path.join(current, BRIEF)
        if os.path.isfile(candidate):
            return current, candidate
        if toplevel is not None and current == toplevel:
            return None, None
        parent = os.path.dirname(current)
        if parent == current:
            return None, None
        current = parent


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        allow()  # never break a session over a malformed event

    tool = data.get("tool_name")
    if tool not in FILE_WRITE_TOOLS and tool != "Bash":
        allow()

    session_cwd = data.get("cwd") or os.getcwd()
    root_real, brief_path = find_brief(session_cwd)
    if root_real is None:
        allow()

    brief_real = os.path.realpath(brief_path)

    try:
        brief_text = open(brief_path, encoding="utf-8").read()
    except Exception as exc:
        deny(f"The brief at {brief_path} exists but could not be read "
             f"({exc!r}). The fence fails closed rather than run this "
             f"session unfenced — report this to the orchestrator.")

    try:
        owns, never = parse_fence(brief_text)
    except Exception as exc:
        deny(f"The brief at {brief_path} exists but could not be parsed "
             f"({exc!r}). The fence fails closed rather than run this "
             f"session unfenced — report this to the orchestrator.")

    broken = unreadable(owns) + unreadable(never)
    notes = []
    if broken:
        notes.append("This brief has " + str(len(broken)) + " fence line(s) the "
                     "hook cannot read as a path pattern ("
                     + ", ".join(repr(p) for p in broken)
                     + "). They match nothing, so they neither grant nor protect "
                       "anything. Tell the orchestrator.")
    clashes = contradictions(owns, never)
    if clashes:
        # `dispatch.sh` refuses a brief like this before the session starts, so
        # reaching here means the brief was edited live or the worker was
        # launched by hand. Said on the way past every call, because the write
        # that would carry the refusal may never be attempted.
        notes.append(contradiction_report(clashes))
    note = "\n\n".join(notes) if notes else None

    tool_input = data.get("tool_input") or {}

    if tool == "Bash":
        command = tool_input.get("command")
        if not command:
            allow(note)
        try:
            check_bash(command, session_cwd, root_real, brief_real, owns, never)
        except SystemExit:
            raise
        except Exception as exc:
            # A scanner that crashed did not check anything. Say so rather than
            # letting the write through on a stack trace.
            deny(f"The fence could not read this `Bash` command ({exc!r}), so it "
                 f"cannot say whether it writes outside this slot. Use `Write` "
                 f"or `Edit`, or ask the orchestrator.")
        allow(note)

    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        allow(note)

    check(os.path.realpath(os.path.join(session_cwd, target)),
          root_real, brief_real, owns, never, "")
    allow(note)


USAGE = ("usage: fence.py --check <brief>\n"
         "       fence.py            (PreToolUse hook: the event arrives on stdin)")


def check_brief(path):
    """`--check` — refuse a brief whose fence contradicts itself, before launch.

    This is the half of the fix a worker cannot deliver (BUG-20260828-010): a
    session refused mid-flight is only visible to whoever attaches to it, and the
    orchestrator dispatched four other slots in the same minute. `dispatch.sh`
    runs this before it copies the brief in, so the mistake is caught in the
    second it is made.
    """
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"fence: cannot read the brief {path}: {exc}", file=sys.stderr)
        return 2

    owns, never = parse_fence(text)

    broken = unreadable(owns) + unreadable(never)
    if broken:
        # Not fatal — an unreadable line matches nothing, so it grants and
        # protects nothing, and the session says so on every call (#129). Worth
        # a word here because the brief is in front of somebody who can fix it.
        lines = ", ".join(repr(p) for p in broken)
        print(f"fence: warning: {len(broken)} fence line(s) in {path} cannot be "
              f"read as a path pattern ({lines}). They match nothing.",
              file=sys.stderr)

    clashes = contradictions(owns, never)
    if not clashes:
        return 0
    print(contradiction_report(clashes), file=sys.stderr)
    return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check" and len(sys.argv) == 3:
            sys.exit(check_brief(sys.argv[2]))
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    main()
