"""cs-eco state, shared by `eco_hook.py` (the hooks) and `eco_ctl.py` (/cs-eco).

Everything lives in two places and nowhere else:

  ${XDG_STATE_HOME:-~/.local/state}/cs-eco/sessions/<session id>/
      mode               "on" or "off" — set by /cs-eco for this session
      reads.json        what the session has read, and the pending soft denials
      register          marker: the working register is in context
      project           cached project id for the stats rows
      filter-stats.jsonl one JSON row per saving (AgentDock `filter.stats` shape)
      raw/               full outputs that were cut (the runner's and ours)
  ${XDG_CONFIG_HOME:-~/.config}/cs-eco/config.json
      {"default": "on" | "off", "mcpMaxChars": 16000}

Whether eco is on for a session: the session's own `mode` file, else
`CS_ECO=on|off` in the environment (the fleet sets it), else the machine
default, else off. Every hook asks this first and does nothing when it is off.

Hot path: imported by a hook on every Bash and Read call of every session that
loads the plugin, so it imports only `json`, `os` and `time` at module level.
"""
import json
import os
import time

ON_WORDS = ("on", "1", "true", "yes")
OFF_WORDS = ("off", "0", "false", "no")

MCP_MAX_CHARS = 16000
GUARD_LINES = 400
# TODO(AgentDock card "manual run kind for filter.stats", E7): switch to "manual"
# once the runner accepts it — it rejects any kind outside its list today, and
# then filters nothing. CS_ECO_RUN_KIND overrides this until then.
RUN_KIND = "skill"


def _home():
    return os.path.expanduser("~")


def state_dir(env=None):
    env = os.environ if env is None else env
    base = env.get("XDG_STATE_HOME") or os.path.join(_home(), ".local", "state")
    return os.path.join(base, "cs-eco")


def config_path(env=None):
    env = os.environ if env is None else env
    base = env.get("XDG_CONFIG_HOME") or os.path.join(_home(), ".config")
    return os.path.join(base, "cs-eco", "config.json")


def safe_sid(sid):
    sid = "".join(c for c in str(sid or "") if c.isalnum() or c in "-_")
    return sid[:128]


def session_dir(sid, env=None):
    sid = safe_sid(sid)
    if not sid:
        return None
    return os.path.join(state_dir(env), "sessions", sid)


def read_config(env=None):
    try:
        with open(config_path(env)) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_config(data, env=None):
    path = config_path(env)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _atomic_write(path, json.dumps(data, indent=2) + "\n")


def _word(value):
    value = str(value or "").strip().lower()
    if value in ON_WORDS:
        return "on"
    if value in OFF_WORDS:
        return "off"
    return None


def session_mode(sid, env=None):
    d = session_dir(sid, env)
    if not d:
        return None
    try:
        with open(os.path.join(d, "mode")) as f:
            return _word(f.read())
    except Exception:
        return None


def resolve(sid, env=None):
    """(on, source): source is "session", "env", "default" or "none"."""
    env = os.environ if env is None else env
    mode = session_mode(sid, env)
    if mode:
        return mode == "on", "session"
    mode = _word(env.get("CS_ECO"))
    if mode:
        return mode == "on", "env"
    mode = _word(read_config(env).get("default"))
    if mode:
        return mode == "on", "default"
    return False, "none"


def is_on(sid, env=None):
    return resolve(sid, env)[0]


def set_session_mode(sid, mode, env=None):
    d = session_dir(sid, env)
    if not d:
        raise ValueError("no session id")
    os.makedirs(d, exist_ok=True)
    _atomic_write(os.path.join(d, "mode"), mode + "\n")


def _atomic_write(path, text):
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


# ---- read memory (E6) ---------------------------------------------------------

def load_reads(sid, env=None):
    d = session_dir(sid, env)
    try:
        with open(os.path.join(d, "reads.json")) as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("read", {})
            data.setdefault("denied", {})
            return data
    except Exception:
        pass
    return {"read": {}, "denied": {}}


def save_reads(sid, data, env=None):
    d = session_dir(sid, env)
    os.makedirs(d, exist_ok=True)
    _atomic_write(os.path.join(d, "reads.json"), json.dumps(data))


def reset_context(sid, env=None):
    """Compaction or /clear: nothing the session read is in context any more,
    and the working register is gone with it."""
    d = session_dir(sid, env)
    if not d:
        return
    for name in ("reads.json", "register"):
        try:
            os.remove(os.path.join(d, name))
        except OSError:
            pass


def read_key(tool_input, st):
    ti = tool_input or {}
    return "|".join(str(x) for x in (
        ti.get("file_path"), ti.get("offset"), ti.get("limit"), ti.get("pages"),
        st.st_mtime_ns, st.st_size))


# ---- stats (E7) -----------------------------------------------------------------

def stats_file(sid, env=None):
    d = session_dir(sid, env)
    return os.path.join(d, "filter-stats.jsonl") if d else None


