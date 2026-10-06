#!/usr/bin/env python3
"""Resolve the Claude Code configuration paths a dispatch pre-flight writes to.

One place, read by `dispatch.sh`, `pretrust_worktree.py` and
`accept_dangerous_mode.py`, so the fallback is not written down three times and
wrong in one of them (BUG-20260903-001).

A machine may set `CLAUDE_CONFIG_DIR` to a profile directory,
and until this existed `pretrust_worktree.py` hardcoded `~/.claude.json` — so
`BUG-20260902-003`'s fix was landing in a file this machine's Claude Code does
not read. Nothing noticed, because the older worktree paths were already
trusted in the file that *is* read.

## The asymmetry, which is the whole reason to have this file

The two paths do not both live under the config directory, and assuming they do
is the mistake this module exists to stop. Read off Claude Code 2.1.259 itself
rather than inferred:

    be()  = CLAUDE_CONFIG_DIR ?? join(homedir(), ".claude")
    json  = join(process.env.CLAUDE_CONFIG_DIR || homedir(), ".claude.json")

So with `CLAUDE_CONFIG_DIR` set both sit under it, but with it unset the
settings file is `~/.claude/settings.json` while the config file is
`~/.claude.json` — *not* `~/.claude/.claude.json`. Confirmed on disk on this
machine: `~/.claude.json` exists and `~/.claude/.claude.json` does not.

Two smaller points, both deliberate:

- The app resolves the *directory* with `??`, so `CLAUDE_CONFIG_DIR=""` would
  give it the empty string. Here an empty value counts as unset, which is what
  `BUG-20260903-001` specifies and what the app's own `||` already does for the
  `.claude.json` path.
- The real filename carries an OAuth-environment suffix — `.claude-staging-oauth
  .json`, `.claude-local-oauth.json` — which is empty on prod. A launcher has no
  business reimplementing that, so this resolves the prod name only.

Usage as a library:

    import claude_config
    claude_config.claude_json_path()
    claude_config.settings_path()

and from a shell, one path per invocation:

    python3 claude_config.py --config-dir
    python3 claude_config.py --claude-json
    python3 claude_config.py --settings
    python3 claude_config.py --canonical-git-root <path>

Every function takes an optional `env` mapping so the tests can drive it with a
fixture instead of mutating the process environment.

## The third path: which *key* inside `.claude.json` (BUG-20260903-002)

Resolving the file was only half of it. Trust is recorded under
`projects.<path>`, and Claude Code reads two different `<path>`es depending on
what it is deciding — which is why `hasTrustDialogAccepted` written for a
worktree suppressed one dialog and not the other:

- the **loose** check (`Jo()`, "should the trust dialog appear at all") accepts
  either `projects[canonical git root]` or a walk up from the session's cwd,
  bounded by that directory's own git top level. For a linked worktree the walk
  therefore matches `projects[<worktree path>]`.
- the **strict** check (`Ld()`, "persisted trust" — whether the project's
  `permissions.allow` rules apply, and whether the permission-disclosure
  backstop is offered) reads `projects[canonical git root]` and nothing else.
  No walk.

And **the canonical git root of a linked worktree is the main checkout**, not
the worktree. Claude Code says so in its own `/cd` copy: *"This directory is
part of the repository at … Trusting it trusts that whole repository, including
its other worktrees and subdirectories."*

So a dispatch that records trust only for `<worktree>` passes the
loose check and fails the strict one, and the worker stops on the
permission-disclosure variant of the trust dialog — with its cancel label
reading *"No, continue without these permissions"*, which is the label Claude
Code only renders when trust **is** accepted. That combination is the
fingerprint of this bug.

`canonical_git_root` resolves the strict key, so `pretrust_worktree.py` can
write both and neither script has to know how a worktree is laid out.
"""
import os
import subprocess
import sys

DEFAULT_DIR_NAME = ".claude"
GIT_DIR_NAME = ".git"
CLAUDE_JSON_NAME = ".claude.json"
SETTINGS_NAME = "settings.json"
LOCAL_SETTINGS_RELPATH = os.path.join(".claude", "settings.local.json")


def _env(env):
    return os.environ if env is None else env


def _home(env):
    # `expanduser` reads HOME too; going through the mapping is what lets a
    # test pass a fixture HOME without touching the process environment.
    return _env(env).get("HOME") or os.path.expanduser("~")


def _configured_dir(env):
    """`CLAUDE_CONFIG_DIR` when set and non-empty, otherwise None."""
    return _env(env).get("CLAUDE_CONFIG_DIR") or None


