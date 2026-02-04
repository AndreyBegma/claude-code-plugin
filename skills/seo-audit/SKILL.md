---
name: ca-seo-audit
description: SEO analysis from GSC/GA4 exports — finds quick wins, problems, and proposes code fixes for meta tags
user-invocable: true
allowed-tools: Read, Grep, Glob, Edit, MultiEdit, mcp__puppeteer__*, mcp__playwright__*, mcp__browserbase__*
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

Try `mcp__puppeteer__*`, `mcp__playwright__*`, or `mcp__browserbase__*`.

**If not available** → Ask: "Browser MCP enables SERP screenshots and live site analysis. Install it?"

- **Install** → `bunx @anthropic-ai/mcp-install@latest install puppeteer --client claude`
- **Skip** → Continue with warning (limited in remote mode — can't fetch meta tags)

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

| Factor                | Weight |
| --------------------- | ------ |
| Avg Position          | 25%    |
| CTR vs benchmark      | 20%    |
| Mobile/Desktop parity | 15%    |
| Zero-click pages      | 15%    |
| Cannibalization       | 15%    |
| Rich results %        | 10%    |

## Step 5: Identify Quick Wins

1. **Position 4-10** — almost top 3, small push needed
2. **High impressions, low CTR** — title/description not compelling
3. **Zero-click pages** — impressions but no clicks

For each: show page, query, current metrics, estimated gain, action.

## Step 6: Detect Problems

1. **Cannibalization** — multiple pages for same query → consolidate
2. **Mobile gap** — significant mobile vs desktop difference → check speed/UX
3. **Declining pages** — traffic drop (if `--compare`) → update content

## Step 7: Cross-Reference GA4

If GA4 data available: correlate GSC clicks with bounce rate, engagement time, conversions. Flag high-bounce pages with search traffic.

## Step 8: Technical SEO Audit

Check in project or via Browser MCP:

- **robots.txt** — exists? blocking important paths? sitemap reference?
- **sitemap** — exists? dynamic? pages missing?
- **Canonical** — duplicates? missing tags?
- **Hreflang** — if i18n detected, check cross-references

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

```markdown
# SEO Audit Report

**Site**: example.com | **Period**: 31 days | **Score**: 67/100

## Summary

- Quick Wins: 12 (+3,400 clicks/mo potential)
- Problems: 8 | Technical Issues: 3 | Fixes: 15 files

## Traffic Split

Branded: 67% | Non-branded: 33%

## Top Actions

1. Fix /pricing meta — +800 clicks
2. Resolve cannibalization — 3 pages competing
3. Mobile optimization — 38% gap

## [Sections: Quick Wins, Problems, Technical, SERP, Fixes, Roadmap]
```

---

## Important

- **Read-only by default** — `--fix` required for changes, confirmation always needed
- **Three modes** — Local (full), Remote (recommendations), Data-only (metrics)
- **Framework-aware** — uses appropriate meta patterns per framework
- **Privacy** — all analysis local, nothing sent externally
- **Browser MCP optional** — but critical for remote mode
