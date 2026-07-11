---
title: "OMNI-RANK · Feature Guide"
---

<div class="cover">

# OMNI-RANK
<div class="subtitle">Feature Guide — every module, every flow</div>
<div class="accent-rule"></div>
<div class="meta">
AI SEO Platform · FastAPI + Next.js<br/>
Document version 1.0
</div>

</div>

# Contents

1. About this document
2. Architecture at a glance
3. External services
4. Onboarding & navigation
5. Overview (dashboard home)
6. Projects
7. Monthly Workflow
8. AI Research
9. AI Keyword Research
10. Rank Tracker
11. AI Visibility (GEO)
12. Revenue Attribution
13. Competitor Monitor
14. Technical SEO Audit
15. Schema Markup
16. Content Brief & Score
17. Content Studio
18. Programmatic SEO
19. Link Building
20. Reports
21. White-label Branding
22. Settings
23. Billing & Plans

# About this document

This guide describes every feature of OMNI-RANK as shipped on branch `claude/setup-omni-rank-local-9GOmi`. Each feature section follows the same template:

- **What it does** — the user goal it serves.
- **Where to find it** — sidebar location.
- **Inputs** — what the user provides.
- **Outputs** — what the user gets back.
- **Backend endpoints** — the FastAPI calls behind the UI.
- **External services** — Claude / Gemini / DataForSEO / GA4 / GSC / Razorpay / etc.
- **Flow** — a diagram or numbered walk-through.
- **Screenshot** — placeholder you can fill from your local app.

To add screenshots: drop PNG files into `docs/pdf/screenshots/` using the filenames referenced in each section, then run `make docs-pdf` from the repo root.

# Architecture at a glance

```
+--------------------+        +-----------------------+        +---------------------+
|  Next.js dashboard | <----> |  FastAPI app (Python) | <----> |  Supabase (Postgres)|
|  (App Router)      |        |  /app/api + services  |        |  + Storage          |
+--------------------+        +-----------+-----------+        +---------------------+
                                          |
                                          v
              +---------------------------+---------------------------+
              |                |                |                     |
        Claude / Gemini    DataForSEO    GA4 + GSC OAuth         Razorpay
        Groq / Perplexity  (SERP, on-page,  (revenue,            (subscriptions,
        (LLM agents)        backlinks)      queries)              INR billing)
```

The dashboard is a single React/Next.js app. Every page calls the FastAPI backend with the `X-API-KEY` header. The backend brokers all external service calls so secrets never reach the browser.

# External services

| Service | Used by | Purpose |
|---|---|---|
| Claude (Anthropic) | Research, Brief, Content, Schema, Link, Programmatic, Reports | Primary LLM for analysis, writing, scoring |
| Gemini | Research, Keyword, AI Visibility, Schema, Programmatic | Secondary LLM / fallback |
| Groq | Research, AI Visibility | Fast/cheap fallback LLM |
| Perplexity | AI Visibility | Citation tracking |
| DataForSEO | Keyword, Rank Tracker, Audit, Competitor, Link | SERP, on-page, backlink data |
| Google Analytics 4 | Revenue Attribution, Settings | Organic revenue + sessions |
| Google Search Console | Revenue Attribution, Settings | Query clicks + impressions + position |
| PageSpeed Insights | Technical Audit | Single-page Lighthouse scores |
| Razorpay | Billing | Subscriptions in INR |
| Firecrawl | Schema, Brief, Competitor (optional) | Page fetch + parsing |

# Onboarding & navigation

The sidebar groups modules into three areas:

- **COMMAND** — Overview, Projects, Workflow.
- **INTELLIGENCE** — AI Research, Keywords, Rank Tracker, AI Visibility, Attribution, Competitors.
- **EXECUTE** — Technical Audit, Schema Markup, Content Brief, Content Studio, Programmatic, Link Building, Reports.
- **Account** — White-label, Settings, Billing.

Each item carries its own electric accent colour. The active item shows a filled tile + glowing dot. The top of the sidebar holds the **OR** logo (violet → magenta gradient). The footer holds the **Light / Dark toggle** and **Log out**.

<div class="screenshot-placeholder">screenshots/sidebar.png — sidebar (dark + light mode)</div>

# Overview (dashboard home)

**What it does.** The home hub: shows the user's projects, keyword totals, latest jobs, and quick links into every other tool.

**Where to find it.** `/dashboard` (sidebar → Overview).

**Inputs.**

- Implicit: the user's API key + the active project from the app store.
- No form input.

