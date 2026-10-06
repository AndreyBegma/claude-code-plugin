#!/usr/bin/env python3
"""PreToolUse guard: refuse process signals by name or pattern, in every session.

`pkill -f 'node dist/src/main'` stops every process whose command line matches —
including other projects' servers and containers running as the same user.
That happened while testing `cs-feature` (2026-10-06): six unrelated API
containers were restarted. A rule in a skill's text is not enough; this hook is
the mechanical version of it.

Refused: `pkill`, `killall`, and `kill` with anything but literal numeric PIDs
(`kill $(pgrep …)`, `kill %1`, `kill $PID`) — through `;` `&&` `|`, `$( )` and
`sh -c`. Allowed: `kill 12345`, `kill -TERM 12345 12346`. Start a process with
`cmd & echo $!`, note the PID, stop it with that number.

The parsing is `fence.py`'s, reused rather than reimplemented. Any internal
error allows the call: a guard that breaks every `Bash` call is a guard someone
turns off.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "orchestrator", "scripts"))


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") != "Bash":
            return
        command = (data.get("tool_input") or {}).get("command") or ""
        if not any(w in command for w in ("kill",)):
            return
        import fence  # noqa: E402

        for cmd in fence.scan(command):
            reason = fence.signal_violation(cmd)
            if reason:
                reason = reason.replace("the fence", "the kill guard").replace("The fence", "The kill guard")
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }))
                return
    except Exception:
        return


if __name__ == "__main__":
    main()
