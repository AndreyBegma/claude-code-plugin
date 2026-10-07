#!/usr/bin/env python3
"""Resolve `orchestrator.specDir` to a place on disk, and read specs from it.

One place, called by `cs-orchestrator` (readiness, briefs) and `cs-spec`
(where a spec file lands), so the grammar is implemented once (#7, D8).

## Grammar (D1)

    null / ""                         kind "none"    — the issue body is the spec
    docs/specs                        kind "inside"  — relative to the main checkout
    ../denitsa-documentation/prs      kind "outside" — a path outside it (or absolute)
    github:<owner>/<repo>[/<subpath>] kind "github"
    https://github.com/<owner>/<repo>[/tree/<branch>/<subpath>]
                                      normalized to the `github:` form; the branch
                                      segment is reported as `ignoredBranch` and
                                      otherwise dropped — specs live on the default
                                      branch only

A path is classified by where it *resolves*, so `docs/../../x` is outside. Any
other value containing `:` is refused: non-GitHub forges are out of scope.

## Where the checkout is (D2)

A path resolves against the **main checkout** — the parent of
`git rev-parse --git-common-dir`, never a worktree — and its repository is the
git toplevel the path lies in. For `github:` an existing sibling clone at
`<parent of main checkout>/<repo>` is used when its *raw* `remote.origin.url`
(`git config --get`, so an `insteadOf` rewrite cannot disguise it) names the
same `owner/repo`. Otherwise the repository is cloned into
`<git-common-dir>/cs-orchestrator/specs/<owner>-<repo>/` — inside `.git`, never
committed, removable at any time.

## Which branch is read (D3)

Specs are read from `origin/<branch>` with `git show` after a fetch, never from
a working tree: a spec merged a minute ago counts, an unmerged local edit does
not. A failed fetch is an error, not a stale read. `<branch>` is the spec
repository's default branch — except for kind `inside`, where it is
`orchestrator.base` (falling back to the default branch): a docs pull request in
the code repository lands on the base like every other pull request, and a
repository whose base is not its default branch would otherwise never see one.

## The local copy a brief points at

`--read` writes the exact `origin/<branch>` content to
`<git-common-dir>/cs-orchestrator/specs/_read/<file>`, mode 0444, and reports
that path as `local`. A sibling clone's working tree may be behind or edited; a
worker handed that path could read the wrong text. (`_` cannot start a GitHub
owner name, so the directory never collides with a cache clone.)

## Usage

    python3 spec_dir.py --resolve [--repo <dir>] [--spec-dir <value>]
    python3 spec_dir.py --read <issue> [--repo <dir>] [--spec-dir <value>]
    python3 spec_dir.py --write-target <issue> <slug> [--repo <dir>] [--spec-dir <value>]

`--repo` is any directory of the code repository (default: the cwd);
`--spec-dir` overrides the configured value. Output is one JSON object on
stdout. A failure prints `{"error": <code>, "message": …}` on stdout, one
`spec_dir:` line on stderr, and exits with:

    1 config       the value cannot be resolved, or the repository is not a git repository
    2 no-spec      no `<issue>-*.md` on the branch (D7)
    3 ambiguous    more than one `<issue>-*.md`; `files` names them (D7)
    4 unreachable  a clone, fetch or ls-remote failed — `message` names the `gh` command
"""
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys

CONFIG_FILE = ".code-analyzer-config.json"
EXIT_CODES = {"config": 1, "no-spec": 2, "ambiguous": 3, "unreachable": 4}
NETWORK_TIMEOUT = 300
AUTH_HINT = ("check access with `gh auth status` (`gh auth login` if logged out, "
             "`gh auth setup-git` so git uses it over HTTPS)")
HTTPS_FALLBACK = ["-c", "url.https://github.com/.insteadOf=git@github.com:"]

REMOTE_RE = re.compile(
    r"^(?:git@github\.com:|ssh://git@github\.com/|git://github\.com/"
    r"|https?://(?:[^@/]+@)?github\.com/)"
    r"([A-Za-z0-9-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$")