def config_dir(env=None):
    """Where Claude Code keeps settings.json, projects/, sessions/ and the rest."""
    return _configured_dir(env) or os.path.join(_home(env), DEFAULT_DIR_NAME)


def claude_json_path(env=None):
    """The config file carrying `projects.<abs path>.hasTrustDialogAccepted`.

    Note the fallback: the home directory, not `config_dir()`. See the module
    docstring — this is the asymmetry.
    """
    return os.path.join(_configured_dir(env) or _home(env), CLAUDE_JSON_NAME)


def settings_path(env=None):
    """The user settings file — Claude Code's `userSettings` layer.

    Machine-wide: it applies to every Claude Code session this person runs, not
    only to a dispatched worker. That breadth is why the bypass-permissions
    acceptance is *not* written here — see `local_settings_path` and
    `accept_dangerous_mode.py`.
    """
    return os.path.join(config_dir(env), SETTINGS_NAME)


def local_settings_path(project_dir):
    """Claude Code's `localSettings` layer for one project directory.

    `<project>/.claude/settings.local.json`, resolved against the session's cwd
    — `bdr("localSettings", …)` returns `cwd` as its root — so for a worker
    started with `tmux -c "$WT"` this is a file inside its own worktree, and it
    dies when the worktree is removed.

    That lifetime is the point. It is the narrowest layer the bypass-permissions
    gate consults, and the gate's list is exact: `userSettings || localSettings
    || flagSettings || policySettings`. Note which one is missing —
    `projectSettings` (`.claude/settings.json`) is **not** consulted, so seeding
    a repository's committed `.claude/settings.json` cannot
    suppress that dialog, however reasonable a place it looks.
    """
    return os.path.join(project_dir, LOCAL_SETTINGS_RELPATH)


GIT_TIMEOUT_SECONDS = 5


def canonical_git_root(path):
    """The repository root Claude Code keys persisted trust on, or None.

    For a linked worktree this is the **main checkout**, which is the whole
    point: `git rev-parse --git-common-dir` is shared by every worktree of a
    repository, so its parent is the one path all of them canonicalise to.

        ~/dev/.wt-myrepo-i42
          --git-dir         ~/dev/myrepo/.git/worktrees/.wt-myrepo-i42
          --git-common-dir  ~/dev/myrepo/.git      ->  ~/dev/myrepo

    `--path-format=absolute` is not optional. Without it git prints the common
    directory relative to the *caller's* cwd, which is a different string in
    every session that asks — the same trap `dispatch.sh` documents for its
    `info/exclude` path.

    Returns None, never raises, when there is no answer to give: `path` is not
    in a repository, `git` is not installed or is too old for
    `--path-format` (2.31, 2021), the call times out, or the common directory
    is not a `.git` whose parent is a working tree — a bare repository has no
    worktree to dispatch into, so there is nothing to pre-trust. A None here
    costs the caller the strict key and nothing else; it must not cost it the
    worktree key, and it must not stop a dispatch.
    """
    common = _git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common is None:
        return None

    common = common.rstrip("/")
    if os.path.basename(common) != GIT_DIR_NAME:
        # Not a `<root>/.git` layout — a bare repository, or `GIT_DIR` pointed
        # somewhere unusual. Fall back to asking git for the working tree.
        top = _git(path, "rev-parse", "--show-toplevel")
        return os.path.realpath(top) if top else None

    return os.path.realpath(os.path.dirname(common))


def _git(path, *args):
    """`git -C <path> <args>` -> stripped stdout, or None if it did not answer."""
    try:
        done = subprocess.run(
            ("git", "-C", path) + args,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if done.returncode != 0:
        return None
    out = done.stdout.strip()
    return out or None


_WHAT = {
    "--config-dir": config_dir,
    "--claude-json": claude_json_path,
    "--settings": settings_path,
}

_WHAT_WITH_PATH = {
    "--canonical-git-root": canonical_git_root,
}


def _usage():
    return "usage: claude_config.py {%s} | claude_config.py {%s} <path>" % (
        "|".join(sorted(_WHAT)),
        "|".join(sorted(_WHAT_WITH_PATH)),
    )


def main(argv):
    if len(argv) == 3 and argv[1] in _WHAT_WITH_PATH:
        answer = _WHAT_WITH_PATH[argv[1]](argv[2])
        if answer is None:
            print("claude_config: no git root for %s" % argv[2], file=sys.stderr)
            return 1
        print(answer)
        return 0

    if len(argv) != 2 or argv[1] not in _WHAT:
        print(_usage(), file=sys.stderr)
        return 2

    print(_WHAT[argv[1]]())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