**Outputs.**

- **KPI strip** with three switchable tabs (Projects / Keywords / Score).
- **Job activity feed** — most recent AI jobs, each with status badge (completed / running / failed), SEO score, "View" and "PDF" actions.
- **Weekly workflow badge** — current week (1–4) with its colour-coded SEO cadence.
- **Quick-action grid** — bento tiles linking to every major tool.

**Backend endpoints.**

- `GET /health`
- `GET /jobs`
- `GET /projects`
- `GET /projects/{id}/keywords` (count only)

**External services.** None directly. Claude is hit only via the health check.

**Flow.**

```
mount  ->  fetch /health      (status indicator)
       ->  fetch /projects    (KPI: project count)
       ->  fetch /jobs        (KPI: latest scores)
       ->  fetch keyword counts for top 3 projects
render KPIs + job feed + quick-actions
```

<div class="screenshot-placeholder">screenshots/overview.png — full dashboard hero + KPI + jobs feed</div>

# Projects

**What it does.** Create, view, activate, and delete SEO projects. The "active" project auto-fills every other tool's website / keyword inputs.

**Where to find it.** `/dashboard/projects`.

**Inputs.**

- **New Project modal** — Project Name, Website URL, Niche / Industry, Goal Keywords (comma-separated).
- Per-card actions: **Set active**, **Delete**.

**Outputs.**

- Card grid. Each card carries an electric accent strip (one of 8 colours, cycled), the project's domain, niche / city chips, goal keywords, current status badge, and a keyword count.
- The active project shows a coloured `★ Active` pill above its card.

**Backend endpoints.**

- `GET /projects`
- `POST /projects`
- `DELETE /projects/{id}`
- `GET /projects/{id}/keywords` (used only for the count badge)

**External services.** None.

**Flow.**

```
click "+ New Project"  ->  modal opens
fill form              ->  POST /projects
                       ->  toast "Project created"
                       ->  grid refreshes
click "Set active"     ->  app store updates businessProfile
                       ->  toast shows new active name
```

<div class="screenshot-placeholder">screenshots/projects.png — card grid with one active project</div>

# Monthly Workflow

**What it does.** A 4-week SEO cadence that runs automated tasks per week:

- **Week 1 — Technical**: re-crawl, schema, broken links.
- **Week 2 — Content**: briefs, content scoring, programmatic refresh.
- **Week 3 — Rankings**: rank check, AI Visibility sweep, competitor scan.
- **Week 4 — Links & Report**: outreach prospects, branded PDF report.

**Where to find it.** `/dashboard/workflow`.

**Inputs.** Project selector. `Run now` button.

**Outputs.**

- **Hero card** — current week + week colour + scheduled tasks.
- **Recent runs table** — each row is a workflow execution: week badge, status pill per sub-task, timestamps, expand for errors.

**Backend endpoints.**

- `GET /workflows/{project_id}/schedule`
- `POST /workflows/{project_id}/run`
- `GET /workflows/{project_id}/runs?limit=10`

**External services.** Claude (per agent), DataForSEO (rank check), optional Razorpay billing for usage.

**Flow.**

```
select project  ->  GET schedule (current week + tasks)
click "Run now" ->  POST /workflows/{id}/run
                ->  backend dispatches week-appropriate agents
                ->  polling /runs surfaces sub-task status
```

<div class="screenshot-placeholder">screenshots/workflow.png — hero card + run history</div>

# AI Research

**What it does.** Generates a deep competitive analysis for a URL + keyword: SEO score, top competitors, content gaps, and prioritised AI recommendations.

**Where to find it.** `/dashboard/research`.

**Inputs.**

- Website URL (auto-filled from active project).
- Primary keyword (auto-filled).
- Target region (India / US / UK / Singapore).
- Language (en-US / en-IN / hi-IN).

**Outputs.**

- **SEO Score** (/100, colour-coded).
- **Competitor profiles** with positions.
- **Content gap list**.
- **AI recommendations** tagged Critical / High / Medium.

**Backend endpoints.**

- `POST /jobs/research` — kicks off a job.
- `GET /jobs/{job_id}` — poll for completion + log stream.

**External services.** Claude (primary), Gemini / Groq (fallback), DataForSEO (SERP scrape).

**Flow.**

```
submit form    ->  POST /jobs/research      (returns job_id)
poll every 4s  ->  GET /jobs/{id}           (status: queued -> running -> completed)
on completion  ->  render score + competitors + gaps + recommendations
```

