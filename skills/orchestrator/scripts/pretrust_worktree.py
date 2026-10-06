#!/usr/bin/env python3
"""Pre-trust a worker's worktree the way Claude Code itself records trust.

`claude --remote-control` raises a first-launch "Do you trust the files in
this folder?" prompt for any project path it has never seen, and a session
started unattended has nobody to press Enter for it. Claude Code records
trust per absolute project path, under `projects.<abs path>
.hasTrustDialogAccepted` in its config file. An older
worktree may have inherited trust already; a new one
is a path Claude Code has never seen, and it sits on the prompt until a
person notices and presses Down + Enter (BUG-20260902-003). `dispatch.sh`
calls this before starting the session so the prompt never appears.

## Two keys, not one (BUG-20260903-002)

Writing only the worktree's own path is what kept the *fourth* launch dialog
alive on a fresh `CLAUDE_CONFIG_DIR`:

    Quick safety check: Is this a project you created or one you trust?
    ⚠ This folder pre-approves 1 tool permission in .claude/settings.json:
      Bash(gh pr merge:*)
    ❯ No, continue without these permissions
      Yes, I trust this folder

Claude Code has two trust checks and they read different keys — see
`claude_config.canonical_git_root` for the full reading. The short version:

- the **loose** check takes either the canonical git root or a walk up from
  the session's cwd, so `projects[<worktree path>]` satisfies it;
- the **strict** one — which decides whether the project's
  `permissions.allow` rules apply, and whether that disclosure backstop is
  offered — takes `projects[<canonical git root>]` and only that.

For a linked worktree the canonical git root is the **main checkout**. So the
worktree key alone left the strict check false, the repository's own
`permissions.allow` entry raised the backstop, and the dialog appeared *with
the cancel label Claude Code only renders when trust is accepted* — which is
exactly how the pane was reported, and why `hasTrustDialogAccepted: true`
looked like it did not work.

Both keys are written. The worktree key is not redundant: it is what the loose
check's walk reads, it is the only one that exists for a plain non-git
directory, and it is what a repository with no committed settings has always
relied on. The root key is added, never substituted.

Usage:

    python3 pretrust_worktree.py <absolute-worktree-path> [claude-json-path]

`claude-json-path` defaults to whatever `claude_config.claude_json_path()`
resolves — `$CLAUDE_CONFIG_DIR/.claude.json` when that variable is set,
`~/.claude.json` otherwise — and is only ever overridden by tests, which point
it at a fixture. It used to be a hardcoded `~/.claude.json`, which on a machine
with `CLAUDE_CONFIG_DIR` set is a file Claude Code never reads, so the trust
landed nowhere and the prompt was one changed environment variable away from
appearing on every dispatch (BUG-20260903-001).

Skips silently (exit 0) if the target file does not exist — a machine with no
config file has never run Claude Code, and inventing the file is not this
script's job.
"""
import json
import os
import stat
import sys
import tempfile

import claude_config


def trust_keys(path):
    """Every `projects.<key>` this path needs trusted, worktree key first.

    One key for a directory git knows nothing about; two for a worktree, the
    second being the repository's canonical root. Deduplicated, because in the
    main checkout of a repository the two are the same path.
    """
    keys = [path]
    root = claude_config.canonical_git_root(path)
    if root is not None and root not in keys:
        keys.append(root)
    return keys


def pretrust(path, claude_json):
    if not os.path.isfile(claude_json):
        return

    with open(claude_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    projects = data.setdefault("projects", {})
    for key in trust_keys(path):
        entry = projects.setdefault(key, {})
        entry["hasTrustDialogAccepted"] = True

    mode = stat.S_IMODE(os.stat(claude_json).st_mode)
    dirpath = os.path.dirname(claude_json) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".claude.json.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.chmod(tmp_path, mode)
        os.rename(tmp_path, claude_json)
    except BaseException:
        os.unlink(tmp_path)
        raise


def main(argv):
    if len(argv) < 2:
        print(
            "usage: pretrust_worktree.py <absolute-worktree-path> [claude-json-path]",
            file=sys.stderr,
        )
        return 2

    path = argv[1]
    claude_json = argv[2] if len(argv) > 2 else claude_config.claude_json_path()
    pretrust(path, claude_json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
