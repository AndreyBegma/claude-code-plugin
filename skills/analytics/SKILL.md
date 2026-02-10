---
name: ca-analytics
description: Data-driven UX analysis from GA4/GSC — user flows, funnels, behavioral anomalies from real usage data
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, AskUserQuestion, mcp__puppeteer__*, mcp__playwright__*, mcp__browserbase__*
---

# Analytics — Data-Driven UX Analysis

Analyze GA4 and GSC CSV exports to find behavioral anomalies, conversion bottlenecks, and user flow problems. Every finding is backed by data evidence and formulas — no opinions.

**Reference**: See `_shared/seo-references.md` for GA4 file patterns and column detection.

## Inputs

`$ARGUMENTS`:

- `/path/to/ga4` — path to GA4 CSV exports (folder or file)
- `/path/to/ga4 /path/to/gsc` — GA4 + GSC exports (separate paths)
- `--url https://example.com` — remote mode (no local project access, Browser MCP required for flow replay)
- No arguments — scan current directory for CSV files

| Mode      | Has                  | Result                                                        |
| --------- | -------------------- | ------------------------------------------------------------- |
| Local     | GA4 + project        | Full analysis + flow replay on local/dev server               |
| Local+GSC | GA4 + GSC + project  | Full analysis with traffic × behavior cross-reference         |
| Remote    | GA4 + `--url`        | Full analysis + flow replay on live site                      |
| Remote+GSC| GA4 + GSC + `--url`  | Full analysis with traffic cross-reference on live site       |
| Data-only | GA4 only             | Metrics analysis only (no flow replay without URL or project) |
| GSC only  | GSC without GA4      | Error — suggest `/ca-seo-audit` instead                       |

## Step 1: Check Browser MCP

Check if Browser MCP is available. Try to use one of: `mcp__puppeteer__*`, `mcp__playwright__*`, or `mcp__browserbase__*`.

If **no browser MCP is available**, ask user to install:

Use `AskUserQuestion`:

- **question**: "Browser MCP enables replaying user flows and visual analysis of problem pages. Install it?"
- **options**:

| Option                    | Description                                                                   |
| ------------------------- | ----------------------------------------------------------------------------- |
| **Install (Recommended)** | Run `claude mcp add puppeteer -- npx -y @modelcontextprotocol/server-puppeteer` |
| **Skip**                  | Continue without browser — no flow replay, no visual analysis                 |

If user picks **Skip**, output warning and continue:

```
⚠️ Continuing without Browser MCP. Analytics will have limitations:
- No replay of user flows — can't verify what users actually experience
- No screenshots of problem pages
- No visual root cause analysis (hidden CTAs, layout issues, load times)
- Recommendations will be data-only, without visual confirmation
```

After installation, verify MCP is working by navigating to a test URL.

## Step 2: Detect & Parse Data

Scan provided paths (or current directory) for CSV files. Auto-detect type by column names (supports localized exports). See `_shared/seo-references.md` for GA4 file patterns.

**Determine mode**:

1. If `--url` provided → **Remote mode**. Use the URL for Browser MCP flow replay.
2. If no `--url` but local project detected (package.json, framework config) → **Local mode**. Detect dev server URL or build the site URL from config.
3. Otherwise → **Data-only mode**.

If **only GSC files** are found (no GA4):

```
❌ No GA4 data found. This skill requires GA4 exports for behavioral analysis.
→ For SEO analysis from GSC data, run: /ca-seo-audit
```

Stop execution.

**Output summary**:

```
Mode: Local / Remote (https://example.com) / Data-only
GA4: Landing Pages (45), Events (28), Sessions (12,340)
GSC: Queries (1,234), Pages (89) [if available]
Period: 2026-01-05 to 2026-02-04 | Sessions: 12,340 | Key Events: 1,456
```

## Step 3: Build User Journey Map

Trace the most common user paths through the site:

1. **Entry points**: Top landing pages by session count
2. **Navigation flows**: page_view sequences → identify the top 5-10 most common paths
3. **Exit points**: Where users leave — high exit rate pages
4. **Completion rates**: For each major flow, what % of users reach the intended destination

For each flow, show:
- Path: `Landing → Page A → Page B → Goal`
- Users who started: X
- Users who completed: Y
- **Completion rate**: `Y / X × 100 = Z%`
- **Drop-off point**: Where the biggest loss happens

## Step 4: Event Analysis

Analyze GA4 events to find engagement anomalies:

1. **Ghost buttons**: Elements with click events but near-zero conversion downstream → users click but nothing useful happens
2. **Conversion rates per event**: For each key event (form_submit, add_to_cart, sign_up), calculate `event_count / sessions × 100`
3. **Engagement anomalies**: Pages with high session count but low engagement time (< 10s) → content mismatch or UX problem
4. **Event sequence gaps**: Expected event chains (e.g., form_start → form_submit) where the second event is disproportionately low

For each finding:
- **Data**: exact numbers and percentages
- **Formula**: how the metric was calculated
- **Benchmark comparison**: if available, compare to typical rates

## Step 5: Traffic × Behavior Cross-Reference

If GSC data is available, correlate search traffic with on-site behavior:

1. **High-traffic, low-engagement pages**: High GSC clicks but GA4 engagement time < 10s or bounce rate > 80% → content doesn't match search intent
2. **High-converting, low-traffic pages**: GA4 pages with high conversion rates but few GSC impressions → SEO priority targets (improving rankings has direct revenue impact)
3. **Intent mismatch detection**: Compare top GSC queries driving traffic to a page with the page's actual GA4 behavior metrics. Flag pages where the search query intent doesn't match what users do on the page.

