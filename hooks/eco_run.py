#!/usr/bin/env python3
"""cs-eco hook entry, registered in `hooks.json` for every eco event.

Deliberately tiny: it runs on every Bash and Read call of every session that
loads the plugin, and Python recompiles the script it starts on every run. The
on/off check uses `eco_lib`; the work is in `eco_hook`, imported (and so
bytecode-cached) only when eco is on. Fails open: any error, no output.
"""
import json
import os
import sys


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import eco_lib
        sid = data.get("session_id")
        if not eco_lib.safe_sid(sid):
            return
        if data.get("hook_event_name") == "PreCompact":
            eco_lib.reset_context(sid)  # whether on or off: stale memory only misleads
            return
        if not eco_lib.is_on(sid):
            return
        import eco_hook
        eco_hook.handle(data, sid)
    except Exception:
        return


if __name__ == "__main__":
    main()
