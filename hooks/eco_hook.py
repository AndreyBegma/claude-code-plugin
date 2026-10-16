#!/usr/bin/env python3
"""cs-eco hooks: what happens on each event once eco is on.

`hooks.json` runs `eco_run.py`, a few lines that check on/off and then import
this module — Python caches the bytecode of an imported module but recompiles
the script it was started with on every run, and this file is too big for that
on every Bash and Read call. `main()` here does the same as `eco_run.py`, for
running it directly.

Events: PreToolUse (Bash, Read), PostToolUse (Read, mcp__*), SessionStart and
PreCompact. It runs in every session that loads the plugin, so nothing happens
unless `eco_lib.resolve` says eco is on for this session.

  PreToolUse Bash  (E1, E3) — delegate to `agentdock-runner filter-hook`, only
                   in bypassPermissions and auto. The runner decides: rewrite +
                   allow in bypass, rewrite without a decision in auto (≥ 0.12.1),
                   nothing otherwise. The rewritten command gets this session's
                   AGENTDOCK_FILTER_* assignments as a prefix, so the runner's
                   `filter` writes its stats rows into our state dir. Nothing
                   when kill_guard would deny the command, nothing when the
                   session was launched by the runner (it already filters).
  PreToolUse Read  (E6) — soft guard for big files, soft dedup of repeated reads.
  PostToolUse Read — remember what was read, for dedup.
  PostToolUse mcp__* (E5 i) — cut a large result to head and tail, save it all.
  SessionStart     — inject the working register once; reset on compact/clear.
  PreCompact       — reset the read memory: nothing read is in context after it.

Fails open: any error prints nothing and exits 0, which Claude Code reads as
"no decision" — the call runs as it was.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eco_lib  # noqa: E402

FILTER_MODES = ("bypassPermissions", "auto")
RUNNER_TIMEOUT = 5  # seconds; hooks.json gives the hook 10


def emit(obj):
    sys.stdout.write(json.dumps(obj))


def deny(reason):
    emit({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }})


# ---- Bash: the command filter ---------------------------------------------------

def _platform_package():
    import platform
    osname = {"linux": "linux", "darwin": "darwin", "win32": "win32"}.get(sys.platform, sys.platform)
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(machine, machine)
    return "agentdock-runner-%s-%s" % (osname, arch)


def _executable(path):
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def find_runner(env=None):
    """The compiled runner binary, not the npm Node shim in front of it: the shim
    costs ~40 ms of Node start-up on every Bash call. Falls back to the shim."""
    import shutil
    env = os.environ if env is None else env
    wrapper = shutil.which("agentdock-runner", path=env.get("PATH"))
    if not wrapper:
        return None
    real = os.path.realpath(wrapper)
    if not real.endswith(".js"):
        return real  # already the binary
    pkg = _platform_package()
    root = os.path.dirname(os.path.dirname(real))  # …/agentdock-runner
    candidates = [
        os.path.join(root, "node_modules", pkg, "bin", "agentdock-runner"),
        os.path.join(os.path.dirname(root), pkg, "bin", "agentdock-runner"),  # hoisted
    ]
    for c in candidates:
        if _executable(c):
            return c
    try:
        import subprocess
        npm_root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True,
                                  timeout=3).stdout.strip()
        c = os.path.join(npm_root, pkg, "bin", "agentdock-runner")
        if npm_root and _executable(c):
            return c
    except Exception:
        pass
    return wrapper


def runner_path(sid, env=None):
    """`find_runner`, resolved once per session and cached in its state dir."""
    d = eco_lib.session_dir(sid, env)
    cache = os.path.join(d, "runner") if d else None
    if cache:
        try:
            with open(cache) as f:
                cached = f.read().strip()
            if _executable(cached):
                return cached
        except OSError:
            pass
    path = find_runner(env)
    if path and cache:
        try:
            os.makedirs(d, exist_ok=True)
            eco_lib._atomic_write(cache, path + "\n")
        except OSError:
            pass
    return path


def on_bash(data, sid):
    if data.get("permission_mode") not in FILTER_MODES:
        return
    if os.environ.get("AGENTDOCK_FILTER_STATS"):
        return  # launched by the runner with Token saver on: its own hook filters
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return
    import kill_guard
    if kill_guard.violation(command):
        return  # kill_guard denies it; never answer the same call with an allow
    runner = runner_path(sid)
    if not runner:
        return
    import shlex
    import subprocess
    fenv = eco_lib.filter_env(sid, data.get("cwd") or os.getcwd())
    env = dict(os.environ)
    env.update(fenv)
    out = subprocess.run([runner, "filter-hook"], input=json.dumps(data), capture_output=True,
                         text=True, timeout=RUNNER_TIMEOUT, env=env).stdout.strip()
    if not out:
        return
    result = json.loads(out)
    hso = result.get("hookSpecificOutput") or {}
    updated = hso.get("updatedInput") or {}
    wrapped = updated.get("command")
    if hso.get("hookEventName") != "PreToolUse" or not isinstance(wrapped, str):
        return
    if hso.get("permissionDecision") not in (None, "allow"):
        return
    prefix = " ".join("%s=%s" % (k, shlex.quote(v)) for k, v in fenv.items())
    updated["command"] = prefix + " " + wrapped
    hso["updatedInput"] = updated
    emit({"hookSpecificOutput": hso})


# ---- Read: soft guard and dedup (E6) -------------------------------------------

OUTLINE_MAX = 40
SCAN_BYTES = 8 * 1024 * 1024

_CODE_PREFIXES = (
    "def ", "async def ", "class ", "function ", "async function ", "export ", "interface ",
    "type ", "enum ", "struct ", "impl ", "trait ", "fn ", "pub ", "func ", "module ",
    "package ", "const ", "let ", "var ", "public ", "private ", "protected ", "abstract ",
    "@", "describe(", "test(", "it(",
)


def outline(text, path):
    """Headings for Markdown, top-level declarations for code, with line numbers."""
    is_md = path.lower().endswith((".md", ".mdx", ".markdown", ".rst"))
    entries = []
    in_fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if is_md:
            if line.startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence and line.startswith("#") and line.lstrip("#").startswith(" "):
                entries.append((n, line.strip()))
        elif line[:1] not in ("", " ", "\t") and line.startswith(_CODE_PREFIXES):
            entries.append((n, line.strip()[:120]))
    more = max(0, len(entries) - OUTLINE_MAX)
    if more:
        step = len(entries) / float(OUTLINE_MAX)
        entries = [entries[int(i * step)] for i in range(OUTLINE_MAX)]
    return entries, more


def scan(path, size):
    """(line count, text) of a text file; (None, None) for binary."""
    with open(path, "rb") as f:
        blob = f.read(SCAN_BYTES)
    if b"\0" in blob[:8192]:
        return None, None
    lines = blob.count(b"\n") + (1 if blob and not blob.endswith(b"\n") else 0)
    return lines, blob.decode("utf-8", "replace")


def guard_hint(path, lines, size, text, truncated):
    entries, more = outline(text, path)
    head = "cs-eco read guard: %s is %s%d lines (%s bytes) — not read." % (
        path, "at least " if truncated else "", lines, "{:,}".format(size))
    body = []
    if entries:
        body.append("Outline:")
        body.extend("  %d: %s" % e for e in entries)
        if more:
            body.append("  (%d more, sampled)" % more)
    else:
        body.append("No outline (no headings or top-level declarations found).")
    tail = ("Re-read with offset/limit for the part you need (Grep finds the line), "
            "or repeat the same call to read it all.")
    return "\n".join([head] + body + [tail])


def _when(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))


def on_read(data, sid):
    ti = data.get("tool_input") or {}
    path = ti.get("file_path")
    if not isinstance(path, str) or not os.path.isabs(path):
        return
    try:
        st = os.stat(path)
    except OSError:
        return
    if not os.path.isfile(path):
        return
    cwd = data.get("cwd") or os.getcwd()
    key = eco_lib.read_key(ti, st)
    reads = eco_lib.load_reads(sid)
    pending = reads["denied"].get(key)

    if pending:
        # The repeat of a soft denial: let it through, and take back the saving
        # the denial claimed (raw − kept of this row cancels it to −hint).
        del reads["denied"][key]
        eco_lib.save_reads(sid, reads)
        hint = int(pending.get("hint", 0))
        eco_lib.write_row(sid, cwd, "cs-eco/" + pending.get("kind", "read"), hint,
                          int(pending.get("bytes", 0)) + hint, bypassed=True)
        return

    seen = reads["read"].get(key)
    if seen:
        estimate = st.st_size
        if ti.get("limit"):
            try:
                lines, _ = scan(path, st.st_size)
                if lines:
                    estimate = min(st.st_size, int(st.st_size / float(lines) * int(ti["limit"])))
            except Exception:
                pass
        reason = ("cs-eco: %s (this range) is already in context since %s and has not changed "
                  "since. Use what you have; repeat the same call to read it again." % (path, _when(seen)))
        reads["denied"][key] = {"kind": "dedup", "bytes": estimate, "hint": len(reason)}
        eco_lib.save_reads(sid, reads)
        eco_lib.write_row(sid, cwd, "cs-eco/dedup", estimate, len(reason))
        deny(reason)
        return

    if ti.get("offset") is not None or ti.get("limit") is not None or ti.get("pages"):
        return
    lines, text = scan(path, st.st_size)
    if lines is None or lines <= eco_lib.GUARD_LINES:
        return
    reason = guard_hint(path, lines, st.st_size, text, st.st_size > SCAN_BYTES)
    reads["denied"][key] = {"kind": "read-guard", "bytes": st.st_size, "hint": len(reason)}
    eco_lib.save_reads(sid, reads)
    eco_lib.write_row(sid, cwd, "cs-eco/read-guard", st.st_size, len(reason))
    deny(reason)


def on_read_done(data, sid):
    ti = data.get("tool_input") or {}
    path = ti.get("file_path")
    if not isinstance(path, str) or not os.path.isabs(path):
        return
    try:
        st = os.stat(path)
    except OSError:
        return
    reads = eco_lib.load_reads(sid)
    reads["read"][eco_lib.read_key(ti, st)] = time.time()
    eco_lib.save_reads(sid, reads)


# ---- MCP: cut large results (E5 i) ----------------------------------------------

HEAD_CHARS = 6000
TAIL_CHARS = 2000


def _texts(resp):
    """The text of an MCP result, whatever shape the hook input carries."""
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict) and isinstance(resp.get("content"), list):
        resp = resp["content"]
    if isinstance(resp, list):
        parts = []
        for block in resp:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return None


def _reshape(resp, summary):
    """`summary` in the shape the tool returned: text blocks replaced by one
    block, non-text blocks (images) kept."""
    if isinstance(resp, str):
        return summary
    if isinstance(resp, dict) and isinstance(resp.get("content"), list):
        out = dict(resp)
        out["content"] = _reshape(resp["content"], summary)
        return out
    others = [b for b in resp if not (isinstance(b, str) or (isinstance(b, dict) and b.get("type") == "text"))]
    return [{"type": "text", "text": summary}] + others


def on_mcp_done(data, sid):
    resp = data.get("tool_response")
    text = _texts(resp)
    limit = int(eco_lib.read_config().get("mcpMaxChars") or eco_lib.MCP_MAX_CHARS)
    if not text or len(text) <= limit:
        return
    d = eco_lib.session_dir(sid)
    raw_dir = os.path.join(d, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    tool = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(data.get("tool_name") or "mcp"))[:80]
    path = os.path.join(raw_dir, "%s-%s-%s.txt" % (time.strftime("%Y%m%dT%H%M%S"), tool, os.urandom(3).hex()))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    head, tail = text[:HEAD_CHARS], text[-TAIL_CHARS:]
    cut = len(text) - len(head) - len(tail)
    summary = ("%s\n\n[… cs-eco: %s of %s characters cut from the middle. Full output: %s — "
               "Read it with offset/limit or Grep it for the part you need …]\n\n%s") % (
        head, "{:,}".format(cut), "{:,}".format(len(text)), path, tail)
    raw_bytes = len(text.encode("utf-8", "replace"))
    eco_lib.write_row(sid, data.get("cwd") or os.getcwd(), "cs-eco/mcp", raw_bytes,
                      len(summary.encode("utf-8", "replace")))
    emit({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "updatedMCPToolOutput": _reshape(resp, summary),
    }})


# ---- Session ---------------------------------------------------------------------

def on_session_start(data, sid):
    source = data.get("source")
    if source in ("compact", "clear"):
        eco_lib.reset_context(sid)
    d = eco_lib.session_dir(sid)
    marker = os.path.join(d, "register")
    if os.path.exists(marker):
        return  # resume: the register is still in the transcript
    os.makedirs(d, exist_ok=True)
    with open(marker, "w") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + "\n")
    emit({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": eco_lib.REGISTER,
    }})


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        sid = data.get("session_id")
        if not eco_lib.safe_sid(sid):
            return
        event = data.get("hook_event_name")
        if event == "PreCompact":
            eco_lib.reset_context(sid)  # whether on or off: stale memory only misleads
            return
        if not eco_lib.is_on(sid):
            return
        handle(data, sid)
    except Exception:
        return


def handle(data, sid):
    """Route one hook input of a session with eco on. `eco_run.py` calls this
    after its own on/off check; it may raise — the caller fails open."""
    event = data.get("hook_event_name")
    tool = data.get("tool_name") or ""
    if event == "PreToolUse":
        if tool == "Bash":
            on_bash(data, sid)
        elif tool == "Read":
            on_read(data, sid)
    elif event == "PostToolUse":
        if tool == "Read":
            on_read_done(data, sid)
        elif tool.startswith("mcp__"):
            on_mcp_done(data, sid)
    elif event == "SessionStart":
        on_session_start(data, sid)


if __name__ == "__main__":
    main()
