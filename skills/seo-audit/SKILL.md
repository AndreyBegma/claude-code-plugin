---
name: ca-seo-audit
description: SEO analysis from GSC/GA4 exports — finds quick wins, problems, and proposes code fixes for meta tags
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Edit, MultiEdit, AskUserQuestion, mcp__puppeteer__*, mcp__playwright__*, mcp__browserbase__*
---

# SEO Audit & Optimization

Analyze Google Search Console and GA4 CSV exports, identify optimization opportunities, propose code fixes.

**Reference**: See `_shared/seo-references.md` for CTR benchmarks, meta tag patterns, structured data templates.

## Inputs

`$ARGUMENTS`:

- `/path/to/metrics` — folder with GSC/GA4 CSV exports
- `--url https://example.com` — remote mode (no local project)
- `--compare /path/prev /path/curr` — compare two periods
- `--fix` — apply fixes (local mode only)

| Mode      | Has           | Result                     |
| --------- | ------------- | -------------------------- |
| Local     | CSV + project | Full analysis + code fixes |
| Remote    | CSV + `--url` | Analysis + recommendations |
| Data-only | CSV only      | Metrics analysis only      |

## Step 1: Check Browser MCP

Check if Browser MCP is available. Try to use one of: `mcp__puppeteer__*`, `mcp__playwright__*`, or `mcp__browserbase__*`.

If **no browser MCP is available**, ask user to install:

Use `AskUserQuestion`:

- **question**: "Browser MCP enables SERP screenshots and live site meta tag analysis. Install it?"
- **options**:

| Option                    | Description                                                                   |
| ------------------------- | ----------------------------------------------------------------------------- |
| **Install (Recommended)** | Run `claude mcp add puppeteer -- npx -y @modelcontextprotocol/server-puppeteer` |
| **Skip**                  | Continue without browser (limited in remote mode — can't fetch meta tags)       |

If user picks **Skip**, output warning and continue:

```
⚠️ Continuing without Browser MCP. SEO analysis will have limitations:
- No SERP screenshots
- No competitor title/description analysis
- Remote mode cannot fetch live meta tags
```

After installation, verify MCP is working by navigating to a test URL.

## Step 2: Detect & Parse Data

Scan folder for CSV files. Auto-detect type by column names (supports localized exports).

**Output summary**:

```
GSC: Queries (1,234), Pages (89), Devices (3), Countries (12)
GA4: Landing Pages (45), Events (28)
Period: 2026-01-05 to 2026-02-04 | Clicks: 12,456 | CTR: 2.73%
```

**Branded split**: Auto-detect brand from domain/package.json. Split queries into branded/non-branded with separate metrics.

**Period comparison** (if `--compare`): Calculate deltas, show gainers/losers.

## Step 3: Gather Context

**Local mode**: Detect framework (Next.js/Remix/Astro/Nuxt/SvelteKit), build URL→file mapping, find meta patterns.

**Remote mode**: Use Browser MCP to fetch meta tags from live pages (top 20 by impressions).

**Data-only**: Skip meta analysis, provide generic recommendations.

## Step 4: Calculate SEO Health Score (0-100)

| Factor                | Weight | How to score                                                                             |
| --------------------- | ------ | ---------------------------------------------------------------------------------------- |
| Avg Position          | 25%    | 25 if avg < 5, 20 if < 8, 15 if < 12, 10 if < 20, 5 if < 30, 0 if 30+                  |
| CTR vs benchmark      | 20%    | Per-page: compare actual CTR to `_shared/seo-references.md` benchmark for that position. Score = avg(actual/benchmark) × 20, capped at 20 |
| Mobile/Desktop parity | 15%    | 15 if gap < 20%, 10 if < 50%, 5 if < 100%, 0 if 100%+. Gap = abs(mobile_CTR - desktop_CTR) / min(mobile_CTR, desktop_CTR) |
| Zero-click pages      | 15%    | 15 if < 5% pages have 0 clicks, 10 if < 15%, 5 if < 30%, 0 if 30%+                      |
| Cannibalization       | 15%    | 15 if no clusters, 10 if 1-2 clusters, 5 if 3-5, 0 if 6+                                |
| Rich results %        | 10%    | 10 if structured data on 50%+ pages, 5 if on any page, 0 if none                        |

**Always show the scoring breakdown** in the report — show each factor's score and why, not just the total.

## Step 5: Identify Quick Wins

1. **Position 4-10** — almost top 3, small push needed
2. **High impressions, low CTR** — title/description not compelling
3. **Zero-click pages** — impressions but no clicks

For each quick win, show:

- Page URL, current title
- Current metrics: clicks, impressions, CTR, avg position
- **CTR gap**: compare actual CTR vs benchmark for that position (see `_shared/seo-references.md`)
- **Estimated gain with formula**: `monthly_impressions × (benchmark_CTR - current_CTR)`. Example: "4,693 impressions × (3.5% benchmark at pos 8 − 0.47% actual) = +142 clicks/month"
- Specific action (rewrite title, add structured data, etc.)

Always show the math — never give estimated gains without the calculation.

## Step 6: Detect Problems

1. **Cannibalization** — multiple pages for same query cluster → show all competing pages, which one should be canonical, and what to do with the rest (redirect, noindex, differentiate)
2. **Mobile gap** — if mobile CTR differs from desktop by > 50%, flag it. Suggest checking: title truncation on mobile, page speed, mobile UX
3. **Declining pages** — traffic drop (if `--compare`) → update content
4. **HTTP/WWW/param duplicates** — look for the same page URL appearing in GSC with different schemes (http/https), www/non-www, or query params. Sum up the split clicks to show wasted potential
5. **Missing meta tags** — if remote/local mode: check for missing or duplicate title tags, missing descriptions, descriptions over 160 chars, titles over 60 chars
6. **Content-intent mismatch** — pages with high impressions but CTR far below benchmark for their position → the search intent may not match what the page offers

## Step 7: Cross-Reference GA4

If GA4 data available, perform deep correlation — not just listing tables:

1. **Traffic-to-conversion mapping**: For each top GSC page, find GA4 metrics (sessions, engagement time, key events). Identify pages that get traffic but don't convert → recommend CTAs or internal links.
2. **High-converting pages with low traffic**: Find GA4 pages with high conversion rates but few GSC clicks → these are SEO priority targets (improving their rankings has direct revenue impact).
3. **Engagement quality**: Flag pages where GSC clicks are high but GA4 engagement time is very low (< 10s) → content quality or intent mismatch issue.
4. **Conversion funnel analysis**: If GA4 events show a funnel (form_start → form_submit), calculate drop-off rate and recommend simplification if > 80% drop-off.
5. **Revenue opportunity**: For high-converting pages, estimate the business value: "Improving this page from position 15 to position 8 could yield +X clicks/month × Y% conversion rate = Z additional leads/month".

## Step 7.5: Internal Linking Analysis

If local project is available, analyze internal link structure:

1. **Orphan pages**: Find high-value pages (by GA4 conversions) that have few or no internal links pointing to them
2. **Link from traffic to conversion**: Identify high-traffic low-conversion pages (e.g., blog posts) that could link to high-converting pages (e.g., product/destination pages). Recommend specific anchor text and placement.
3. **Hub pages**: Check if the site has category/hub pages that link to related content. If not, recommend creating them for major topic clusters.

## Step 8: Technical SEO Audit

Check in project or via Browser MCP:

- **robots.txt** — exists? blocking important paths? sitemap reference?
- **sitemap** — exists? dynamic? pages missing?
- **Canonical** — duplicates? missing tags?
- **Hreflang** — if i18n detected, check cross-references
- **Core Web Vitals** — if Browser MCP available, run Lighthouse. If not, recommend user check PageSpeed Insights and include a link: `https://pagespeed.web.dev/analysis?url={site_url}`
- **HTTP/HTTPS/WWW variants** — check GSC data for multiple URL variants of the same page (http:// vs https://, www vs non-www). Flag if clicks are split across variants — recommend 301 redirects to canonical.

## Step 9: SERP Analysis (with Browser MCP)

For top 5-10 queries:

1. Screenshot Google SERP
2. Compare your title/description vs competitors
3. Identify SERP features (snippets, PAA, videos)
4. Extract competitor patterns (numbers, year, brackets, length)

## Step 10: Generate Fixes

**Local**: Read file, show current meta, generate optimized version with rationale.

**Remote**: Show fetched meta, provide recommendations with example code.

For each page:

- Current title/description + issues
- Optimized meta (based on queries, CTR benchmarks, competitors)
- Structured data suggestion if applicable

## Step 11: Apply Fixes (--fix, local only)

If `--fix` in remote mode → warn and skip.

If `--fix` in local mode → Ask: "Apply SEO fixes? (X files)"

- **All** — apply all
- **Review each** — show diff, confirm per file
- **None** — skip

## Step 12: Generate Report

Structure the report in this exact order:

```markdown
# SEO Audit Report

**Site**: example.com | **Period**: Jan 5 – Feb 4, 2026 (31 days) | **Mode**: Local/Remote

---

## Data Summary
GSC: Queries (X), Pages (Y), Devices (Z), Countries (W)
GA4: Landing Pages (X), Events (Y)
Period: ... | Clicks: X | Impressions: Y | CTR: Z% | Avg Position: X

## Traffic Split (Device, Branded/Non-Branded, Top Countries)

## SEO Health Score: X/100
Show each factor with score AND reasoning (not just the number).

## Quick Wins (Estimated +X clicks/month)
For each: page, metrics, CTR gap formula, estimated gain, action.

## Problems Detected
Severity labels: CRITICAL / HIGH / MEDIUM. For each: what, why, impact.

## GA4 Cross-Reference
- High-traffic low-conversion pages (add CTAs)
- High-converting low-traffic pages (SEO priority)
- Conversion funnel drop-off analysis

## Internal Linking Opportunities (if local mode)
- Link high-traffic pages → high-converting pages
- Orphan high-value pages

## Technical SEO Audit
robots.txt, sitemap, canonical, OG tags, HTTP variants, Core Web Vitals link.

## Top N Action Items (Priority Order)
Table with: #, Action, Impact, Effort, Estimated Gain.

## Recommended Meta Tag Fixes
Per page: current → new title, current → new description, rationale.

## Structured Data Recommendations
Use templates from _shared/seo-references.md but customize with actual site data
(real page titles, real company name, real URLs — not generic placeholders).
```

---

## Important

- **Read-only by default** — `--fix` required for changes, confirmation always needed
- **Three modes** — Local (full), Remote (recommendations), Data-only (metrics)
- **Framework-aware** — uses appropriate meta patterns per framework
- **Privacy** — all analysis local, nothing sent externally
- **Browser MCP optional** — but critical for remote mode
