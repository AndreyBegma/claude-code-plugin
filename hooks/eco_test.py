#!/usr/bin/env python3
"""Tests for the cs-eco hooks (`eco_hook.py`), state (`eco_lib.py`) and CLI
(`eco_ctl.py`).

    python3 hooks/eco_test.py        (or: python3 -m pytest -q hooks)

Every case runs the hook as Claude Code would — a subprocess fed hook JSON on
stdin — with HOME, XDG_STATE_HOME and XDG_CONFIG_HOME in a temp dir and a stub
`agentdock-runner` on PATH that records what it was called with. Nothing here
touches the real state, config or settings.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "eco_run.py")
# Exactly what hooks.json runs: `-S` skips site-packages initialisation (~12 ms
# per call on a machine with a few .pth files); the hooks need the stdlib only.
HOOK_CMD = [sys.executable, "-S", HOOK]
CTL = os.path.join(HERE, "eco_ctl.py")
KILL_GUARD = os.path.join(HERE, "kill_guard.py")
STATUSLINE = os.path.join(HERE, "eco-statusline.sh")
sys.path.insert(0, HERE)

import eco_hook  # noqa: E402
import eco_lib  # noqa: E402

SID = "sess-1234"

# The stub answers like agentdock-runner ≥ 0.12.1's filter-hook: rewrite + allow
# in bypass, rewrite without a decision in auto, nothing otherwise. It records
# its argv and the AGENTDOCK_* env it saw. STUB_MODE switches it to misbehave.
STUB = r"""#!/bin/sh
log="$STUB_LOG"
[ -n "$log" ] && { echo "argv:$*"; env | grep '^AGENTDOCK_' | sort; } >> "$log"
case "$1" in --version) echo "0.12.1"; exit 0 ;; esac
input=$(cat)
case "$STUB_MODE" in
  garbage) echo 'not json {'; exit 0 ;;
  fail) exit 3 ;;
  sleep) sleep 30; exit 0 ;;
  ask) echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","updatedInput":{"command":"x"}}}'; exit 0 ;;
esac
case "$input" in
  *'"bypassPermissions"'*) echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"AgentDock token saver","updatedInput":{"command":"/opt/runner filter -- bun run test","timeout":1000}}}' ;;
  *'"auto"'*) echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{"command":"/opt/runner filter -- bun run test"}}}' ;;