OWNER_RE = re.compile(r"^[A-Za-z0-9-]+$")
REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class SpecDirError(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


# --------------------------------------------------------------------------
# git
# --------------------------------------------------------------------------

def _git_env():
    env = dict(os.environ)
    # A credential prompt in an unattended session is a hang, not a question.
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _run(argv, cwd=None, timeout=60):
    try:
        return subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              env=_git_env(), timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", "timed out after %ss" % timeout)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def _git(checkout, *args, timeout=60):
    return _run(["git", "-C", checkout] + list(args), timeout=timeout)


def _last_line(text):
    lines = [line for line in (text or "").strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def main_checkout(start):
    """(main checkout, git common dir) for any directory of the repository."""
    done = _git(start, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if done.returncode != 0:
        raise SpecDirError("config", "%s is not inside a git repository" % start)
    common = os.path.realpath(done.stdout.strip())
    return os.path.dirname(common), common


def origin_url(checkout):
    done = _git(checkout, "config", "--get", "remote.origin.url")
    return done.stdout.strip() if done.returncode == 0 else None


def normalize_remote(url):
    """`(owner, repo)` for a GitHub remote URL in any of its spellings, else None."""
    match = REMOTE_RE.match((url or "").strip())
    return (match.group(1), match.group(2)) if match else None


def same_repo(a, b):
    return a is not None and b is not None and \
        (a[0].lower(), a[1].lower()) == (b[0].lower(), b[1].lower())


def default_branch(checkout):
    done = _git(checkout, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if done.returncode == 0 and done.stdout.strip().startswith("origin/"):
        return done.stdout.strip()[len("origin/"):]
    for extra in ([], HTTPS_FALLBACK):
        done = _run(["git", "-C", checkout] + extra + ["ls-remote", "--symref", "origin", "HEAD"],
                    timeout=NETWORK_TIMEOUT)
        if done.returncode == 0:
            for line in done.stdout.splitlines():
                if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
                    return line[len("ref: refs/heads/"):-len("\tHEAD")]
    raise SpecDirError("unreachable", "cannot tell the default branch of %s's origin — %s"
                       % (checkout, AUTH_HINT))


def fetch(checkout):
    errors = []
    for extra in ([], HTTPS_FALLBACK):
        done = _run(["git", "-C", checkout] + extra + ["fetch", "--quiet", "origin"],
                    timeout=NETWORK_TIMEOUT)
        if done.returncode == 0:
            return
        errors.append(_last_line(done.stderr))
    raise SpecDirError("unreachable", "could not fetch origin in %s over SSH or HTTPS (%s) — "
                       "refusing to read a stale spec; %s"
                       % (checkout, errors[-1] or "no output", AUTH_HINT))


def clone(owner, repo, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    attempts = []
    if shutil.which("gh"):
        attempts.append(["gh", "repo", "clone", "%s/%s" % (owner, repo), dest, "--", "--quiet"])
    attempts.append(["git", "clone", "--quiet",
                     "https://github.com/%s/%s.git" % (owner, repo), dest])
    error = ""
    for argv in attempts:
        done = _run(argv, timeout=NETWORK_TIMEOUT)
        if done.returncode == 0:
            return
        error = _last_line(done.stderr) or error
        shutil.rmtree(dest, ignore_errors=True)
    raise SpecDirError("unreachable", "could not clone %s/%s (%s) — %s"
                       % (owner, repo, error or "no output", AUTH_HINT))


# --------------------------------------------------------------------------
# grammar
# --------------------------------------------------------------------------

def _github(owner, repo, rest, value):
    if repo.endswith(".git"):
        repo = repo[:-len(".git")]
    if not OWNER_RE.match(owner or "") or not REPO_RE.match(repo or ""):
        raise SpecDirError("config", "specDir %r does not name a GitHub owner/repo" % value)
    if any(part in ("", ".", "..") for part in rest):
        raise SpecDirError("config", "specDir %r has an empty, `.` or `..` path segment" % value)
    return {"kind": "github", "owner": owner, "repo": repo, "subpath": "/".join(rest)}


def parse(value):
    """Apply D1 to a raw `specDir` value. Touches nothing on disk."""
    if value is None:
        return {"kind": "none"}
    if not isinstance(value, str):
        raise SpecDirError("config", "specDir must be a string or null, got %r" % (value,))
    value = value.strip()
    if not value:
        return {"kind": "none"}
    if value.startswith("github:"):
        parts = value[len("github:"):].strip("/").split("/")
        if len(parts) < 2:
            raise SpecDirError("config", "specDir %r needs github:<owner>/<repo>[/<subpath>]" % value)
        return _github(parts[0], parts[1], parts[2:], value)
    url = re.match(r"^https://(?:www\.)?github\.com/(.*)$", value)
    if url:
        parts = url.group(1).strip("/").split("/")
        if len(parts) < 2:
            raise SpecDirError("config", "specDir %r needs https://github.com/<owner>/<repo>" % value)
        rest, branch = parts[2:], None
        if rest:
            if rest[0] != "tree" or len(rest) < 2:
                raise SpecDirError("config", "specDir %r: only /tree/<branch>/<subpath> URLs "
                                   "are understood" % value)
            branch, rest = rest[1], rest[2:]
        parsed = _github(parts[0], parts[1], rest, value)
        if branch is not None:
            parsed["ignoredBranch"] = branch
        return parsed
    if ":" in value:
        raise SpecDirError("config", "specDir %r is neither a path nor github:<owner>/<repo> — "
                           "non-GitHub forges are not supported" % value)
    return {"kind": "path", "value": value}


# --------------------------------------------------------------------------
# resolve / read / write-target
# --------------------------------------------------------------------------

def read_config(main):
    path = os.path.join(main, CONFIG_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        raise SpecDirError("config", "cannot read %s: %s" % (CONFIG_FILE, exc))
    section = data.get("orchestrator") if isinstance(data, dict) else None
    return section if isinstance(section, dict) else {}


_UNSET = object()


def _toplevel_of(target):
    probe = target
    while not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    done = _git(probe, "rev-parse", "--show-toplevel")
    if done.returncode != 0:
        raise SpecDirError("config", "specDir resolves to %s, which is not inside a git "
                           "repository" % target)
    return os.path.realpath(done.stdout.strip())


def _is_clone_of(path, pair):
    """A checkout's own toplevel whose raw origin names `pair` — the sibling test (D2)."""
    if not os.path.isdir(path):
        return False
    done = _git(path, "rev-parse", "--show-toplevel")
    if done.returncode != 0 or os.path.realpath(done.stdout.strip()) != os.path.realpath(path):
        return False
    return same_repo(normalize_remote(origin_url(path)), pair)


def _tree_url(repo, branch, subpath):
    if not repo:
        return None
    return "https://github.com/%s/tree/%s%s" % (repo, branch, "/" + subpath if subpath else "")


def _blob_url(repo, branch, path):
    return "https://github.com/%s/blob/%s/%s" % (repo, branch, path) if repo else None


def _slug(pair):
    return "%s/%s" % pair if pair else None


def resolve(start=".", spec_dir=_UNSET):
    """Apply D1 and D2. May clone (kind `github` with no usable sibling); never fetches."""
    main, common = main_checkout(start)
    config = read_config(main)
    value = config.get("specDir") if spec_dir is _UNSET else spec_dir
    parsed = parse(value)
    if parsed["kind"] == "none":
        return {"kind": "none"}

    if parsed["kind"] == "path":
        target = os.path.realpath(os.path.join(main, os.path.expanduser(parsed["value"])))
        inside = target == main or target.startswith(main + os.sep)
        checkout = main if inside else _toplevel_of(target)
        if not inside and checkout == main:
            raise SpecDirError("config", "specDir %r resolves outside the main checkout but "
                               "into its repository" % parsed["value"])
        subpath = os.path.relpath(target, checkout)
        subpath = "" if subpath == "." else subpath.replace(os.sep, "/")
        pair = normalize_remote(origin_url(checkout))
        base = config.get("base") if inside else None
        branch = base if isinstance(base, str) and base else default_branch(checkout)
        result = {"kind": "inside" if inside else "outside", "source": "main" if inside else "path"}
    else:
        pair = (parsed["owner"], parsed["repo"])
        sibling = os.path.join(os.path.dirname(main), parsed["repo"])
        if _is_clone_of(sibling, pair):
            checkout, source = os.path.realpath(sibling), "sibling"
        else:
            checkout = os.path.join(common, "cs-orchestrator", "specs",
                                    "%s-%s" % (parsed["owner"], parsed["repo"]))
            source = "cache"
            if not os.path.isdir(checkout):
                clone(parsed["owner"], parsed["repo"], checkout)
            elif not same_repo(normalize_remote(origin_url(checkout)), pair):
                raise SpecDirError("config", "%s exists but its origin is not %s — remove it "
                                   "and run again" % (checkout, _slug(pair)))
        subpath = parsed["subpath"]
        branch = default_branch(checkout)
        result = {"kind": "github", "source": source}
        if "ignoredBranch" in parsed:
            result["ignoredBranch"] = parsed["ignoredBranch"]

    repo = _slug(pair)
    result.update({
        "local": os.path.join(checkout, subpath) if subpath else checkout,
        "checkout": checkout,
        "repo": repo,
        "defaultBranch": branch,
        "subpath": subpath,
        "url": _tree_url(repo, branch, subpath),
        "separate": checkout != main,
    })
    return result


def _check_issue(issue):
    if not re.match(r"^[1-9][0-9]*$", str(issue)):
        raise SpecDirError("config", "issue must be a number, got %r" % (issue,))
    return str(issue)


def _write_snapshot(common, name, content):
    folder = os.path.join(common, "cs-orchestrator", "specs", "_read")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    if os.path.lexists(path):
        os.remove(path)
    with open(path, "w") as handle:
        handle.write(content)
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return path


def read(issue, start=".", spec_dir=_UNSET):
    """Apply D3 and D7: the one `<issue>-*.md` on `origin/<branch>`, fetched first."""
    issue = _check_issue(issue)
    where = resolve(start, spec_dir)
    if where["kind"] == "none":
        return where
    checkout, branch, subpath = where["checkout"], where["defaultBranch"], where["subpath"]
    fetch(checkout)
    ref = "origin/" + branch
    if _git(checkout, "rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode != 0:
        raise SpecDirError("config", "%s has no %s after fetching" % (where["repo"] or checkout, ref))
    commit = _git(checkout, "rev-parse", ref).stdout.strip()
    folder = subpath or "."
    listing = _git(checkout, "ls-tree", "-z", "%s:%s" % (commit, subpath))
    names = []
    if listing.returncode == 0:
        for entry in listing.stdout.split("\0"):
            if "\t" in entry:
                meta, name = entry.split("\t", 1)
                if meta.split()[1] == "blob" and re.match(r"^%s-.+\.md$" % issue, name):
                    names.append(name)
    looked = "%s-*.md in %s on %s of %s" % (issue, folder, ref, where["repo"] or checkout)
    if not names:
        raise SpecDirError("no-spec", "no %s" % looked, lookedFor=looked)
    paths = sorted((subpath + "/" + name) if subpath else name for name in names)
    if len(paths) > 1:
        raise SpecDirError("ambiguous", "more than one %s: %s" % (looked, ", ".join(paths)),
                           files=paths)
    path = paths[0]
    shown = _git(checkout, "show", "%s:%s" % (commit, path))
    if shown.returncode != 0:
        raise SpecDirError("unreachable", "git show %s:%s failed: %s"
                           % (ref, path, _last_line(shown.stderr)))
    _, common = main_checkout(start)
    local = _write_snapshot(common, os.path.basename(path), shown.stdout)
    url = _blob_url(where["repo"], branch, path)
    shown_as = url or "%s on %s" % (path, ref)
    return {
        "kind": where["kind"],
        "repo": where["repo"],
        "defaultBranch": branch,
        "commit": commit,
        "path": path,
        "url": url,
        "local": local,
        "content": shown.stdout,
        "briefLine": "Spec: %s (local read-only copy: %s)" % (shown_as, local),
    }


def write_target(issue, slug, start=".", spec_dir=_UNSET):
    """Where cs-spec writes `<issue>-<slug>.md`, and on which branch of which repository."""
    issue = _check_issue(issue)
    if not SLUG_RE.match(slug or ""):
        raise SpecDirError("config", "slug must be lowercase letters, digits and dashes, got %r"
                           % (slug,))
    where = resolve(start, spec_dir)
    if where["kind"] == "none":
        raise SpecDirError("config", "specDir is not set — the issue body is the spec")
    name = "%s-%s.md" % (issue, slug)
    rel = (where["subpath"] + "/" + name) if where["subpath"] else name
    return {
        "kind": where["kind"],
        "checkout": where["checkout"],
        "repo": where["repo"],
        "defaultBranch": where["defaultBranch"],
        "branch": "docs/%s-%s" % (issue, slug),
        "relPath": rel,
        "path": os.path.join(where["checkout"], rel),
        "url": _blob_url(where["repo"], where["defaultBranch"], rel),
        "separate": where["separate"],
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv):
    parser = argparse.ArgumentParser(prog="spec_dir.py", description=__doc__.split("\n")[0])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--resolve", action="store_true")
    action.add_argument("--read", metavar="ISSUE")
    action.add_argument("--write-target", nargs=2, metavar=("ISSUE", "SLUG"))
    parser.add_argument("--repo", default=".")
    parser.add_argument("--spec-dir", default=_UNSET)
    args = parser.parse_args(argv)
    try:
        if args.resolve:
            out = resolve(args.repo, args.spec_dir)
        elif args.read is not None:
            out = read(args.read, args.repo, args.spec_dir)
        else:
            out = write_target(args.write_target[0], args.write_target[1], args.repo, args.spec_dir)
    except SpecDirError as exc:
        payload = {"error": exc.code, "message": exc.message}
        payload.update(exc.extra)
        print(json.dumps(payload, indent=2))
        print("spec_dir: %s" % exc.message, file=sys.stderr)
        return EXIT_CODES[exc.code]
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