<div class="screenshot-placeholder">screenshots/research.png — score, competitors, recommendations</div>

# AI Keyword Research

**What it does.** Discovers high-intent keyword opportunities ranked by a priority score (volume × intent × winnability).

**Where to find it.** `/dashboard/keywords`.

**Inputs.**

- Seed keyword.
- Your domain.
- Industry / niche.
- Region.

**Outputs.**

- Opportunities table: Keyword · Volume · Difficulty · Intent badge · Priority bar.
- Quick-fill chips from the active project's keywords.

**Backend endpoints.** `POST /keywords/research`.

**External services.** Claude / Gemini (intent classification), DataForSEO (volume + difficulty).

<div class="screenshot-placeholder">screenshots/keywords.png — opportunities table</div>

# Rank Tracker

**What it does.** Tracks each tracked keyword's Google position over time. Surfaces deltas, sparklines, and a "best mover" KPI.

**Where to find it.** `/dashboard/rank-tracker`.

**Inputs.**

- Project selector.
- Add keyword form: keyword text, region, primary flag.

**Outputs.**

- Summary KPIs — average position, top-10 count, best mover.
- Keywords table — Position · Δ vs last check · Sparkline · Volume · Intent · Delete.

**Backend endpoints.**

- `GET /projects/{id}/keywords`
- `POST /projects/{id}/keywords`
- `DELETE /keywords/{id}`
- `POST /keywords/{id}/history?limit=12`
- `POST /keywords/rank-check`

**External services.** DataForSEO.

**Flow.**

```
add keyword       ->  POST /projects/{id}/keywords
click "Check"     ->  POST /keywords/rank-check
                  ->  backend queues DataForSEO scan
poll history      ->  POST /keywords/{id}/history (last 12 entries)
render sparkline
```

<div class="screenshot-placeholder">screenshots/rank-tracker.png — KPI strip + keyword rows with sparklines</div>

# AI Visibility (GEO)

**What it does.** Measures whether the domain shows up in Google AI Overviews and as a citation in ChatGPT / Perplexity / Gemini responses for given keywords.

**Where to find it.** `/dashboard/ai-visibility`.

**Inputs.**

- Domain.
- Keywords (one per line, max 50).
- Engine checkboxes (ChatGPT, Perplexity, Gemini).
- "Include Google AI Mode" toggle.

**Outputs.**

- Overall score, AI Overview coverage %, citation rate %, per-engine mention rates.
- Per-keyword table with check / mention / absent icons per engine.

**Backend endpoints.** `POST /ai-visibility/geo-check`.

**External services.** Claude, Gemini, Groq, Perplexity, Google Search (AIO detection).

<div class="screenshot-placeholder">screenshots/ai-visibility.png — scores + keyword visibility matrix</div>

# Revenue Attribution

**What it does.** Merges GA4 (revenue + sessions) with GSC (queries + clicks + impressions) to show which keywords and pages drive organic revenue.

**Where to find it.** `/dashboard/attribution`.

**Inputs.**

- Date range (7d / 30d / 90d).
- Pre-requisite: GA4 + GSC connected via Settings.

**Outputs.**

- Stat cards: organic revenue, organic sessions, GSC clicks, average position.
- Top pages table (with revenue per page).
- Top queries table (with revenue attribution + CTR + position).

**Backend endpoints.**

- `POST /analytics/attribution-report`
- (internally calls GA4 Data API + GSC Search Analytics API using stored tokens)

**External services.** GA4, GSC, optional Claude for prioritisation.

**Flow.**

```
ensure GA4 + GSC connected (Settings)  ->  store tokens
pick date range                         ->  POST /analytics/attribution-report
                                        ->  backend pulls GA4 + GSC, joins on landing page
render KPI strip + tables
```

<div class="screenshot-placeholder">screenshots/attribution.png — KPI strip + pages + queries tables</div>

# Competitor Monitor

**What it does.** Tracks competitor pages discovered during AI Research. Captures content, top entities, and backlink profile changes over time.

**Where to find it.** `/dashboard/competitors`.

**Inputs.** Project selector. `Scan Competitors` button.

**Outputs.**

- KPI strip — competitors tracked, pages indexed, entities mapped.
- Expandable competitor cards: domain, capture date, top entities (purple chips), content snapshot, backlink profile snippet.

**Backend endpoints.**

- `GET /competitors/{project_id}`
- `POST /competitors/{project_id}/scan`

**External services.** Claude / Gemini (entity extraction), DataForSEO (backlinks), Firecrawl (optional).

