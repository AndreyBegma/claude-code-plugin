---
name: ca-ux-review
description: UX analysis and redesign proposals — identify friction, propose improvements with before/after mockups, measure impact in clicks/time saved
user-invocable: true
allowed-tools: Read, Grep, Glob, mcp__puppeteer__*, mcp__browserbase__*, mcp__playwright__*
---

# UX Review & Transformation

You are a UX analyst and designer. Analyze UI for friction points, propose redesigns with before/after comparisons, and measure impact in clicks/time saved.

## Inputs

`$ARGUMENTS` — one of:

- **URL**: `http://localhost:3000/users` — analyze specific page
- **Focus area**: `tables` / `forms` / `navigation` / `workflows` / `accessibility` / `loading` / `mobile` — focus on specific problem type
- **`full`**: Complete UX audit of the application

## Step 1: Gather Project Context

Before analysis, understand the project:

1. Read `package.json` — identify framework (Next.js, React, Vue, Angular, Svelte, Astro)
2. Read `CLAUDE.md` — check for existing UX guidelines or design system
3. Identify app type (adapt analysis accordingly):
   - **SaaS Dashboard** — data tables, forms, workflows (Linear, Notion patterns)
   - **E-commerce** — product cards, checkout flow, filters, cart (Shopify, Amazon patterns)
   - **Admin Panel** — CRUD operations, settings, user management (Retool patterns)
   - **Consumer App** — feed, engagement, social features (Twitter, Instagram patterns)
   - **Landing / Marketing** — conversion, CTA clarity, scroll flow, trust signals
   - **Documentation / Content** — readability, search, navigation hierarchy
   - **Marketplace** — listings, search, seller/buyer flows, trust indicators
   - **Developer Tool** — CLI output, config UX, error messages, onboarding
4. Check for UI library: Tailwind, MUI, Chakra, Radix, shadcn/ui, Ant Design, Bootstrap
5. Look for existing components in `src/components` or similar
6. Check for i18n setup (`next-intl`, `react-i18next`, `i18n/` folder) — if present, include i18n checks

## Step 2: Ensure Browser MCP Available

**Browser automation is REQUIRED for this skill.** UX review without visual inspection is incomplete.

### Check for Browser MCP

Try to use one of: `mcp__puppeteer__*`, `mcp__playwright__*`, `mcp__browserbase__*`

If **no browser MCP is available**, stop and ask user to install:

```
⚠️ Browser automation required for UX review.

This skill needs to open pages in a browser to:
- Take screenshots at different viewport sizes
- Test keyboard navigation
- Measure actual interactions
- Verify visual states (hover, focus, loading)

Install browser MCP to continue:
```

Use `AskUserQuestion`:

- **question**: "Install Puppeteer MCP to enable browser automation?"
- **options**:

| Option                    | Description                                                                   |
| ------------------------- | ----------------------------------------------------------------------------- |
| **Install (Recommended)** | Run `bunx @anthropic-ai/mcp-install@latest install puppeteer --client claude` |
| **Cancel**                | Stop UX review — cannot proceed without browser                               |

If user picks **Cancel**, output: "UX review cancelled. Browser automation is required for visual analysis." and stop.

After installation, verify MCP is working by navigating to a test URL.

## Step 3: Capture Current State

For each page/flow analyzed:

1. **Open URL in browser** — navigate to the target page
2. **Screenshot at multiple viewports**:
   - Desktop: 1440×900
   - Tablet: 768×1024
   - Mobile: 375×812
3. **Map user journey** — count clicks to complete task
4. **Test keyboard navigation** — Tab through page, check focus order
5. **Check interactive states** — hover, focus, active, disabled
6. **Read component code** — understand constraints, state management, loading states

```
Current State Analysis:
- Screenshots: [desktop], [tablet], [mobile]
- Task: [what user is trying to do]
- Current steps: [numbered list of clicks/actions]
- Total interactions: X clicks, ~Y seconds
- Keyboard navigable: Yes/No (issues: ...)
- Pain points: [list frustrations]
```

## Step 4: Identify Friction Categories

Evaluate against these friction types:

