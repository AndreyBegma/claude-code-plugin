#!/usr/bin/env python3
"""Record the bypass-permissions acceptance the way Claude Code records it.

A worker starts with `--permission-mode bypassPermissions`, and the first time
a configuration has never accepted that mode Claude Code raises:

    WARNING: Claude Code running in Bypass Permissions mode
    In Bypass Permissions mode, Claude Code will not ask for your approval
    before running potentially dangerous commands.
    ...
    > No, exit
      Yes, I accept

A session started unattended has nobody to press Down + Enter for it, and the
failure is invisible from the launcher: `dispatch.sh` exits 0, the tmux session
is live, and `watch.sh` reported `IDLE` — the same picture as a worker thinking.
That is how the 2026-09-03 round lost its first slot (BUG-20260903-001).

## Where it is written, and why not the obvious place

`<worktree>/.claude/settings.local.json` — Claude Code's `localSettings` layer,
inside the worker's own worktree, gone when the worktree is removed.

The first version of this script wrote the person's **user** settings, which is
what Claude Code itself writes when somebody accepts the dialog. That is too
broad, and the orchestrator was right to send it back: `skipDangerousMode
PermissionPrompt` in user settings turns the confirmation off for *every* Claude
Code session on the machine, not only for `cs-*` workers. On a machine where the
key is already set that write is a no-op, which is precisely what makes it
dangerous — the first machine where it is not a no-op is one nobody is watching,
and it will be quiet there too. A setting that exists to serve one dispatched
session should not outlive it.

`localSettings` gives that lifetime and is in the gate's list. `projectSettings`
(`.claude/settings.json`) — the committed settings of the repository, and
the obvious place to look — is **not** in the list, so
it cannot suppress this dialog. The list is exact; see below.

## The key, and how it was found

`skipDangerousModePermissionPrompt`, in a **settings** file, not in
`.claude.json`. Read off Claude Code 2.1.259 rather than guessed:

- its own schema description is *"Whether the user has accepted the bypass
  permissions mode dialog"*;
- accepting the dialog runs
  `nn("userSettings", {skipDangerousModePermissionPrompt: true})` — the app
  writes the same file this script writes;
- the gate is `i$()`, and it is one expression:

      !!(Se("userSettings")?.skipDangerousModePermissionPrompt
      || Se("localSettings")?.skipDangerousModePermissionPrompt
      || Se("flagSettings")?.skipDangerousModePermissionPrompt
      || Se("policySettings")?.skipDangerousModePermissionPrompt)

  Four layers, and `projectSettings` is not one of them.

Corroborated on this machine: the profile's `settings.json` carries the key with
an mtime matching the minute the orchestrator hand-accepted the dialog, and
`~/.claude/settings.json` — a config directory that never saw it — does not.

And confirmed by dispatch rather than by reading: a throwaway worker launched
with the key present *only* in its worktree's `settings.local.json`, and absent
from the user settings it was pointed at, reached its prompt with no dialog.

Usage:

    python3 accept_dangerous_mode.py <worktree-path> [settings-path]

`settings-path` defaults to `claude_config.local_settings_path(<worktree>)` and
is only ever overridden by tests.

## Why this one creates the file and `pretrust_worktree.py` does not

Pre-trusting skips silently when there is no config file, on the grounds that a
machine with none has never run Claude Code. That reasoning does not carry here
at all: a fresh worktree never has a `settings.local.json`, so skipping when it
is absent would mean never writing it. The file and its directory are created.

Every other key keeps its value, and the file's mode is preserved; a created one
gets 0644, which is what Claude Code's own settings files carry. A file that
does not parse is left completely alone and the script fails loudly instead —
overwriting a settings file nobody could read would be worse than the dialog.
Writing into the worktree makes that last case cheap rather than alarming: the
file it declines to touch is one this dispatch created, not the person's.
"""
import json
import os
import stat
import sys
import tempfile

import claude_config

KEY = "skipDangerousModePermissionPrompt"
CREATED_MODE = 0o644


def accept(settings_path):
    """Set `KEY` true in `settings_path`. Returns True when the file was written.

    Already-true is a no-op — which matters less now the target is per-worktree
    than it did when this wrote a shared file, but a re-dispatch into an existing
    worktree still reaches it, and not rewriting is still the right answer.
    """
    data = {}
    mode = CREATED_MODE

    if os.path.isfile(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except ValueError as exc:
                raise ValueError(
                    "%s is not valid JSON (%s) — refusing to overwrite it"
                    % (settings_path, exc)
                )
        if not isinstance(data, dict):
            raise ValueError(
                "%s does not hold a JSON object — refusing to overwrite it"
                % settings_path
            )
        mode = stat.S_IMODE(os.stat(settings_path).st_mode)
        if data.get(KEY) is True:
            return False

    data[KEY] = True

    dirpath = os.path.dirname(settings_path) or "."
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".settings.json.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.chmod(tmp_path, mode)
        os.rename(tmp_path, settings_path)
    except BaseException:
        os.unlink(tmp_path)
        raise
    return True


def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        print(
            "usage: accept_dangerous_mode.py <worktree-path> [settings-path]",
            file=sys.stderr,
        )
        return 2

    worktree = argv[1]
    settings_path = (
        argv[2] if len(argv) > 2 else claude_config.local_settings_path(worktree)
    )
    if accept(settings_path):
        print("recorded %s in %s" % (KEY, settings_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
