#!/usr/bin/env python3
"""The command line behind /cs-eco.

  eco_ctl.py on|off      --session <id>   this session (takes effect on the next tool call)
  eco_ctl.py default on|off               new sessions on this machine
  eco_ctl.py status      --session <id>
  eco_ctl.py stats       --session <id> [--all]
  eco_ctl.py statusline                   reads Claude Code's statusline JSON on stdin
  eco_ctl.py snippet                      the statusLine settings snippet to paste

The skill passes `${CLAUDE_SESSION_ID}`, which Claude Code substitutes into the
skill's text before the model sees it. A literal `${…}` or an empty value means
the substitution did not happen, and the session commands refuse to guess.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import eco_lib  # noqa: E402


def _session(args):
    sid = None
    if "--session" in args:
        i = args.index("--session")
        sid = args[i + 1] if i + 1 < len(args) else None
    if not sid or "${" in sid or not eco_lib.safe_sid(sid):
        raise SystemExit("cs-eco: no session id — Claude Code did not substitute ${CLAUDE_SESSION_ID} "
                         "into the skill (needs a recent Claude Code). Nothing changed.")
    return sid


def runner_state():
    """("unavailable", None) | ("owned", None) | ("available", version)."""
    if os.environ.get("AGENTDOCK_FILTER_STATS"):
        return "owned", None
    import eco_hook
    path = eco_hook.find_runner()
    if not path:
        return "unavailable", None
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5).stdout
        version = out.split()[0] if out.split() else "?"
    except Exception:
        version = "?"
    return "available", version


def _older(version, than):
    try:
        a = [int(x) for x in version.split("-")[0].split(".")[:3]]
        b = [int(x) for x in than.split(".")]
        return a < b
    except Exception:
        return False


def status_lines(sid):
    on, source = eco_lib.resolve(sid)
    where = {"session": "set for this session", "env": "CS_ECO in the environment",
             "default": "machine default", "none": "default off"}[source]
    lines = ["eco: %s (%s)" % ("on" if on else "off", where)]
    state, version = runner_state()
    if state == "unavailable":
        lines.append("command filter: unavailable (agentdock-runner not installed)")
    elif state == "owned":
        lines.append("command filter: handled by the AgentDock launch of this session")
    else:
        note = ""
        if _older(version, "0.12.1"):
            note = " — auto mode needs agentdock-runner ≥ 0.12.1; this one rewrites in bypassPermissions only"
        lines.append("command filter: agentdock-runner %s, rewrites in bypassPermissions and auto only%s"
                     % (version, note))
    lines.append("read guard (> %d lines) and read dedup: %s" % (eco_lib.GUARD_LINES, "on" if on else "off"))
    limit = int(eco_lib.read_config().get("mcpMaxChars") or eco_lib.MCP_MAX_CHARS)
    lines.append("MCP output cut above %s characters: %s" % ("{:,}".format(limit), "on" if on else "off"))
    lines.append("scout agent (haiku): available as `code-sentinel:scout`")
    pct = os.environ.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
    if pct:
        lines.append("early compaction: on at %s%% (CLAUDE_AUTOCOMPACT_PCT_OVERRIDE)" % pct)
    else:
        lines.append("early compaction: off — it is read at launch: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70 claude")
    default = eco_lib.read_config().get("default") or "off"
    lines.append("default for new sessions: %s" % default)
    return lines


def stats_lines(sid, everything):
    paths = eco_lib.all_stats_files() if everything else [eco_lib.stats_file(sid)]
    total, by_filter = eco_lib.summarize(paths)
    scope = "all sessions" if everything else "this session"
    if not total["rows"]:
        return ["cs-eco stats (%s): nothing recorded yet." % scope]
    lines = ["cs-eco stats (%s): saved %s bytes ≈ %s tokens (%s → %s bytes)" % (
        scope, eco_lib.human(total["saved"]), eco_lib.human(eco_lib.tokens(total["saved"])),
        eco_lib.human(total["raw"]), eco_lib.human(total["kept"]))]
    lines.append("  rows: %d filtered, %d bypassed, %d commands left alone" % (
        total["filtered"], total["bypassed"], total["passedThrough"]))
    for fid, agg in sorted(by_filter.items(), key=lambda kv: -kv[1]["saved"]):
        lines.append("  %-28s %4d × · saved ≈ %s tokens" % (fid, agg["count"],
                                                            eco_lib.human(eco_lib.tokens(agg["saved"]))))
    lines.append("  rows: %s" % (os.path.join(eco_lib.state_dir(), "sessions", "*", "filter-stats.jsonl")
                                  if everything else paths[0]))
    return lines


def statusline(stdin_text):
    try:
        data = json.loads(stdin_text or "{}")
    except Exception:
        data = {}
    sid = data.get("session_id")
    on = eco_lib.is_on(sid) if eco_lib.safe_sid(sid) else False
    parts = ["eco " + ("on" if on else "off")]
    f = eco_lib.stats_file(sid) if eco_lib.safe_sid(sid) else None
    if f:
        total, _ = eco_lib.summarize([f])
        if total["rows"]:
            parts.append("saved ≈%s tok" % eco_lib.human(eco_lib.tokens(total["saved"])))
    used = (data.get("context_window") or {}).get("used_percentage")
    if isinstance(used, (int, float)):
        parts.append("ctx %d%%" % round(used))
    return " · ".join(parts)


def snippet():
    script = os.path.join(HERE, "eco-statusline.sh")
    return json.dumps({"statusLine": {"type": "command", "command": script}}, indent=2)


def main(argv):
    if not argv:
        argv = ["on"]
    cmd, rest = argv[0], argv[1:]
    if cmd in ("on", "off"):
        sid = _session(rest)
        eco_lib.set_session_mode(sid, cmd)
        print("\n".join(status_lines(sid)))
        if cmd == "on":
            d = eco_lib.session_dir(sid)
            marker = os.path.join(d, "register")
            if not os.path.exists(marker):
                with open(marker, "w") as f:
                    f.write("ctl\n")
                print()
                print(eco_lib.REGISTER)
        return 0
    if cmd == "default":
        value = rest[0] if rest and rest[0] in ("on", "off") else None
        if not value:
            raise SystemExit("cs-eco: usage: default on|off")
        cfg = eco_lib.read_config()
        cfg["default"] = value
        eco_lib.write_config(cfg)
        print("cs-eco: new sessions start with eco %s (%s)" % (value, eco_lib.config_path()))
        return 0
    if cmd == "status":
        print("\n".join(status_lines(_session(rest))))
        return 0
    if cmd == "stats":
        sid = _session(rest)
        print("\n".join(stats_lines(sid, "--all" in rest)))
        return 0
    if cmd == "statusline":
        print(statusline(sys.stdin.read()))
        return 0
    if cmd == "snippet":
        print(snippet())
        return 0
    raise SystemExit("cs-eco: unknown command %r — on, off, default on|off, status, stats, snippet" % cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
