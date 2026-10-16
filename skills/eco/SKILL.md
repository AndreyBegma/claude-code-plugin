---
name: cs-eco
description: Token saver for the current Claude Code session — filters noisy command output through agentdock-runner (bypassPermissions and auto modes only), soft-guards whole reads of big files, soft-dedups repeated reads, cuts large MCP results to head and tail, injects a concise working register, and points broad searches at the haiku `scout` agent. Per session plus a machine default; reports status and savings
argument-hint: "[on|off|default on|off|status|stats [--all]|snippet]"
user-invocable: true
allowed-tools: Bash
---

# Token Saver

You switch the code-sentinel token saver on or off for **this session**, set
the machine default, and report status and savings. Everything runs through one
script; you do not reimplement anything it does.

## Arguments

`$ARGUMENTS` — exactly one of these forms. Anything else: print the list and
stop.

| Arguments | Command to run |
|---|---|
| *(none)* or `on` | `on` |
| `off` | `off` |
| `default on` / `default off` | `default on` / `default off` |
| `status` | `status` |
| `stats` / `stats --all` | `stats` / `stats --all` |
| `snippet` | `snippet` |

## Run it

Map the arguments to the command from the table, then run exactly this, as one
`Bash` call, substituting only `<command>` — never the arguments' raw text:

```sh
python3 "${CLAUDE_SKILL_DIR}/../../hooks/eco_ctl.py" <command> --session "${CLAUDE_SESSION_ID}"
```

Show the output to the person as it is, in a code block. Add nothing unless one
of these applies:

- **`on`** — the output ends with the working register. From now on follow it
  for the rest of the session: it is the instruction, not an example.
- **`command filter: unavailable (agentdock-runner not installed)`** — say that
  every other technique is on and that command filtering needs
  `npm i -g agentdock-runner`.
- **`early compaction: off`** — say it can only be set when Claude Code starts
  (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70 claude`); `/cs-orchestrator` workers get
  it automatically.
- **`snippet`** — say that the person pastes it into their own
  `~/.claude/settings.json` (or calls the script from their existing
  statusline). The plugin never edits settings, and the path changes when the
  plugin updates, so re-run `/cs-eco snippet` after an update.
- **`no session id`** — the Claude Code in use does not substitute
  `${CLAUDE_SESSION_ID}` into skills. Say so; nothing was changed. `default on`
  still works and takes effect for new sessions.

## What each technique does

| Technique | When eco is on |
|---|---|
| Command filter | `bun run test`, `tsc`, `git log`… run as `agentdock-runner filter -- …`, which keeps failures and drops noise. Only in `bypassPermissions` and `auto`; never in default, plan or acceptEdits. `AGENTDOCK_RAW=1 <cmd>` runs one command unfiltered |
| Read guard | A whole-file `Read` of a file over 400 lines is refused once with its size and an outline; repeating the same call reads it |
| Read dedup | A repeated `Read` of an unchanged range is refused once ("already in context since …"); repeating it reads it. Both reset at compaction |
| MCP cut | MCP results over 16,000 characters (`mcpMaxChars` in the config) become head + tail; the full text is saved and its path shown |
| Working register | Concise-answer instructions, injected once per session (again after compaction) |
| `code-sentinel:scout` agent | Haiku, read-only — broad searches and many-file reads return a conclusion, not dumps |
| Early compaction | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, read at launch; set by `/cs-orchestrator` for workers |
| Statusline | `eco-statusline.sh` — on/off, saving, context fill |

State: `${XDG_STATE_HOME:-~/.local/state}/cs-eco/`. Default:
`${XDG_CONFIG_HOME:-~/.config}/cs-eco/config.json`. Savings are JSONL rows in
AgentDock's `filter.stats` shape, per session.