esac
exit 0
"""


def big_text(lines=500):
    out = ["# Title", "", "## Install", ""]
    out += ["line %d of filler text" % i for i in range(lines - 8)]
    out += ["## Usage", "", "def top_level():", "    pass"]
    return "\n".join(out) + "\n"


class EcoBase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="eco_test_")
        self.bin = os.path.join(self.root, "bin")
        os.makedirs(self.bin)
        self.stub_log = os.path.join(self.root, "stub.log")
        self.install_stub()
        self.files = os.path.join(self.root, "files")
        os.makedirs(self.files)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("AGENTDOCK_", "CS_ECO", "XDG_", "CLAUDE_AUTOCOMPACT"))}
        self.env.update(
            HOME=self.root,
            XDG_STATE_HOME=os.path.join(self.root, "state"),
            XDG_CONFIG_HOME=os.path.join(self.root, "config"),
            PATH=self.bin + os.pathsep + "/usr/bin:/bin",
            STUB_LOG=self.stub_log,
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def install_stub(self):
        path = os.path.join(self.bin, "agentdock-runner")
        with open(path, "w") as f:
            f.write(STUB)
        os.chmod(path, 0o755)

    def hook(self, payload, **env):
        e = dict(self.env)
        e.update(env)
        r = subprocess.run(HOOK_CMD, input=json.dumps(payload) if not isinstance(payload, str)
                           else payload, capture_output=True, text=True, env=e, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        return json.loads(r.stdout) if r.stdout.strip() else None

    def ctl(self, *args, stdin="", **env):
        e = dict(self.env)
        e.update(env)
        return subprocess.run([sys.executable, CTL] + list(args), input=stdin, capture_output=True,
                              text=True, env=e, timeout=30)

    def eco_on(self, sid=SID):
        r = self.ctl("on", "--session", sid)
        self.assertEqual(r.returncode, 0, r.stderr)

    def bash(self, command="bun run test", mode="bypassPermissions", sid=SID, **extra):
        p = {"session_id": sid, "hook_event_name": "PreToolUse", "tool_name": "Bash",
             "tool_input": {"command": command}, "permission_mode": mode, "cwd": self.files}
        p.update(extra)
        return p

    def read(self, path, event="PreToolUse", sid=SID, **ti):
        tool_input = {"file_path": path}
        tool_input.update(ti)
        return {"session_id": sid, "hook_event_name": event, "tool_name": "Read",
                "tool_input": tool_input, "permission_mode": "default", "cwd": self.files}

    def write_file(self, name, text):
        path = os.path.join(self.files, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def stub_calls(self):
        try:
            with open(self.stub_log) as f:
                return f.read()
        except OSError:
            return ""

    def sdir(self, sid=SID):
        return os.path.join(self.env["XDG_STATE_HOME"], "cs-eco", "sessions", sid)

    def rows(self, sid=SID):
        path = os.path.join(self.sdir(sid), "filter-stats.jsonl")
        try:
            with open(path) as f:
                return [json.loads(line) for line in f]
        except OSError:
            return []


class OnOff(EcoBase):
    def test_off_by_default_everything_is_a_noop(self):
        big = self.write_file("big.md", big_text())
        self.assertIsNone(self.hook(self.read(big)))
        self.assertIsNone(self.hook(self.bash()))
        self.assertIsNone(self.hook({"session_id": SID, "hook_event_name": "SessionStart", "source": "startup"}))
        self.assertEqual(self.stub_calls(), "")
        self.assertFalse(os.path.exists(self.sdir()))

    def test_session_on_then_off_stops_at_once(self):
        self.eco_on()
        self.assertIsNotNone(self.hook(self.bash()))
        r = self.ctl("off", "--session", SID)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(self.hook(self.bash()))

    def test_env_on_and_session_off_wins_over_env(self):
        self.assertIsNotNone(self.hook(self.bash(), CS_ECO="on"))
        self.ctl("off", "--session", SID)
        self.assertIsNone(self.hook(self.bash(), CS_ECO="on"))

    def test_machine_default(self):
        r = self.ctl("default", "on")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.env["XDG_CONFIG_HOME"], "cs-eco", "config.json")) as f:
            self.assertEqual(json.load(f)["default"], "on")
        self.assertIsNotNone(self.hook(self.bash(sid="other")))
        self.assertIsNone(self.hook(self.bash(sid="other"), CS_ECO="off"))
        self.ctl("default", "off")
        self.assertIsNone(self.hook(self.bash(sid="other")))

    def test_other_sessions_are_untouched(self):
        self.eco_on("a")
        self.assertIsNotNone(self.hook(self.bash(sid="a")))
        self.assertIsNone(self.hook(self.bash(sid="b")))


class BashFilter(EcoBase):
    def setUp(self):
        super().setUp()
        self.eco_on()
        os.remove(self.stub_log)  # `on` printed the status, which asked for --version

    def test_bypass_rewrites_with_allow_and_session_env_prefix(self):
        out = self.hook(self.bash())
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "allow")
        cmd = hso["updatedInput"]["command"]
        stats = os.path.join(self.sdir(), "filter-stats.jsonl")
        self.assertTrue(cmd.startswith("AGENTDOCK_FILTER_STATS=" + stats + " "), cmd)
        self.assertIn("AGENTDOCK_FILTER_RUN=" + SID, cmd)
        self.assertIn("AGENTDOCK_FILTER_RUN_KIND=skill", cmd)
        self.assertTrue(cmd.endswith(" /opt/runner filter -- bun run test"), cmd)
        calls = self.stub_calls()
        self.assertIn("argv:filter-hook", calls)
        self.assertIn("AGENTDOCK_FILTER_STATS=" + stats, calls)  # the runner saw it too

    def test_auto_rewrites_with_no_decision(self):
        out = self.hook(self.bash(mode="auto"))
        hso = out["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", hso)
        self.assertIn("filter -- bun run test", hso["updatedInput"]["command"])

    def test_never_in_default_plan_or_accept_edits(self):
        for mode in ("default", "plan", "acceptEdits", None):
            self.assertIsNone(self.hook(self.bash(mode=mode)), mode)
        self.assertEqual(self.stub_calls(), "")  # not even asked

    def test_runner_output_fields_survive(self):
        out = self.hook(self.bash())
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecisionReason"], "AgentDock token saver")
        self.assertEqual(hso["updatedInput"]["timeout"], 1000)  # the runner keeps the tool input

    def test_runner_kind_override(self):
        out = self.hook(self.bash(), CS_ECO_RUN_KIND="card")
        self.assertIn("AGENTDOCK_FILTER_RUN_KIND=card", out["hookSpecificOutput"]["updatedInput"]["command"])

    def test_kill_guard_denial_wins(self):
        command = "kill $(pgrep -f node)"
        p = self.bash(command=command)
        r = subprocess.run([sys.executable, KILL_GUARD], input=json.dumps(p), capture_output=True, text=True)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(self.hook(p))
        self.assertEqual(self.stub_calls(), "")

    def test_runner_launched_session_is_left_to_the_runner(self):
        self.assertIsNone(self.hook(self.bash(), AGENTDOCK_FILTER_STATS="/x/filter-stats.jsonl"))
        self.assertEqual(self.stub_calls(), "")

    def test_no_runner_no_rewrite_and_status_says_so(self):
        os.remove(os.path.join(self.bin, "agentdock-runner"))
        shutil.rmtree(self.sdir(), ignore_errors=True)
        self.eco_on()
        self.assertIsNone(self.hook(self.bash()))
        r = self.ctl("status", "--session", SID)
        self.assertIn("command filter unavailable (agentdock-runner not installed)", r.stdout.replace(":", ""))

    def test_fails_open(self):
        for mode in ("garbage", "fail", "ask"):
            self.assertIsNone(self.hook(self.bash(), STUB_MODE=mode), mode)
        self.assertIsNone(self.hook("not json at all"))
        self.assertIsNone(self.hook({"session_id": SID, "hook_event_name": "PreToolUse", "tool_name": "Bash",
                                     "tool_input": None, "permission_mode": "bypassPermissions"}))

    def test_runner_timeout_fails_open(self):
        old = eco_hook.RUNNER_TIMEOUT
        try:
            eco_hook.RUNNER_TIMEOUT = 1
            stdout = []
            orig = sys.stdout.write
            sys.stdout.write = stdout.append
            os.environ["STUB_MODE"] = "sleep"
            try:
                saved = {k: os.environ.get(k) for k in ("PATH", "XDG_STATE_HOME", "XDG_CONFIG_HOME", "HOME")}
                os.environ.update({k: self.env[k] for k in saved})
                import io
                sys_stdin = sys.stdin
                sys.stdin = io.StringIO(json.dumps(self.bash()))
                t0 = time.time()
                eco_hook.main()
                elapsed = time.time() - t0
            finally:
                sys.stdin = sys_stdin
                sys.stdout.write = orig
                os.environ.pop("STUB_MODE", None)
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
            self.assertEqual("".join(stdout), "")
            self.assertLess(elapsed, 5)
        finally:
            eco_hook.RUNNER_TIMEOUT = old


class RunnerResolution(EcoBase):
    def test_wrapper_resolves_to_platform_binary(self):
        pkg = eco_hook._platform_package()
        root = os.path.join(self.root, "lib", "node_modules", "agentdock-runner")
        os.makedirs(os.path.join(root, "bin"))
        js = os.path.join(root, "bin", "agentdock-runner.js")
        with open(js, "w") as f:
            f.write("#!/usr/bin/env node\n")
        os.chmod(js, 0o755)
        binary = os.path.join(root, "node_modules", pkg, "bin", "agentdock-runner")
        os.makedirs(os.path.dirname(binary))
        with open(binary, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(binary, 0o755)
        os.remove(os.path.join(self.bin, "agentdock-runner"))
        os.symlink(js, os.path.join(self.bin, "agentdock-runner"))
        self.assertEqual(eco_hook.find_runner({"PATH": self.bin}), binary)

    def test_hoisted_and_wrapper_fallbacks(self):
        pkg = eco_hook._platform_package()
        nm = os.path.join(self.root, "lib", "node_modules")
        js = os.path.join(nm, "agentdock-runner", "bin", "agentdock-runner.js")
        os.makedirs(os.path.dirname(js))
        with open(js, "w") as f:
            f.write("#!/usr/bin/env node\n")
        os.chmod(js, 0o755)
        link = os.path.join(self.bin, "agentdock-runner")
        os.remove(link)
        os.symlink(js, link)
        # no platform package anywhere (and no npm on this PATH): the wrapper
        self.assertEqual(eco_hook.find_runner({"PATH": self.bin}), link)
        hoisted = os.path.join(nm, pkg, "bin", "agentdock-runner")
        os.makedirs(os.path.dirname(hoisted))
        with open(hoisted, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(hoisted, 0o755)
        self.assertEqual(eco_hook.find_runner({"PATH": self.bin}), hoisted)

    def test_resolved_once_per_session(self):
        self.eco_on()
        self.hook(self.bash())
        with open(os.path.join(self.sdir(), "runner")) as f:
            self.assertEqual(f.read().strip(), os.path.join(self.bin, "agentdock-runner"))


class ReadGuard(EcoBase):
    def setUp(self):
        super().setUp()
        self.eco_on()

    def test_big_file_denied_once_with_outline_then_repeat_passes(self):
        path = self.write_file("big.md", big_text())
        out = self.hook(self.read(path))
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        reason = hso["permissionDecisionReason"]
        self.assertIn("500 lines", reason)
        self.assertIn("1: # Title", reason)
        self.assertIn("## Usage", reason)
        self.assertIn("repeat the same call", reason)
        self.assertIn("offset/limit", reason)
        self.assertIsNone(self.hook(self.read(path)))  # the repeat reads it
        rows = [r["row"] for r in self.rows()]
        self.assertEqual([r["filter"] for r in rows], ["cs-eco/read-guard", "cs-eco/read-guard"])
        self.assertEqual([r["bypassed"] for r in rows], [False, True])
        net = sum(r["rawBytes"] - r["keptBytes"] for r in rows)
        self.assertEqual(net, -len(reason))  # the override costs the hint, nothing is claimed

    def test_code_outline_lists_top_level_symbols(self):
        body = "import os\n\n" + "".join("def f%d():\n    return %d\n\n" % (i, i) for i in range(200))
        path = self.write_file("big.py", body)
        reason = self.hook(self.read(path))["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("3: def f0():", reason)
        self.assertIn("more, sampled", reason)
        self.assertNotIn("return 0", reason)

    def test_small_files_ranges_and_binaries_pass(self):
        small = self.write_file("small.txt", "x\n" * 400)
        self.assertIsNone(self.hook(self.read(small)))
        big = self.write_file("big.txt", "x\n" * 1000)
        self.assertIsNone(self.hook(self.read(big, offset=1, limit=50)))
        self.assertIsNone(self.hook(self.read(big, limit=50)))
        binary = os.path.join(self.files, "blob.bin")
        with open(binary, "wb") as f:
            f.write(b"\0\1\2\n" * 5000)
        self.assertIsNone(self.hook(self.read(binary)))
        self.assertIsNone(self.hook(self.read(os.path.join(self.files, "missing.txt"))))
        self.assertIsNone(self.hook(self.read("relative/path.txt")))

    def test_dedup_denies_an_unchanged_repeat_once(self):
        path = self.write_file("a.txt", "hello\n" * 10)
        self.assertIsNone(self.hook(self.read(path)))
        self.assertIsNone(self.hook(self.read(path, event="PostToolUse")))
        out = self.hook(self.read(path))
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("already in context since", reason)
        self.assertIsNone(self.hook(self.read(path)))  # the repeat passes

    def test_dedup_key_is_path_range_mtime_and_size(self):
        path = self.write_file("a.txt", "hello\n" * 10)
        self.hook(self.read(path, event="PostToolUse", offset=1, limit=5))
        self.assertIsNone(self.hook(self.read(path, offset=2, limit=5)))  # other range
        self.assertIsNone(self.hook(self.read(path)))  # whole file is another range
        self.assertIsNotNone(self.hook(self.read(path, offset=1, limit=5)))  # same range
        self.hook(self.read(path, offset=1, limit=5))  # repeat passes
        self.hook(self.read(path, event="PostToolUse", offset=1, limit=5))
        with open(path, "a") as f:
            f.write("changed\n")
        self.assertIsNone(self.hook(self.read(path, offset=1, limit=5)))  # changed file

    def test_dedup_same_size_new_mtime_passes(self):
        path = self.write_file("a.txt", "aaaa\n")
        self.hook(self.read(path, event="PostToolUse"))
        st = os.stat(path)
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
        self.assertIsNone(self.hook(self.read(path)))

    def test_compaction_resets_guard_and_dedup(self):
        path = self.write_file("a.txt", "hello\n")
        self.hook(self.read(path, event="PostToolUse"))
        self.hook({"session_id": SID, "hook_event_name": "PreCompact", "trigger": "auto"})
        self.assertIsNone(self.hook(self.read(path)))
        self.hook(self.read(path, event="PostToolUse"))
        out = self.hook({"session_id": SID, "hook_event_name": "SessionStart", "source": "compact"})
        self.assertIn("Working register", out["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.hook(self.read(path)))
        big = self.write_file("big.md", big_text())
        self.assertIsNotNone(self.hook(self.read(big)))  # pending denial…
        self.hook({"session_id": SID, "hook_event_name": "PreCompact", "trigger": "manual"})
        self.assertIsNotNone(self.hook(self.read(big)))  # …is forgotten: the guard fires again


class SessionRegister(EcoBase):
    def start(self, source="startup"):
        return self.hook({"session_id": SID, "hook_event_name": "SessionStart", "source": source})

    def test_injected_once_while_on(self):
        self.assertIsNone(self.start())  # off
        self.ctl("default", "on")
        out = self.start()
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("scout", out["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.start("resume"))
        self.assertIsNotNone(self.start("clear"))

    def test_ctl_on_prints_register_once(self):
        r = self.ctl("on", "--session", SID)
        self.assertIn("Working register", r.stdout)
        r = self.ctl("on", "--session", SID)
        self.assertNotIn("Working register", r.stdout)
        self.assertIsNone(self.start("resume"))


class McpCut(EcoBase):
    def setUp(self):
        super().setUp()
        self.eco_on()

    def post(self, response, tool="mcp__glitchtip__list_issues"):
        return self.hook({"session_id": SID, "hook_event_name": "PostToolUse", "tool_name": tool,
                          "tool_input": {}, "tool_response": response, "cwd": self.files})

    def test_large_block_list_cut_to_head_and_tail_and_saved(self):
        text = "HEAD" + "m" * 50000 + "TAIL"
        image = {"type": "image", "data": "AAAA", "mimeType": "image/png"}
        out = self.post([{"type": "text", "text": text}, image])
        new = out["hookSpecificOutput"]["updatedMCPToolOutput"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertEqual(new[1], image)
        summary = new[0]["text"]
        self.assertTrue(summary.startswith("HEAD"))
        self.assertTrue(summary.endswith("TAIL"))
        self.assertLess(len(summary), 9000)
        saved = summary.split("Full output: ")[1].split(" — ")[0]
        self.assertTrue(saved.startswith(os.path.join(self.sdir(), "raw")))
        with open(saved) as f:
            self.assertEqual(f.read(), text)
        self.assertEqual(stat.S_IMODE(os.stat(saved).st_mode), 0o600)
        row = self.rows()[-1]
        self.assertEqual(row["row"]["filter"], "cs-eco/mcp")
        self.assertGreater(row["row"]["rawBytes"], row["row"]["keptBytes"])

    def test_string_and_dict_shapes_kept(self):
        out = self.post("x" * 20000)
        self.assertIsInstance(out["hookSpecificOutput"]["updatedMCPToolOutput"], str)
        out = self.post({"content": [{"type": "text", "text": "y" * 20000}], "isError": False})
        new = out["hookSpecificOutput"]["updatedMCPToolOutput"]
        self.assertFalse(new["isError"])
        self.assertIn("cs-eco", new["content"][0]["text"])

    def test_small_results_and_non_mcp_tools_untouched(self):
        self.assertIsNone(self.post([{"type": "text", "text": "small"}]))
        self.assertIsNone(self.post("z" * 20000, tool="WebFetch"))

    def test_threshold_from_config(self):
        cfg = os.path.join(self.env["XDG_CONFIG_HOME"], "cs-eco", "config.json")
        os.makedirs(os.path.dirname(cfg), exist_ok=True)
        with open(cfg, "w") as f:
            json.dump({"mcpMaxChars": 100000}, f)
        self.assertIsNone(self.post("x" * 20000))


class Stats(EcoBase):
    def test_row_shape_matches_filter_stats(self):
        self.eco_on()
        self.hook(self.read(self.write_file("big.md", big_text())))
        line = self.rows()[0]
        self.assertEqual(set(line), {"projectId", "row"})
        self.assertEqual(set(line["row"]), {"id", "runId", "runKind", "filter", "rawBytes", "keptBytes",
                                            "bypassed", "passedThrough", "at"})
        self.assertEqual(line["row"]["runId"], SID)
        self.assertEqual(line["row"]["runKind"], "skill")
        self.assertTrue(line["row"]["at"].endswith("Z"))
        self.assertEqual(line["projectId"], "files")  # no git remote: the directory name

    def test_stats_reports_runner_rows_and_ours(self):
        self.eco_on()
        d = self.sdir()
        runner_row = {"projectId": "p", "row": {"id": "f_1", "runId": SID, "runKind": "skill",
                                                "filter": "js/run-script", "rawBytes": 40000,
                                                "keptBytes": 2000, "bypassed": False,
                                                "passedThrough": False, "at": "2026-10-16T00:00:00.000Z"}}
        passed = dict(runner_row, row=dict(runner_row["row"], passedThrough=True, rawBytes=0, keptBytes=0))
        with open(os.path.join(d, "filter-stats.jsonl"), "a") as f:
            f.write(json.dumps(runner_row) + "\n" + json.dumps(passed) + "\nnot json\n")
        r = self.ctl("stats", "--session", SID)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("saved 38.0k bytes", r.stdout)
        self.assertIn("js/run-script", r.stdout)
        self.assertIn("1 commands left alone", r.stdout)
        r = self.ctl("stats", "--all", "--session", SID)
        self.assertIn("all sessions", r.stdout)

    def test_statusline(self):
        self.eco_on()
        with open(os.path.join(self.sdir(), "filter-stats.jsonl"), "w") as f:
            f.write(json.dumps({"projectId": "p", "row": {"filter": "x", "rawBytes": 8000, "keptBytes": 0}}) + "\n")
        data = json.dumps({"session_id": SID, "context_window": {"used_percentage": 42.6}})
        r = subprocess.run(["bash", STATUSLINE], input=data, capture_output=True, text=True, env=self.env)
        self.assertEqual(r.stdout.strip(), "eco on · saved ≈2.0k tok · ctx 43%")
        r = subprocess.run(["bash", STATUSLINE], input="{}", capture_output=True, text=True, env=self.env)
        self.assertEqual(r.stdout.strip(), "eco off")


class Ctl(EcoBase):
    def test_refuses_without_a_substituted_session_id(self):
        for sid in ("${CLAUDE_SESSION_ID}", ""):
            r = self.ctl("on", "--session", sid)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no session id", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.env["XDG_STATE_HOME"], "cs-eco", "sessions")))

    def test_status(self):
        self.eco_on()
        r = self.ctl("status", "--session", SID)
        self.assertIn("eco: on (set for this session)", r.stdout)
        self.assertIn("agentdock-runner 0.12.1, rewrites in bypassPermissions and auto only", r.stdout)
        self.assertIn("early compaction: off", r.stdout)
        r = self.ctl("status", "--session", SID, CLAUDE_AUTOCOMPACT_PCT_OVERRIDE="70")
        self.assertIn("early compaction: on at 70%", r.stdout)

    def test_old_runner_is_named(self):
        self.assertTrue(__import__("eco_ctl")._older("0.12.0", "0.12.1"))
        self.assertFalse(__import__("eco_ctl")._older("0.12.1", "0.12.1"))

    def test_snippet_points_at_the_script(self):
        r = self.ctl("snippet")
        self.assertEqual(json.loads(r.stdout)["statusLine"]["command"], STATUSLINE)

    def test_unknown_command(self):
        self.assertNotEqual(self.ctl("bogus").returncode, 0)


class Registration(unittest.TestCase):
    """hooks.json: the kill guard first on Bash, eco after it, and the eco
    command is the one these tests run."""

    def test_hooks_json(self):
        with open(os.path.join(HERE, "hooks.json")) as f:
            hooks = json.load(f)["hooks"]
        pre = hooks["PreToolUse"]
        self.assertIn("kill_guard.py", pre[0]["hooks"][0]["command"])
        self.assertEqual(pre[0]["matcher"], "Bash")
        eco_cmd = 'python3 -S "${CLAUDE_PLUGIN_ROOT}/hooks/eco_run.py"'
        self.assertEqual(pre[1]["matcher"], "Bash|Read")
        self.assertEqual(pre[1]["hooks"][0]["command"], eco_cmd)
        self.assertEqual(hooks["PostToolUse"][0]["matcher"], "Read|mcp__.*")
        for event in ("PostToolUse", "SessionStart", "PreCompact"):
            self.assertEqual(hooks[event][0]["hooks"][0]["command"], eco_cmd, event)
        self.assertEqual(HOOK_CMD[1:], ["-S", HOOK])


class Latency(EcoBase):
    """Acceptance: hook latency p95 ≤ 50 ms. Measured as Claude Code pays it —
    a fresh `python3 eco_hook.py` per call — against the stub runner, so the
    number is our overhead, not the runner's (the compiled runner adds ~20 ms
    on the calls it rewrites, the npm shim would add ~60)."""
    N = 40
    BUDGET_MS = 50.0

    def p95(self, payload, **env):
        e = dict(self.env)
        e.update(env)
        raw = json.dumps(payload)
        times = []
        for _ in range(self.N):
            t0 = time.perf_counter()
            subprocess.run(HOOK_CMD, input=raw, capture_output=True, text=True, env=e)
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        p95 = times[int(0.95 * (len(times) - 1))]
        sys.stderr.write("\n  %s p95 %.1f ms (median %.1f ms)\n" % (self.id().rsplit(".", 1)[-1], p95,
                                                                   times[len(times) // 2]))
        return p95

    def test_p95_off(self):
        big = self.write_file("big.md", big_text())
        self.assertLessEqual(self.p95(self.read(big)), self.BUDGET_MS)

    def test_p95_read_guard_on(self):
        self.eco_on()
        small = self.write_file("small.md", big_text(300))
        self.assertLessEqual(self.p95(self.read(small)), self.BUDGET_MS)

    def test_p95_bash_filter_on(self):
        self.eco_on()
        stub = os.path.join(self.bin, "agentdock-runner")
        with open(stub, "w") as f:  # a stub without the logging, as fast as a real exec
            f.write("#!/bin/sh\necho '{}'\n")
        self.assertLessEqual(self.p95(self.bash()), self.BUDGET_MS)


if __name__ == "__main__":
    unittest.main(verbosity=1)