<div class="screenshot-placeholder">screenshots/competitors.png — cards expanded showing entities + content snapshot</div>

# Technical SEO Audit

**What it does.** Two modes:

1. **Single-page audit** — Lighthouse (Performance, Accessibility, Best Practices, SEO) + flagged issues.
2. **Full-site crawl** — DataForSEO on-page audit across many pages with broken-link detection, duplicate titles, and per-page on-page scores.

**Where to find it.** `/dashboard/audit`.

**Inputs.**

- Tab 1: URL.
- Tab 2: Domain + max pages (10–1000).

**Outputs.**

- Lighthouse score cards.
- Issues accordion with severity badges (Critical / High / Medium).
- Crawl status (crawling / finished / failed) + on-page score.
- Broken links table, duplicate-titles list, sample pages table.

**Backend endpoints.**

- `POST /audit/single-page`
- `POST /audit/crawl/start`
- `GET /audit/crawl/{task_id}` (poll ~ 6 s)

**External services.** PageSpeed Insights, DataForSEO On-Page.

<div class="screenshot-placeholder">screenshots/audit.png — Lighthouse scores + crawl results</div>

# Schema Markup

**What it does.** Detects existing JSON-LD on a page, identifies missing schema types for the business model, and generates ready-to-paste markup.

**Where to find it.** `/dashboard/schema`.

**Inputs.**

- URL.
- Business type dropdown (Default, Local Business, Restaurant, E-commerce, SaaS, Publisher, Agency).
- Business name (optional).

**Outputs.**

- Stats: blocks found, types detected, missing recommended, generated stubs.
- Detected types (green badges) + missing types (amber badges).
- Generated JSON-LD blocks with `Copy` button.

**Backend endpoints.** `POST /schema/detect`.

**External services.** Claude / Gemini, optional Firecrawl.

<div class="screenshot-placeholder">screenshots/schema.png — detected + missing + generated markup cards</div>

# Content Brief & Score

**What it does.** Two halves:

1. **Brief** — pulls top 5 SERP competitors, returns target word count, recommended H2 outline, entities to cover, FAQs, meta suggestions.
2. **Score** — scores a URL or pasted markdown against the brief on length / headings / entities / questions / keyword use.

**Where to find it.** `/dashboard/brief`.

**Inputs.**

- Target keyword.
- Your domain (optional).
- Score mode: URL or pasted markdown.

**Outputs.**

- Brief block with H2s, entities, questions, meta.
- Top competitors table.
- Score card (/100) + breakdown + improvement recommendations.

**Backend endpoints.**

- `POST /brief/generate`
- `POST /brief/score`

**External services.** Claude, DataForSEO / Serper for SERP.

<div class="screenshot-placeholder">screenshots/brief.png — brief + score panels</div>

# Content Studio

**What it does.** Manages article drafts with a Markdown editor, status workflow (draft → review → approved → published), and one-click AI rewrite via Claude.

**Where to find it.** `/dashboard/content`.

**Inputs.**

- Project selector.
- New Draft form (title, target keyword, optional markdown).
- Editor: title, keyword, markdown, status dropdown.

**Outputs.**

- Drafts table (title, keyword, word count, status, publish target).
- Editor with live word count, AI Rewrite button, Save button.

**Backend endpoints.**

- `GET /content/{project_id}`
- `POST /content/{project_id}`
- `PATCH /content/{draft_id}`
- `POST /content/{draft_id}/rewrite`

**External services.** Claude Sonnet.

<div class="screenshot-placeholder">screenshots/content.png — drafts list + editor side-by-side</div>

# Programmatic SEO

**What it does.** Generates hundreds of pages from a single template + a CSV dataset. Variables are `{{column_name}}` placeholders in the template.

**Where to find it.** `/dashboard/programmatic`.

**Inputs.**

- Template fields: name, slug template, title template, meta description, H1, body (markdown).
- CSV pasted into textarea (first row = headers).
- Max pages (1–5000).

**Outputs.**

- Stats: rows · generated · skipped · variables used.
- Warnings list.
- Page previews (slug, title, meta, per-row warnings).
- "Export JSON" button.

**Backend endpoints.** `POST /programmatic/generate`.

**External services.** Claude / Gemini (validation).

<div class="screenshot-placeholder">screenshots/programmatic.png — template editor + CSV + results panel</div>

# Link Building

**What it does.** Two tabs:

1. **Outreach Pipeline** — kanban-style prospect tracker (new → researching → contacted → replied → agreed → placed → declined). Each row can generate a personalised outreach email via AI.
2. **Live Backlinks** — pulls a DataForSEO backlink profile for any domain. Top anchors and referring domains are shown; each referring domain has a "+ track" button to add as a prospect.

**Where to find it.** `/dashboard/links`.

**Inputs.**

- Tab 1: Add prospect form (Domain, URL, Contact, Email, Domain Rating). Email defaults section (Sender name, Sender site, Value prop, Template).
- Tab 2: Domain + Fetch Profile.

**Outputs.**

- Prospects table with inline status dropdown + Draft Email + Delete.
- Draft email card (Subject + Body + Copy).
- Backlink profile KPIs + anchor / domain tables.

**Backend endpoints.**

- `GET /prospects/{project_id}` (optionally `?status=`)
- `POST /prospects/{project_id}`
- `PATCH /prospects/{prospect_id}`
- `DELETE /prospects/{prospect_id}`
- `POST /prospects/{prospect_id}/draft-email`
- `POST /backlinks/profile`

**External services.** Claude / Gemini, DataForSEO.

<div class="screenshot-placeholder">screenshots/links.png — pipeline + email draft + backlink stats</div>

# Reports

**What it does.** Generates branded PDF SEO reports per project; lets the user view past reports inline or download as PDF.

**Where to find it.** `/dashboard/reports`.

**Inputs.** Project selector. "Generate Report" button.

**Outputs.** Report list + inline HTML viewer + Download PDF.

**Backend endpoints.**

- `GET /reports/{project_id}`
- `POST /reports/{project_id}/generate`
- `GET /reports/{project_id}/{report_id}/html`

**External services.** Claude, optional Puppeteer for PDF render.

<div class="screenshot-placeholder">screenshots/reports.png — report list + viewer iframe</div>

# White-label Branding

**What it does.** Customise the agency name, logo, palette, and cover copy used on every report for a given project. Renders a live preview.

**Where to find it.** `/dashboard/branding`.

**Inputs.**

- Enable toggle.
- Agency name, logo URL, website, contact email.
- Colour pickers (Primary, Secondary, Accent, Text, Background).
- Cover title, cover subtitle, footer text.

**Outputs.**

- Validation warnings (e.g. logo URL not https).
- Live preview iframe rendering a sample branded report.

**Backend endpoints.**

- `GET /projects/{id}/branding`
- `POST /projects/{id}/branding`
- `POST /projects/{id}/branding/preview`

**External services.** None.

<div class="screenshot-placeholder">screenshots/branding.png — form + live preview side-by-side</div>

# Settings

**What it does.** API key management, business profile summary, GA4 + GSC OAuth connections.

**Where to find it.** `/dashboard/settings`.

**Inputs.**

- API key field (password input).
- Connect / Disconnect buttons for GA4 and GSC.

**Outputs.**

- Business profile read-only card.
- GA4 connection card (status, property ID).
- GSC connection card (status, site URL).
- Attribution Overview widget (live numbers when both connected).

**Backend endpoints.**

- `GET /analytics/ga4/auth-url?project_id={id}`
- `GET /analytics/gsc/auth-url?project_id={id}`
- `POST /analytics/exchange-token`

**External services.** Google OAuth, GA4 API, GSC API.

<div class="screenshot-placeholder">screenshots/settings.png — API key + GA4 + GSC + attribution widget</div>

# Billing & Plans

**What it does.** Shows the current plan + monthly usage (projects, keywords, AI reports) vs limits. Lets the user upgrade to Starter / Growth / Agency via Razorpay checkout (INR).

**Where to find it.** `/dashboard/billing`.

**Inputs.** Plan card "Upgrade" button per plan.

**Outputs.**

- Current Plan card (plan, price, renewal status).
- Usage card with progress bars per metric.
- Three plan cards with features + Upgrade button. "Most popular" pill on Growth. "Current" pill on the active plan.
- Razorpay setup note for backend env config.

**Backend endpoints.**

- `GET /billing/usage`
- `POST /billing/subscribe?plan={id}&email={email}` — returns Razorpay `checkout_url`.

**External services.** Razorpay.

**Flow.**

```
mount       ->  GET /billing/usage  (count projects, keywords, reports)
click plan  ->  POST /billing/subscribe?plan=growth&email=...
            ->  open returned checkout_url in new tab (Razorpay)
            ->  user completes payment in Razorpay
            ->  webhook (server-side) updates plan
```

<div class="screenshot-placeholder">screenshots/billing.png — current plan + usage + 3 plan cards</div>