def project_id(sid, cwd, env=None):
    """owner/name of the origin remote, else the directory name. Cached per
    session: the remote does not change under a running session."""
    d = session_dir(sid, env)
    cache = os.path.join(d, "project") if d else None
    if cache:
        try:
            with open(cache) as f:
                value = f.read().strip()
            if value:
                return value
        except OSError:
            pass
    value = ""
    try:
        import subprocess
        url = subprocess.run(["git", "-C", cwd or ".", "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=2).stdout.strip()
        url = url[:-4] if url.endswith(".git") else url
        parts = url.replace(":", "/").rstrip("/").split("/")
        if len(parts) >= 2 and parts[-1] and parts[-2]:
            value = parts[-2] + "/" + parts[-1]
    except Exception:
        pass
    if not value:
        value = os.path.basename(os.path.abspath(cwd or ".")) or "unknown"
    if cache:
        try:
            os.makedirs(d, exist_ok=True)
            _atomic_write(cache, value + "\n")
        except OSError:
            pass
    return value


def run_kind(env=None):
    env = os.environ if env is None else env
    return env.get("CS_ECO_RUN_KIND") or RUN_KIND


def filter_env(sid, cwd, env=None):
    """The AGENTDOCK_FILTER_* environment that makes `agentdock-runner filter`
    write its rows into this session's stats file."""
    return {
        "AGENTDOCK_FILTER_STATS": stats_file(sid, env),
        "AGENTDOCK_FILTER_PROJECT": project_id(sid, cwd, env),
        "AGENTDOCK_FILTER_RUN": safe_sid(sid),
        "AGENTDOCK_FILTER_RUN_KIND": run_kind(env),
    }


def write_row(sid, cwd, filter_id, raw_bytes, kept_bytes, bypassed=False, env=None, now=None):
    """One row in the runner's `filter-stats.jsonl` shape. Net saving of a file
    is sum(rawBytes - keptBytes) over its rows; a soft denial that the session
    then overrides writes a correcting row, so the sum stays honest."""
    path = stats_file(sid, env)
    if not path:
        return
    now = time.time() if now is None else now
    row = {
        "projectId": project_id(sid, cwd, env),
        "row": {
            "id": "c_%s%s" % (format(int(now * 1000), "x"), os.urandom(4).hex()),
            "runId": safe_sid(sid),
            "runKind": run_kind(env),
            "filter": filter_id,
            "rawBytes": int(raw_bytes),
            "keptBytes": int(kept_bytes),
            "bypassed": bool(bypassed),
            "passedThrough": False,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + ".%03dZ" % int((now % 1) * 1000),
        },
    }
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as f:
            f.write(json.dumps(row) + "\n")
    except OSError:
        pass


def summarize(paths):
    """Aggregate stats rows: totals and per-filter numbers."""
    total = {"rows": 0, "filtered": 0, "passedThrough": 0, "bypassed": 0, "raw": 0, "kept": 0}
    by_filter = {}
    for path in paths:
        try:
            f = open(path)
        except OSError:
            continue
        with f:
            for line in f:
                try:
                    row = json.loads(line)["row"]
                except Exception:
                    continue
                total["rows"] += 1
                if row.get("passedThrough"):
                    total["passedThrough"] += 1
                    continue
                if row.get("bypassed"):
                    total["bypassed"] += 1
                else:
                    total["filtered"] += 1
                raw, kept = int(row.get("rawBytes") or 0), int(row.get("keptBytes") or 0)
                total["raw"] += raw
                total["kept"] += kept
                fid = str(row.get("filter") or "?")
                agg = by_filter.setdefault(fid, {"count": 0, "saved": 0})
                agg["count"] += 1
                agg["saved"] += raw - kept
    total["saved"] = total["raw"] - total["kept"]
    return total, by_filter


def all_stats_files(env=None):
    root = os.path.join(state_dir(env), "sessions")
    try:
        names = os.listdir(root)
    except OSError:
        return []
    return [os.path.join(root, n, "filter-stats.jsonl") for n in sorted(names)]


def tokens(nbytes):
    """Bytes to an approximate token count (about four bytes per token)."""
    return int(round(nbytes / 4.0))


def human(n):
    n = int(n)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000:
        return "%s%.1fM" % (sign, n / 1e6)
    if n >= 1000:
        return "%s%.1fk" % (sign, n / 1e3)
    return "%s%d" % (sign, n)


REGISTER = """cs-eco is on for this session (token saver). Working register:
- Answer tersely. No preamble, no restating the request, no summary of what you are about to do; report results and decisions, not narration.
- Never paste back file contents or command output the person can see; quote only the lines that matter, with file:line.
- Read narrowly: Grep/Glob first, then Read with offset/limit on the part you need. A Read of a file over 400 lines without offset/limit is refused once with an outline; repeat the call only if you really need all of it.
- A repeated Read of an unchanged file range is refused once ("already in context") — use what you already have.
- Broad searches, many-file reads and "where is X used" questions go to the `code-sentinel:scout` subagent (haiku); you get its conclusion, not the file dumps.
- Commands in bypass/auto mode may run through `agentdock-runner filter`, which keeps the failures and drops the noise. If you need the raw output, prefix the command with AGENTDOCK_RAW=1.
- Large MCP tool results are cut to head and tail; the full text is saved and its path is shown — Read that file with offset/limit if you need more."""