| Friction Type          | Question                                | Example                                     |
| ---------------------- | --------------------------------------- | ------------------------------------------- |
| **Step bloat**         | Can this be done in fewer clicks?       | 5 clicks to create item → should be 2       |
| **Context switching**  | Does user need to leave this page?      | Navigating away to look up data             |
| **Cognitive load**     | Is there too much to process?           | 20 fields visible at once                   |
| **Discovery**          | Is the action easy to find?             | Hidden in dropdown menu                     |
| **Feedback gap**       | Does user know what happened?           | No confirmation after save                  |
| **Error recovery**     | Can user easily fix mistakes?           | Must re-enter entire form                   |
| **Keyboard hostility** | Must user reach for mouse?              | Can't tab through table rows                |
| **Mobile unfriendly**  | Does it work on small screens?          | Horizontal scroll required                  |
| **Slow feedback**      | Does UI feel sluggish?                  | Full page reload on every action            |
| **Loading UX**         | What does user see while waiting?       | Blank screen or spinner instead of skeleton |
| **Inconsistency**      | Does it break established patterns?     | Different button styles on same page        |
| **Accessibility**      | Can everyone use it?                    | No focus indicators, missing labels         |
| **Transition gaps**    | Are state changes abrupt?               | Content pops in without animation           |
| **i18n readiness**     | Will it break with longer translations? | Fixed-width buttons clip translated text    |

## Step 5: Accessibility Audit

Check against WCAG 2.1 AA (adapt depth to app type):

### Keyboard Navigation

- All interactive elements reachable via Tab
- Logical tab order (follows visual layout)
- Focus indicators visible (not just `outline: none`)
- Skip-to-content link present
- Modal/dialog traps focus correctly
- Escape closes modals/dropdowns

### Screen Readers

- Images have meaningful `alt` text (not "image" or empty on meaningful images)
- Form inputs have associated `<label>` or `aria-label`
- Dynamic content uses `aria-live` regions
- Headings follow hierarchy (h1 → h2 → h3, no skipping)
- Buttons/links have descriptive text (not "click here")
- Icons have `aria-hidden="true"` or descriptive label

### Visual

- Color contrast meets 4.5:1 for text, 3:1 for large text
- Information not conveyed by color alone (error states need icons/text too)
- Text resizable to 200% without layout breaking
- Touch targets minimum 44x44px on mobile

### Motion

- Animations respect `prefers-reduced-motion`
- No auto-playing video/audio without controls
- No content that flashes more than 3 times per second

Output accessibility findings with severity:

- **CRITICAL**: Blocks usage entirely (can't submit form, can't navigate)
- **HIGH**: Major barrier (no focus management in modal, missing labels)
- **MEDIUM**: Degraded experience (poor contrast, small touch targets)
- **LOW**: Enhancement (missing skip link, suboptimal heading order)

## Step 6: Loading & Transition States

Evaluate how the app handles async operations:

| State                 | Bad                                 | Good                                               |
| --------------------- | ----------------------------------- | -------------------------------------------------- |
| **Initial load**      | Blank screen / full-page spinner    | Skeleton screens matching layout                   |
| **Data fetching**     | Spinner replacing all content       | Skeleton for loading parts, keep existing content  |
| **Form submit**       | Button does nothing, then redirects | Button shows loading state, disable, then feedback |
| **Navigation**        | Full page reload, white flash       | Route transition with progress indicator           |
| **Empty state**       | Blank area or "No data" text        | Helpful message + CTA to create first item         |
| **Error state**       | Generic "Something went wrong"      | Specific message + retry action + what to do       |
| **Partial failure**   | Entire page fails                   | Failed section shows error, rest works             |
| **Optimistic update** | Wait for server before UI change    | Update UI immediately, rollback on error           |

Check in code:

- Suspense boundaries / loading.tsx files (Next.js)
- Loading/error/empty state handling in components
- Skeleton components existence and usage
- Error boundaries

## Step 7: Propose Redesigns

For each friction point, propose a specific redesign using this format:

```markdown
## Redesign: [Feature Name]

### Problem

[1-2 sentences describing the friction]

### Current Journey

1. Click "Items" tab (1 click)
2. Click "Create" button (1 click)
3. Fill 15 form fields (15 interactions)
4. Click "Save" (1 click)
5. Wait for page reload
6. Navigate back (2 clicks)
   **Total: 20 interactions, ~3 minutes**

### Proposed Journey

1. Click "+" in table header (1 click)
2. Inline row appears with 4 essential fields
3. Press Enter to save (1 keypress)
4. Row animates into place
   **Total: 6 interactions, ~30 seconds**

### Before/After

**BEFORE:**
┌─────────────────────────────────────┐
│ Items [Create] │
├─────────────────────────────────────┤
│ Name │ Status │ Created │
│──────────│──────────│───────────────│
│ Item A │ Active │ 2024-01-15 │
│ Item B │ Draft │ 2024-01-14 │
└─────────────────────────────────────┘
↓ Click Create → Full page form

**AFTER:**
┌─────────────────────────────────────┐
│ Items [+] │
├─────────────────────────────────────┤
│ Name │ Status │ Created │
│──────────│──────────│───────────────│
│ Item A │ Active │ 2024-01-15 │
│ Item B │ Draft │ 2024-01-14 │
│ [____] │ [Select] │ [Auto] [✓][×] │ ← Inline add
└─────────────────────────────────────┘

### Impact

- **Clicks saved**: 14 (20 → 6)
- **Time saved**: ~2.5 minutes per item
- **Context preserved**: User stays on list
- **Keyboard friendly**: Tab + Enter workflow

### Implementation Hint

- Add `InlineCreateRow` component
- Use optimistic UI update
- Progressive disclosure for optional fields
```

---

## Design Patterns Library

### Pattern 1: Inline Editing

**Use when**: Creating or editing simple records in a list context
**App types**: SaaS, Admin, Marketplace

```
Instead of:                    Do this:
─────────────────────────────────────────────
Click row → Full page form     Click row → Expand inline
Navigate away                  Stay in context
Reload after save              Optimistic update
```

**Reference**: Notion, Airtable, Linear

### Pattern 2: Command Palette

**Use when**: Power users need quick access to actions
**App types**: SaaS, Developer Tools, Admin

```
Press Cmd+K → Search anything:
- "Create new user"
- "Go to settings"
- "Export as CSV"
- "Switch to dark mode"
```

**Reference**: Linear, Raycast, VS Code

### Pattern 3: Progressive Disclosure

**Use when**: Forms have many fields but most are optional
**App types**: Any

```
Essential fields visible:
┌────────────────────────┐
│ Name: [____________]   │
│ Email: [___________]   │
│ [+ Advanced options]   │ ← Expand for optional
└────────────────────────┘
```

**Reference**: GitHub issue creation, Stripe dashboard

### Pattern 4: Bulk Actions

**Use when**: User often performs same action on multiple items
**App types**: SaaS, Admin, E-commerce (orders), Marketplace

```
┌─────────────────────────────────────────┐
│ [☑] Select all         [3 selected]     │
│─────────────────────────────────────────│
│ [☑] Item A  │ Active   │ 2024-01-15     │
│ [☑] Item B  │ Draft    │ 2024-01-14     │
│ [☑] Item C  │ Active   │ 2024-01-13     │
│─────────────────────────────────────────│
│ [Delete]  [Export]  [Change Status ▼]   │
└─────────────────────────────────────────┘
```

**Reference**: Gmail, Notion, Figma

### Pattern 5: Keyboard-First Tables

**Use when**: Power users navigate data frequently
**App types**: SaaS, Admin, Developer Tools

```
Keyboard shortcuts:
- ↑/↓: Navigate rows
- Enter: Open detail / confirm
- e: Edit inline
- d: Delete (with confirmation)
- /: Filter/search
- Escape: Cancel/close
- Space: Toggle selection
```

**Reference**: Superhuman, Linear, vim

### Pattern 6: Smart Defaults

**Use when**: Most entries have predictable values
**App types**: Any

