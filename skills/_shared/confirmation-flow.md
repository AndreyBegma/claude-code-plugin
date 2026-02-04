# Confirmation Flow

All user confirmations MUST use the `AskUserQuestion` tool (interactive selector), NOT text prompts.

**Important rules:**

1. Always output the numbered list of items as **plain text before** calling `AskUserQuestion`. The selector options must be **short and concise** — never repeat or embed the full item list inside option descriptions. The user sees both the text output and the selector together.
2. **Never add extra options** beyond what is specified below. Do NOT add "Select specific", "Pick items", or similar options — users who want specific items will type numbers in the built-in "Other" field. Adding extra options causes conflicts where typing `1` is ambiguous (option #1 vs item #1).

## Bulk Selection (with severity)

When presenting a numbered list of findings that have severity levels (CRITICAL / HIGH / MEDIUM / LOW), use `AskUserQuestion` with these options:

| Option | Description |
|--------|-------------|
| **All (Recommended)** | Process every item in the list |
| **Critical only** | Process only CRITICAL severity items |
| **High+** | Process CRITICAL + HIGH severity items |
| **None** | Skip entirely, process nothing |

The user can also type in the **"Other"** field:

- **Specific numbers:** `1 3` or `1, 3` — process only those items
- **Inverted selection:** `!3 5` — process all EXCEPT items #3 and #5

### Interpreting "Other" input

- Numbers `1 3` or `1, 3` → include only items #1 and #3
- Inverted `!2 4` or `!2, 4` → include all items EXCEPT #2 and #4
- Severity `critical` → same as "Critical only" option
- Severity `high+` → same as "High+" option

### Example

```
Found 5 issues:

1. [CRITICAL] SQL injection in UserService.ts:45
2. [HIGH] Missing auth guard on admin.controller.ts:23
3. [MEDIUM] Unused import in utils.ts:1
4. [LOW] Naming: prefer camelCase in config.ts:12
5. [HIGH] Hardcoded secret in config.ts:8
```

Then ask with AskUserQuestion:
- question: "Post 5 comments to GitHub?"
- options: All (Recommended) / Critical only / High+ / None
- multiSelect: false

| User picks | Result |
|------------|--------|
| All | Post all 5 |
| Critical only | Post #1 |
| High+ | Post #1, #2, #5 |
| Other: `!3 4` | Post #1, #2, #5 (all except #3 and #4) |
| Other: `2 5` | Post #2 and #5 |
| None | Skip |

## Bulk Selection (without severity)

When items don't have severity levels (e.g., resolved comments, extracted rules), use `AskUserQuestion` with:

| Option | Description |
|--------|-------------|
| **All (Recommended)** | Process every item |
| **None** | Skip entirely |

The user can type numbers (`1 3`) or inverted selection (`!2`) in "Other".

## Single-Item Confirmation

For previewing a single item before posting (comment, issue, PR), use `AskUserQuestion` with:

| Option | Description |
|--------|-------------|
| **Send (Recommended)** | Post/create as-is |
| **Edit** | Let user modify before posting |

## Binary Choice

For simple yes/no decisions (e.g., "Wait for CI?"), use `AskUserQuestion` with:

| Option | Description |
|--------|-------------|
| **Yes (Recommended)** | Proceed with the action |
| **No** | Skip |

Add contextual descriptions to each option explaining what happens.

## Three-Way Choice

For decisions with a third option (e.g., CI failure handling), use `AskUserQuestion` with up to 4 options. Example:

| Option | Description |
|--------|-------------|
| **View logs (Recommended)** | Show failed CI logs, then continue to review |
| **Skip logs** | Continue to review without viewing logs |
| **Cancel** | Stop the review entirely |
