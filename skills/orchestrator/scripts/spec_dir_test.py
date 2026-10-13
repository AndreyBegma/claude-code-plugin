#!/usr/bin/env python3
"""Tests for `spec_dir.py`, the `orchestrator.specDir` resolver (#7).

Run it directly:

    python3 skills/orchestrator/scripts/spec_dir_test.py

No network. Fixture bare repositories under a temp directory stand in for
github.com: a throwaway `GIT_CONFIG_GLOBAL` rewrites `https://github.com/` and
`git@github.com:` to them with `insteadOf`, so every clone keeps a real GitHub
URL as its raw `remote.origin.url` — which is exactly what the sibling test
reads. A fake `gh` that always fails sits first on `PATH`, so cloning takes the
`git clone` fallback. `CS_*` and `GIT_*` variables inherited from the session
are dropped first.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_DIR = os.path.join(HERE, "spec_dir.py")
sys.path.insert(0, HERE)
import spec_dir  # noqa: E402

BASE_ENV = {k: v for k, v in os.environ.items() if not k.startswith(("CS_", "GIT_"))}


# --------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------

class World:
    """A temp directory holding fake GitHub remotes and the checkouts around them."""

    def __init__(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="spec-dir-test-"))
        self.remotes = os.path.join(self.root, "remotes")
        self.seeds = os.path.join(self.root, "seeds")
        bindir = os.path.join(self.root, "bin")
        os.makedirs(bindir)
        gh = os.path.join(bindir, "gh")
        with open(gh, "w") as handle:
            handle.write("#!/bin/sh\necho 'gh: fake, always fails' >&2\nexit 1\n")
        os.chmod(gh, 0o755)
        gitconfig = os.path.join(self.root, "gitconfig")
        with open(gitconfig, "w") as handle:
            handle.write(
                "[user]\n\tname = Spec Test\n\temail = spec@test.invalid\n"
                "[init]\n\tdefaultBranch = main\n"
                "[advice]\n\tdetachedHead = false\n"
                '[url "file://%s/"]\n'
                "\tinsteadOf = https://github.com/\n"
                "\tinsteadOf = git@github.com:\n" % self.remotes)
        self.env = dict(BASE_ENV)
        self.env.update({
            "GIT_CONFIG_GLOBAL": gitconfig,
            "GIT_CONFIG_NOSYSTEM": "1",
            "PATH": bindir + os.pathsep + BASE_ENV.get("PATH", ""),
        })

    def git(self, cwd, *args):
        done = subprocess.run(["git"] + list(args), cwd=cwd, env=self.env,
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError("git %s in %s: %s" % (" ".join(args), cwd, done.stderr))
        return done.stdout

    def remote(self, owner, repo, files):
        """A bare `owner/repo` on the fake GitHub, seeded with `files` on main."""
        bare = os.path.join(self.remotes, owner, repo + ".git")
        os.makedirs(bare)
        self.git(bare, "init", "-q", "--bare", "-b", "main")
        seed = os.path.join(self.seeds, owner + "-" + repo)
        os.makedirs(seed)
        self.git(seed, "init", "-q", "-b", "main")
        self.git(seed, "remote", "add", "origin", "https://github.com/%s/%s.git" % (owner, repo))
        self.commit(owner, repo, files)

    def commit(self, owner, repo, files, branch="main"):
        """Commit `files` on `branch` of the seed and push it — a merge on GitHub."""
        seed = os.path.join(self.seeds, owner + "-" + repo)
        if self.git(seed, "branch", "--list", branch).strip():
            self.git(seed, "checkout", "-q", branch)
        elif self.git(seed, "branch").strip():
            self.git(seed, "checkout", "-q", "-b", branch, "main")
        # else: the first commit, on the unborn main
        for path, content in files.items():
            write(os.path.join(seed, path), content)
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-q", "-m", "seed %s" % branch)
        self.git(seed, "push", "-q", "origin", branch)
        self.git(seed, "checkout", "-q", "main")

    def merge(self, owner, repo, branch):
        seed = os.path.join(self.seeds, owner + "-" + repo)
        self.git(seed, "checkout", "-q", "main")
        self.git(seed, "merge", "-q", "--no-ff", "-m", "merge %s" % branch, branch)
        self.git(seed, "push", "-q", "origin", "main")

    def clone(self, owner, repo, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        self.git(self.root, "clone", "-q", "https://github.com/%s/%s.git" % (owner, repo), dest)
        return dest

    def run(self, cwd, *args):
        done = subprocess.run([sys.executable, SPEC_DIR] + list(args), cwd=cwd, env=self.env,
                              capture_output=True, text=True, timeout=120)
        try:
            payload = json.loads(done.stdout) if done.stdout.strip() else {}
        except ValueError:
            payload = {"unparsed": done.stdout}
        return done.returncode, payload, done.stderr

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(content)


def config(checkout, **orchestrator):
    write(os.path.join(checkout, ".code-analyzer-config.json"),
          json.dumps({"orchestrator": orchestrator}))


FAILURES = []
PASSED = [0]


def check(label, condition, detail=""):
    print("%s  %s" % ("ok  " if condition else "FAIL", label))
    if condition:
        PASSED[0] += 1
    else:
        FAILURES.append("%s%s" % (label, " — %s" % detail if detail else ""))


def expect(label, result, code, **fields):
    rc, payload, stderr = result
    wrong = {k: (payload.get(k), v) for k, v in fields.items() if payload.get(k) != v}
    check(label, rc == code and not wrong,
          "exit %s (want %s), mismatched %s, stderr %s" % (rc, code, wrong, stderr.strip()))
    return payload


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------

def unit_cases():
    for url, want in [
        ("git@github.com:Acme/App.git", ("Acme", "App")),
        ("https://github.com/acme/app", ("acme", "app")),
        ("https://x-token@github.com/acme/app.git/", ("acme", "app")),
        ("ssh://git@github.com/acme/app-documentation.git", ("acme", "app-documentation")),
        ("https://gitlab.com/acme/app.git", None),
        ("/srv/git/app.git", None),
    ]:
        check("normalize_remote %s" % url, spec_dir.normalize_remote(url) == want,
              repr(spec_dir.normalize_remote(url)))
    check("same_repo ignores case",
          spec_dir.same_repo(("Acme", "App"), ("acme", "app")))

    for value, want in [
        (None, {"kind": "none"}),
        ("", {"kind": "none"}),
        ("docs/specs", {"kind": "path", "value": "docs/specs"}),
        ("../x-documentation/prs", {"kind": "path", "value": "../x-documentation/prs"}),
        ("github:o/r/prs", {"kind": "github", "owner": "o", "repo": "r", "subpath": "prs"}),
        ("github:o/r", {"kind": "github", "owner": "o", "repo": "r", "subpath": ""}),
        ("https://github.com/o/r/tree/main/prs",
         {"kind": "github", "owner": "o", "repo": "r", "subpath": "prs", "ignoredBranch": "main"}),
        ("https://github.com/o/r.git", {"kind": "github", "owner": "o", "repo": "r", "subpath": ""}),
    ]:
        got = spec_dir.parse(value)
        check("parse %r" % (value,), got == want, repr(got))
    for value in ["gitlab:o/r", "github:o", "https://github.com/o/r/blob/main/x.md",
                  "github:o/r/../x", "C:\\specs", 42]:
        try:
            spec_dir.parse(value)
            check("parse %r is refused" % (value,), False, "accepted")
        except spec_dir.SpecDirError as exc:
            check("parse %r is refused" % (value,), exc.code == "config", exc.code)


def matching_sibling_cases(w):
    """Acceptance 1, 2 (match half), 3, 4, and write-target."""
    app = w.clone("acme", "app", os.path.join(w.root, "a", "app"))
    docs = w.clone("acme", "app-documentation", os.path.join(w.root, "a", "app-documentation"))
    config(app, base="develop", specDir="docs/specs")

    expect("docs/specs is inside, read from the base", w.run(app, "--resolve"), 0,
           kind="inside", local=os.path.join(app, "docs", "specs"), checkout=app,
           repo="acme/app", defaultBranch="develop", subpath="docs/specs", separate=False,
           url="https://github.com/acme/app/tree/develop/docs/specs")
    config(app, specDir="docs/specs")
    expect("inside with no base falls back to the default branch", w.run(app, "--resolve"), 0,
           kind="inside", defaultBranch="main")
    config(app, base="develop", specDir="docs/specs")

    worktree = os.path.join(w.root, "a", ".wt-app-i1")
    w.git(app, "worktree", "add", "-q", "-b", "feat/1-x", worktree)
    expect("from a worktree, a path resolves against the main checkout",
           w.run(worktree, "--resolve"), 0, kind="inside", checkout=app,
           local=os.path.join(app, "docs", "specs"))

    expect("../app-documentation/prs is outside",
           w.run(app, "--resolve", "--spec-dir", "../app-documentation/prs"), 0,
           kind="outside", local=os.path.join(docs, "prs"), checkout=docs,
           repo="acme/app-documentation", defaultBranch="main", subpath="prs", separate=True,
           url="https://github.com/acme/app-documentation/tree/main/prs")
    expect("docs/../../app-documentation/prs is classified by where it resolves",
           w.run(app, "--resolve", "--spec-dir", "docs/../../app-documentation/prs"), 0,
           kind="outside", checkout=docs)
    expect("github:acme/app-documentation/prs uses the matching sibling",
           w.run(app, "--resolve", "--spec-dir", "github:acme/app-documentation/prs"), 0,
           kind="github", source="sibling", checkout=docs, local=os.path.join(docs, "prs"),
           repo="acme/app-documentation", defaultBranch="main", subpath="prs")
    payload = expect("a GitHub tree URL is normalized to the github: form",
                     w.run(app, "--resolve", "--spec-dir",
                           "https://github.com/acme/app-documentation/tree/main/prs"), 0,
                     kind="github", source="sibling", checkout=docs, subpath="prs",
                     ignoredBranch="main")
    check("a URL with no /tree/ reports no ignoredBranch",
          "ignoredBranch" not in w.run(app, "--resolve", "--spec-dir",
                                       "https://github.com/acme/app-documentation")[1])
    expect("a non-default branch in the URL is reported, not followed",
           w.run(app, "--resolve", "--spec-dir",
                 "https://github.com/acme/app-documentation/tree/release/prs"), 0,
           defaultBranch="main", ignoredBranch="release")
    check("no cache clone was made while the sibling matched",
          not os.path.exists(os.path.join(app, ".git", "cs-orchestrator", "specs",
                                          "acme-app-documentation")), payload)

    expect("write-target in a separate repository",
           w.run(app, "--write-target", "12", "my-spec", "--spec-dir",
                 "github:acme/app-documentation/prs"), 0,
           checkout=docs, repo="acme/app-documentation", defaultBranch="main",
           branch="docs/12-my-spec", relPath="prs/12-my-spec.md",
           path=os.path.join(docs, "prs", "12-my-spec.md"), separate=True,
           url="https://github.com/acme/app-documentation/blob/main/prs/12-my-spec.md")
    expect("write-target inside the code repository lands on the base",
           w.run(app, "--write-target", "12", "my-spec"), 0,
           checkout=app, repo="acme/app", defaultBranch="develop",
           relPath="docs/specs/12-my-spec.md", separate=False)
    expect("write-target refuses a slug with spaces",
           w.run(app, "--write-target", "12", "My Spec"), 1, error="config")

    return app, docs


def read_cases(w, app, docs):
    """Acceptance 3 (origin, not the working tree) and 4 (two matches)."""
    spec = "github:acme/app-documentation/prs"
    write(os.path.join(docs, "prs", "42-foo.md"), "LOCAL EDIT, never committed\n")
    write(os.path.join(docs, "prs", "77-draft.md"), "a local draft nobody pushed\n")
    payload = expect("--read 42 returns origin/main, not the uncommitted edit",
                     w.run(app, "--read", "42", "--spec-dir", spec), 0,
                     path="prs/42-foo.md", content="merged spec 42\n",
                     url="https://github.com/acme/app-documentation/blob/main/prs/42-foo.md",
                     defaultBranch="main", repo="acme/app-documentation")
    snapshot = os.path.join(app, ".git", "cs-orchestrator", "specs", "_read", "42-foo.md")
    check("the local copy is a snapshot inside .git", payload.get("local") == snapshot,
          payload.get("local"))
    if os.path.exists(snapshot):
        with open(snapshot) as handle:
            check("the snapshot holds the origin content", handle.read() == "merged spec 42\n")
        check("the snapshot is read-only (0444)",
              stat.S_IMODE(os.stat(snapshot).st_mode) == 0o444,
              oct(stat.S_IMODE(os.stat(snapshot).st_mode)))
    check("briefLine carries the URL and the local path",
          payload.get("briefLine") == "Spec: https://github.com/acme/app-documentation/blob/main/"
          "prs/42-foo.md (local read-only copy: %s)" % snapshot, payload.get("briefLine"))
    expect("a second --read replaces the read-only snapshot",
           w.run(app, "--read", "42", "--spec-dir", spec), 0, local=snapshot)

    expect("an unpushed local spec is NO SPEC",
           w.run(app, "--read", "77", "--spec-dir", spec), 2, error="no-spec")
    expect("42 does not match 420-other.md, and 4 matches nothing",
           w.run(app, "--read", "4", "--spec-dir", spec), 2, error="no-spec")

    w.commit("acme", "app-documentation", {"prs/43-new.md": "merged a minute ago\n"})
    expect("a spec merged after the sibling was cloned is read (fetch first)",
           w.run(app, "--read", "43", "--spec-dir", spec), 0, content="merged a minute ago\n")

    w.commit("acme", "app-documentation", {"prs/7-new.md": "second\n"})
    payload = expect("two 7-*.md files are an error naming both",
                     w.run(app, "--read", "7", "--spec-dir", spec), 3, error="ambiguous",
                     files=["prs/7-new.md", "prs/7-old.md"])
    check("the ambiguity message names both files",
          "prs/7-new.md" in payload.get("message", "") and
          "prs/7-old.md" in payload.get("message", ""), payload.get("message"))

    expect("--read 99 names what it looked for",
           w.run(app, "--read", "99", "--spec-dir", spec), 2, error="no-spec",
           lookedFor="99-*.md in prs on origin/main of acme/app-documentation")
    expect("--read with specDir unset is kind none",
           w.run(app, "--read", "42", "--spec-dir", ""), 0, kind="none")
    expect("--read refuses a non-number", w.run(app, "--read", "4x", "--spec-dir", spec), 1,
           error="config")
    expect("a non-GitHub forge is a config error",
           w.run(app, "--resolve", "--spec-dir", "gitlab:acme/docs"), 1, error="config")


def mismatched_sibling_cases(w):
    """Acceptance 2 (mismatch half) — and the clone fallback through `git clone`."""
    app = w.clone("acme", "app", os.path.join(w.root, "b", "app"))
    w.clone("other", "app-documentation", os.path.join(w.root, "b", "app-documentation"))
    cache = os.path.join(app, ".git", "cs-orchestrator", "specs", "acme-app-documentation")
    spec = "github:acme/app-documentation/prs"
    expect("a sibling with a different origin is not used; the repo is cloned into .git",
           w.run(app, "--resolve", "--spec-dir", spec), 0,
           kind="github", source="cache", checkout=cache, local=os.path.join(cache, "prs"),
           repo="acme/app-documentation", defaultBranch="main")
    check("the cache clone's origin is acme/app-documentation",
          spec_dir.normalize_remote(w.git(cache, "config", "--get", "remote.origin.url").strip())
          == ("acme", "app-documentation"))
    expect("the cache clone is reused", w.run(app, "--resolve", "--spec-dir", spec), 0,
           source="cache", checkout=cache)
    expect("--read through the cache clone",
           w.run(app, "--read", "42", "--spec-dir", spec), 0, content="merged spec 42\n")

    payload = expect("an unreachable repository names the gh auth command",
                     w.run(app, "--resolve", "--spec-dir", "github:acme/private-docs"), 4,
                     error="unreachable")
    check("…with `gh auth status` in the message", "gh auth status" in payload.get("message", ""),
          payload.get("message"))
    check("…and leaves no half-made clone behind",
          not os.path.exists(os.path.join(app, ".git", "cs-orchestrator", "specs",
                                          "acme-private-docs")))


def orchestrator_dry_check(w):
    """Acceptance 5 and 6: NO SPEC while unmerged, READY after, and the brief line."""
    w.remote("acme", "docs-repo", {"prs/.keep": ""})
    app = w.clone("acme", "app", os.path.join(w.root, "c", "app"))
    docs = w.clone("acme", "docs-repo", os.path.join(w.root, "c", "docs-repo"))
    config(app, base="develop", specDir="../docs-repo/prs")

    w.commit("acme", "docs-repo", {"prs/1-x.md": "spec for #1\n"}, branch="docs/1-x")
    w.git(docs, "fetch", "-q", "origin")
    w.git(docs, "checkout", "-q", "-b", "docs/1-x", "origin/docs/1-x")
    expect("spec only on an unmerged branch (even checked out locally) → NO SPEC",
           w.run(app, "--read", "1"), 2, error="no-spec")

    w.merge("acme", "docs-repo", "docs/1-x")
    snapshot = os.path.join(app, ".git", "cs-orchestrator", "specs", "_read", "1-x.md")
    payload = expect("after the docs PR merges → READY", w.run(app, "--read", "1"), 0,
                     kind="outside", content="spec for #1\n", path="prs/1-x.md",
                     url="https://github.com/acme/docs-repo/blob/main/prs/1-x.md",
                     local=snapshot)
    check("the brief's Spec: line has the GitHub URL and the local path",
          payload.get("briefLine") == "Spec: https://github.com/acme/docs-repo/blob/main/prs/"
          "1-x.md (local read-only copy: %s)" % snapshot, payload.get("briefLine"))

    bare = os.path.join(w.remotes, "acme", "docs-repo.git")
    os.rename(bare, bare + ".gone")
    try:
        payload = expect("a failed fetch is an error, never a stale read",
                         w.run(app, "--read", "1"), 4, error="unreachable")
        check("…and it names the gh command", "gh auth" in payload.get("message", ""))
    finally:
        os.rename(bare + ".gone", bare)


def main():
    unit_cases()
    w = World()
    try:
        w.remote("acme", "app", {"README.md": "app\n"})
        w.commit("acme", "app", {"docs/specs/.keep": ""}, branch="develop")
        w.remote("acme", "app-documentation", {
            "prs/42-foo.md": "merged spec 42\n",
            "prs/420-other.md": "not 42\n",
            "prs/7-old.md": "first\n",
        })
        w.remote("other", "app-documentation", {"prs/42-foo.md": "the wrong repository\n"})
        app, docs = matching_sibling_cases(w)
        read_cases(w, app, docs)
        mismatched_sibling_cases(w)
        orchestrator_dry_check(w)
    finally:
        w.cleanup()

    print()
    if FAILURES:
        print("%d failed:" % len(FAILURES))
        for line in FAILURES:
            print("  - %s" % line)
        return 1
    print("%d passed" % PASSED[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