```
Auto-fill based on context:
- Date: Default to today
- Status: Default to "Draft"
- Owner: Pre-select current user
- Currency: Match user's locale
```

### Pattern 7: Skeleton Loading

**Use when**: Content takes >200ms to load
**App types**: Any

```
Loading:                       Loaded:
┌─────────────────────┐       ┌─────────────────────┐
│ ████████            │       │ John Smith           │
│ ██████████████      │       │ john@example.com     │
│                     │       │                      │
│ ████ ██████ ████    │       │ Edit  Settings  ...  │
└─────────────────────┘       └─────────────────────┘
```

**Reference**: Facebook, LinkedIn, Shopify

### Pattern 8: Optimistic Updates

**Use when**: Action has high success rate, feedback feels slow
**App types**: Any with server interactions

```
User clicks "Save"
  ↓
UI immediately shows success ← Don't wait for server
  ↓
Server confirms (or rollback if error)
```

**Reference**: Facebook, Twitter, any modern SPA

### Pattern 9: Contextual Actions

**Use when**: Actions depend on current selection/state
**App types**: SaaS, Admin, Marketplace

```
Nothing selected:        Row hovered:           Row selected:
[+ Create]              [Edit] [Delete] [...]   [Bulk actions bar]
```

**Reference**: Figma, Google Drive

### Pattern 10: Empty States with Action

**Use when**: List/table is empty
**App types**: Any

```
┌─────────────────────────────────────┐
│                                     │
│        No items yet                 │
│                                     │
│   Create your first item to get     │
│   started with the platform.        │
│                                     │
│        [+ Create Item]              │
│                                     │
└─────────────────────────────────────┘
```

**Reference**: Stripe, Linear, Notion

### Pattern 11: Micro-interactions

**Use when**: Actions need visual feedback beyond state change
**App types**: Consumer, E-commerce, SaaS

```
Hover:      Button lifts (shadow)  /  Row highlights
Click:      Ripple effect  /  Scale down briefly
Success:    Check animation  /  Green flash
Delete:     Slide out + collapse  /  Fade with undo
Toggle:     Smooth slide with color transition
Drag:       Item lifts, placeholder appears, snap to position
```

**Reference**: Material Design, Apple HIG, Stripe

### Pattern 12: Trust & Conversion Signals

**Use when**: User needs confidence to take action
**App types**: E-commerce, Landing, Marketplace

```
┌─────────────────────────────────────┐
│ [Complete Purchase]                 │
│                                     │
│ 🔒 Secure checkout (TLS encrypted) │
│ ↩️  30-day money-back guarantee     │
│ ⭐ 4.8/5 from 2,341 reviews        │
└─────────────────────────────────────┘
```

**Reference**: Shopify, Amazon, Stripe Checkout

---

## Common Problem Areas

### Tables

**Common issues:**

- Rows not keyboard navigable
- No bulk selection
- Click target is entire row (accidental clicks)
- No inline editing
- No column resizing/reordering
- Pagination instead of infinite scroll (or vice versa — depends on data size)

**Target state:**

- Arrow keys navigate, Enter opens
- Checkbox column for bulk ops
- Explicit action buttons per row
- Double-click or 'e' key for inline edit
- Responsive column priorities (hide less important on mobile)

### Forms

**Common issues:**

- All fields visible at once (overwhelming)
- Full page reload on save
- No autosave/draft
- Validation only on submit
- No field-level help text
- No loading state on submit button

**Target state:**

- Progressive disclosure (essential → optional)
- Inline validation as user types
- Autosave drafts periodically
- Optimistic UI updates
- Clear error messages with fix suggestions
- Submit button shows loading state + disables during submit

### Navigation

**Common issues:**

- Deep nesting (many clicks to reach content)
- Breadcrumbs as only way back
- No quick navigation
- No keyboard shortcuts
- Mobile nav is afterthought

**Target state:**

- Cmd+K command palette
- Recent items in sidebar
- Keyboard shortcuts for common pages
- Sticky header with key actions
- Responsive mobile-first nav

### Search & Filters

**Common issues:**

- Search requires exact match
- Filters hidden behind "Advanced"
- No saved searches
- Results don't highlight matches
- Slow/blocking search