For each finding, show:
- Page URL
- GSC metrics: clicks, impressions, CTR, avg position
- GA4 metrics: sessions, engagement time, key events, conversion rate
- **Gap formula**: e.g., `CTR: 4.2% but engagement: 8s avg → intent mismatch score = clicks × (1 - engagement_rate)`

If no GSC data, skip this step with a note: "GSC data not available — skipping traffic cross-reference. Run `/ca-seo-audit` for search traffic analysis."

## Step 6: Conversion Funnel Analysis

Identify and analyze conversion funnels from GA4 event sequences:

1. **Auto-detect funnels**: Look for event chains that suggest a funnel (e.g., `page_view → form_start → form_submit`, `product_view → add_to_cart → begin_checkout → purchase`)
2. **Drop-off rates**: For each funnel step, calculate `users_at_step_N / users_at_step_1 × 100`
3. **Revenue impact**: For funnels with monetary value, estimate: `drop-off_users × avg_conversion_value = lost_revenue`
4. **Comparison**: If multiple funnels exist, compare their efficiency

For each funnel:

```
Funnel: [Name]
Step 1: [Event] — 1,000 users (100%)
Step 2: [Event] — 450 users (45%) ← 55% drop-off
Step 3: [Event] — 120 users (12%) ← 73% drop-off from Step 2
Overall conversion: 12%
Revenue impact: 880 lost users × $50 avg value = $44,000/month potential
```

Flag funnels with > 80% drop-off at any single step as CRITICAL.

## Step 7: Browser MCP — Replay User Flows & Visual Analysis

**Skip if no Browser MCP available.** In **Data-only mode** without `--url`, skip with note: "No site URL available for flow replay. Pass `--url` or run from a local project."

Use the site URL from Step 2 (either `--url`, detected local dev server, or project config). Replay the top user journeys discovered in Steps 3 and 6 through Browser MCP to see what real users experience. This is **not just screenshots** — walk through each flow step by step.

### 7a. Replay Top Funnels

For each top funnel from Step 6 (up to 3 funnels):

1. **Navigate** to the funnel entry page
2. **Screenshot** the initial state — what the user sees on landing
3. **Interact** with the page as the GA4 data suggests users do: click CTAs, fill forms, scroll to key sections
4. **Screenshot after each step** — capture what the user sees at every funnel stage
5. **Focus on drop-off points**: at the step where GA4 shows the biggest drop-off, carefully examine:
   - Is the next action obvious? Is the CTA visible without scrolling?
   - Does the page load quickly? Any layout shifts?
   - Are there distractions, confusing options, or friction (long forms, mandatory fields, login walls)?

### 7b. Replay Problem Paths

For pages flagged in Steps 3-5 (high exit rate, low engagement, intent mismatch — up to 5 pages):

1. **Navigate** to the page using the same entry path users take (e.g., from Google search result or referrer)
2. **Interact** as data suggests: scroll, click elements that have click events in GA4
3. **Screenshot** key moments: initial view, after scroll, after click
4. **Test ghost buttons** from Step 4: click elements that GA4 shows users click but get no conversion — document what actually happens

### 7c. Correlate Visual Findings with Data

For each replayed flow, connect what you see to the numbers:

- "Form has 12 fields — explains 73% drop-off between form_start and form_submit"
- "CTA is below 3 screen-folds of text — explains 3% click rate despite 2,000 sessions"
- "Page takes 4s to render main content — explains 8s avg engagement time (users leave before content loads)"
- "After clicking 'Get Started', user lands on a pricing page with no clear next step — explains exit rate spike"

Every visual observation must reference the specific data point from earlier steps.

## Step 8: Generate Recommendations

For each finding, generate a data-backed recommendation:

- **What to fix**: specific, actionable change
- **Evidence**: the data that supports this recommendation
- **Estimated impact formula**: quantified prediction
  - Example: `Current: 450 form_starts, 120 form_submits (26.7%). If simplified form improves to 40%: 450 × 0.40 = 180 submits (+60/month)`
- **Effort level**: LOW / MEDIUM / HIGH
- **Priority**: based on `estimated_impact / effort`

**Key principle**: Never recommend anything without data evidence. If the data doesn't support a conclusion, say so.

## Step 9: Generate Report

Structure the report in this exact order:

```markdown
# Analytics Report

**Site**: example.com | **Period**: Jan 5 – Feb 4, 2026 (31 days)

---

## Data Summary
GA4: Landing Pages (X), Events (Y), Sessions (Z)
GSC: Queries (X), Pages (Y) [if available]
Period: ... | Sessions: X | Key Events: Y | Overall Conversion: Z%

## User Journey Map
Top flows with completion rates. Visual flow diagram if possible.

## Engagement & Event Analysis
- Ghost buttons / dead-end interactions
- Conversion rates per event
- Engagement anomalies

## Traffic × Behavior (if GSC available)
- High-traffic / low-engagement pages
- High-converting / low-traffic pages (SEO priorities)
- Intent mismatch pages

## Conversion Funnels
Per funnel: steps, drop-off rates, revenue impact.

## Flow Replay & Visual Analysis (if Browser MCP available)
Per flow: step-by-step screenshots, interactions, visual root causes correlated with data.

## Top N Action Items (Priority Order)
Table with: #, Action, Evidence, Impact Formula, Effort, Priority.

## Methodology
Brief note on data sources, period, and any limitations.
```

---

## Important

- **Read-only** — this skill never modifies the target project
- **Data-driven** — every finding must cite specific numbers and formulas
- **No opinions** — if the data doesn't support a conclusion, don't make one
- **GA4 required** — GSC-only analysis should use `/ca-seo-audit` instead
- **Privacy** — all analysis local, nothing sent externally
- **Browser MCP optional** — enhances with visual analysis but not required