**Target state:**

- Fuzzy search with typo tolerance
- Frequently used filters visible
- Save and name filter combinations
- Highlight matching text in results
- Debounced, non-blocking search

### Loading & Async

**Common issues:**

- Full-page spinner for any data fetch
- No skeleton screens
- Form submit blocks entire UI
- No error recovery (must reload page)
- Content layout shift when data loads

**Target state:**

- Skeleton screens matching final layout
- Inline loading indicators for partial updates
- Submit buttons with loading state
- Retry buttons on failed requests
- Reserved space to prevent layout shift

### Accessibility

**Common issues:**

- `outline: none` globally with no replacement focus style
- Interactive elements not reachable via keyboard
- Form inputs without labels (placeholder-only)
- Color as only indicator (red = error, green = success)
- Modals don't trap focus
- No skip-to-content link

**Target state:**

- Visible focus indicators on all interactive elements
- Full keyboard navigation with logical tab order
- All inputs have associated labels
- Icons/colors paired with text
- Focus trapped in modals, restored on close
- `aria-live` for dynamic content updates

---

## Output Format

```markdown
# UX Review: [Page/Flow Name]

**App**: [Project name]
**Type**: [App type from Step 1]
**Date**: YYYY-MM-DD
**Friction score**: X/10 (10 = unusable, 1 = excellent)

## Executive Summary

[2-3 sentences: main problems and key recommendations]

## Current State

- Task: [what user is trying to do]
- Current journey: X clicks, ~Y seconds
- Key pain points: [bullet list]

## Accessibility

- [CRITICAL/HIGH/MEDIUM/LOW] issues found
- Key findings: [list]

## Loading & Transitions

- [Issues with loading states, skeleton screens, feedback]

## Proposed Redesigns

### 1. [Redesign Name]

**Problem**: [friction description]
**Pattern**: [which pattern from library]

**Before**:
[ASCII mockup]

**After**:
[ASCII mockup]

**Impact**:
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Clicks | X | Y | -Z% |
| Time | Xm | Ym | -Z% |

**Implementation**:

- File: `src/components/...`
- Effort: S/M/L
- Dependencies: [other changes needed]

### 2. [Next Redesign]

...

## Prioritized Roadmap

| #   | Improvement | Impact | Effort | Priority   |
| --- | ----------- | ------ | ------ | ---------- |
| 1   | [Name]      | High   | Small  | Do first   |
| 2   | [Name]      | High   | Medium | Do second  |
| 3   | [Name]      | Medium | Large  | Plan later |

## Quick Wins

1. [Change] — [Impact]
2. [Change] — [Impact]

## Bigger Bets

1. [Change] — [Impact] — [Why worth it]
```

---

## Metrics to Track

After implementing redesigns:

| Metric               | How to Measure                   |
| -------------------- | -------------------------------- |
| Task completion time | Time from start to success       |
| Click count          | Interactions per task            |
| Error rate           | Failed attempts / total attempts |
| Keyboard usage       | % users using shortcuts          |
| Bounce rate          | % users abandoning mid-task      |
| Support tickets      | UX-related complaints            |
| User satisfaction    | NPS or task completion surveys   |
| Accessibility score  | Lighthouse / axe audit score     |
| Core Web Vitals      | LCP, FID, CLS                    |

---

## Important

- **Always show before/after** — proposals without visuals are hard to evaluate
- **Measure in clicks and seconds** — concrete numbers, not "better UX"
- **Adapt to app type** — don't suggest command palette for a landing page, or trust signals for an admin panel
- **Consider all states** — empty, loading, error, partial failure, success
- **Respect existing patterns** — don't break consistency for one improvement
- **Prioritize by impact/effort** — quick wins first, big bets with buy-in
- **Mobile matters** — test responsive behavior, check touch targets
- **Accessibility is not optional** — keyboard nav, screen readers, color contrast, focus management
- **i18n awareness** — if i18n is set up, check for layout breakage with longer translations, RTL readiness
- **Read-only** — this skill analyzes and reports, it does not modify project files
