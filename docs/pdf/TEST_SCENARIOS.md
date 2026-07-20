---
title: "OMNI-RANK · Test Scenarios"
---

<div class="cover">

# OMNI-RANK
<div class="subtitle">Test Scenarios — feature-by-feature</div>
<div class="accent-rule"></div>
<div class="meta">
QA pack with steps, sample data and expected results<br/>
Document version 1.0
</div>

</div>

# Contents

1. How to use this document
2. Environment preconditions
3. Sample data appendix
4. Onboarding
5. Projects
6. Monthly Workflow
7. AI Research
8. AI Keyword Research
9. Rank Tracker
10. AI Visibility
11. Revenue Attribution
12. Competitor Monitor
13. Technical SEO Audit
14. Schema Markup
15. Content Brief & Score
16. Content Studio
17. Programmatic SEO
18. Link Building
19. Reports
20. White-label Branding
21. Settings
22. Billing & Plans
23. End-to-end smoke test

# How to use this document

Each feature has a table with:

- **#** — scenario id (e.g. `RANK-03`).
- **Scenario** — short title.
- **Preconditions** — what must be true before starting.
- **Steps** — numbered actions in the UI.
- **Data inputs** — exact strings or files to use (see the appendix for re-used sets).
- **Expected result** — pass criteria.
- **Priority** — <span class="p-critical">Critical</span> / <span class="p-high">High</span> / <span class="p-medium">Medium</span> / <span class="p-low">Low</span>.

Priorities map to release gates:

- **Critical** — blocks release.
- **High** — must pass before promoting to staging.
- **Medium** — must pass before promoting to production.
- **Low** — nice to have; tracked but not blocking.

# Environment preconditions

Before running any scenario:

1. Backend env vars set (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ANTHROPIC_API_KEY`, `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`, `OMNI_API_KEY`). Razorpay vars required for Billing tests only.
2. Supabase migrations applied (`supabase/migrations/*.sql`).
3. Backend running on `http://localhost:8000`.
4. Frontend running on `http://localhost:3000` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
5. Browser logged in with API key matching `OMNI_API_KEY`.

# Sample data appendix

Reused across scenarios. Substitute `SAMPLE-*` tokens below for the corresponding value.

| Token | Value |
|---|---|
| `SAMPLE-DOMAIN` | `govindarestaurant.org` |
| `SAMPLE-URL` | `https://govindarestaurant.org/menu` |
| `SAMPLE-KEYWORD` | `pure veg restaurant chennai` |
| `SAMPLE-SEED` | `vegetarian restaurant` |
| `SAMPLE-NICHE` | `Restaurant` |
| `SAMPLE-REGION` | `India` |
| `SAMPLE-LANGUAGE` | `en-IN` |
| `SAMPLE-EMAIL` | `qa+omni@example.com` |
| `SAMPLE-API-KEY` | matches `OMNI_API_KEY` env var |
| `SAMPLE-CSV` | see Programmatic section below |
| `SAMPLE-MD-DRAFT` | see Content Studio section below |

# Onboarding

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| ONB-01 | First-run onboarding | Fresh browser, no localStorage | 1. Visit `/onboarding`. 2. Fill website, city, business type, keywords. 3. Click `Continue`. | Website: `SAMPLE-DOMAIN`. City: `Chennai`. Type: `Restaurant`. Keywords: `pure veg, thali, mini meals` | Redirected to `/dashboard`. Business profile chip appears in header. | <span class="p-critical">Critical</span> |
| ONB-02 | Skip onboarding | Fresh browser | 1. Visit `/onboarding`. 2. Click `Skip for now`. | — | Lands on `/dashboard` with empty state cards. | <span class="p-medium">Medium</span> |
| ONB-03 | Returning user bypass | localStorage has `businessProfile` | Visit `/onboarding` directly. | — | Auto-redirects to `/dashboard`. | <span class="p-high">High</span> |

# Projects

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| PRJ-01 | Create project (happy path) | Logged in | 1. `/dashboard/projects`. 2. `+ New Project`. 3. Fill form. 4. `Create Project`. | Name: `Govindas Chennai`. URL: `https://govindarestaurant.org`. Niche: `Restaurant`. Keywords: `pure veg chennai, thali, mini meals` | Toast `Project created`. New card appears in grid with accent strip. | <span class="p-critical">Critical</span> |
| PRJ-02 | Create with invalid URL | Logged in | 1. Open form. 2. URL = `not-a-url`. 3. Submit. | URL: `not-a-url` | Native HTML validation blocks submit. No POST sent. | <span class="p-high">High</span> |
| PRJ-03 | Set active project | At least 2 projects exist | 1. Click `Set active` on a non-active card. | — | Card gets `★ Active` pill + glow. Header chip updates. Toast confirms. | <span class="p-critical">Critical</span> |
| PRJ-04 | Delete project | At least 1 project | 1. Hover card. 2. Click trash icon. 3. Confirm. | — | Card removed from grid. Toast `Project deleted`. If it was active, header chip clears. | <span class="p-high">High</span> |
| PRJ-05 | Cancel delete | At least 1 project | 1. Click trash. 2. Cancel the browser confirm. | — | Card stays. No API call. | <span class="p-medium">Medium</span> |
| PRJ-06 | Active card auto-fills tools | Active project set | 1. Navigate to `/dashboard/research`. | — | Website + keyword fields pre-populated from active project. | <span class="p-high">High</span> |
| PRJ-07 | Empty state | No projects exist | Visit `/dashboard/projects`. | — | Shows empty-state card with `Create project` + `Run onboarding` buttons. | <span class="p-medium">Medium</span> |

# Monthly Workflow

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| WF-01 | Schedule renders current week | Project selected | 1. `/dashboard/workflow`. 2. Pick project. | — | Hero card shows current ISO week (W1/W2/W3/W4) with its accent colour and tasks list. | <span class="p-high">High</span> |
| WF-02 | Trigger run | Project selected | 1. Click `Run now`. | — | Toast `Workflow queued`. New row appears at top of run history within ~5s. | <span class="p-critical">Critical</span> |
| WF-03 | Failure shown | A sub-task is expected to fail (e.g. DataForSEO disabled) | 1. Trigger run. 2. Wait for completion. 3. Expand row. | — | Failing sub-task shows red X + error string. | <span class="p-high">High</span> |
| WF-04 | History limit | More than 10 runs exist | 1. Reload page. | — | Only 10 most-recent runs shown. | <span class="p-low">Low</span> |
| WF-05 | No project selected | No project | 1. Visit page without selecting. | — | Empty-state instructs the user to pick a project. | <span class="p-medium">Medium</span> |

# AI Research

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| RES-01 | Run a research job | Active project, Claude key set | 1. `/dashboard/research`. 2. Verify URL + keyword auto-filled. 3. Pick region + language. 4. `Start research`. | URL: `SAMPLE-URL`. Keyword: `SAMPLE-KEYWORD`. Region: `India`. Language: `en-IN` | Logs panel streams updates. Within ~90s, status flips to `completed`. Score, competitors, and recommendations render. | <span class="p-critical">Critical</span> |
| RES-02 | Missing Claude key | `ANTHROPIC_API_KEY` unset | 1. Submit form. | Same as RES-01 | Job returns status `failed` with helpful error message in logs. | <span class="p-high">High</span> |
| RES-03 | Cancel mid-run | Job started | 1. Start a job. 2. Reload the page. 3. Return to research. | — | Logs reconnect via job_id. No duplicate jobs. | <span class="p-medium">Medium</span> |
| RES-04 | Recommendations severity colours | Job completed | 1. Inspect recommendation list. | — | Each item carries a Critical / High / Medium tag with matching colour. | <span class="p-medium">Medium</span> |

# AI Keyword Research

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| KW-01 | Seed → opportunities | Claude + DataForSEO configured | 1. `/dashboard/keywords`. 2. Fill form. 3. `Find opportunities`. | Seed: `SAMPLE-SEED`. Domain: `SAMPLE-DOMAIN`. Industry: `Restaurant`. Region: `India` | Table renders within ~60s with ≥ 5 rows. Each row shows intent badge + priority bar. | <span class="p-critical">Critical</span> |
| KW-02 | Empty seed | — | 1. Leave seed blank. 2. Submit. | Seed: `` | Form validation blocks submit. | <span class="p-high">High</span> |
| KW-03 | Sort by priority | Results table visible | 1. Click priority column header. | — | Rows re-order descending; the same column header shows arrow. | <span class="p-medium">Medium</span> |
| KW-04 | Quick-fill chip | Active project has keywords | 1. Click a chip. | — | Seed input populates with the chip value. | <span class="p-low">Low</span> |

# Rank Tracker

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| RANK-01 | Add a keyword | Active project | 1. `/dashboard/rank-tracker`. 2. `+ Add keyword`. 3. Fill form. 4. Submit. | Keyword: `SAMPLE-KEYWORD`. Region: `India`. Primary: yes | New row in table. Position is `—` until first check. | <span class="p-critical">Critical</span> |
| RANK-02 | Run rank check | At least 1 keyword tracked | 1. Click `Check Rankings`. 2. Wait ~2 min. 3. Refresh table. | — | Position fills in with a number. Δ column populates after the second check. | <span class="p-critical">Critical</span> |
| RANK-03 | Sparkline renders | Keyword has ≥ 2 history rows | 1. Inspect sparkline column. | — | SVG line with green/red/grey colour reflecting trend direction. | <span class="p-high">High</span> |
| RANK-04 | Delete keyword | Keyword exists | 1. Click delete icon. 2. Confirm. | — | Row removed. Aggregate KPIs recompute. | <span class="p-medium">Medium</span> |
| RANK-05 | Top-10 KPI | ≥ 1 keyword ranks ≤ 10 | 1. Inspect KPI card. | — | Top-10 count reflects the dataset. | <span class="p-medium">Medium</span> |
| RANK-06 | Best mover KPI | ≥ 1 keyword improved by ≥ 5 positions | 1. Inspect KPI card. | — | Card shows the keyword with the biggest improvement. | <span class="p-low">Low</span> |

# AI Visibility

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| GEO-01 | Run a visibility sweep | LLM keys configured | 1. `/dashboard/ai-visibility`. 2. Fill form. 3. `Run GEO check`. | Domain: `SAMPLE-DOMAIN`. Keywords: `pure veg chennai\nthali near me\nmini meals chennai`. Engines: all 3. AI Mode: on | Score cards populate. Per-keyword matrix shows check / mention / absent per engine. | <span class="p-critical">Critical</span> |
| GEO-02 | One engine selected | LLM keys configured | 1. Uncheck Perplexity + Gemini. 2. Submit. | Engines: ChatGPT only | Other engine columns hidden (or marked `—`). | <span class="p-medium">Medium</span> |
| GEO-03 | 50+ keywords | — | 1. Paste 60 keywords. 2. Submit. | 60 lines of keywords | Form caps at 50 with a warning. | <span class="p-medium">Medium</span> |
| GEO-04 | Domain not cited anywhere | Use a brand-new domain not yet indexed | 1. Submit. | Domain: `notarealdomain123.test` | Citation rate `0%`. Each row shows `absent`. | <span class="p-low">Low</span> |

# Revenue Attribution

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| ATT-01 | Both connected (happy path) | GA4 + GSC connected for active project | 1. `/dashboard/attribution`. 2. Pick `30d`. 3. `Run report`. | Range: 30d | KPI strip + pages + queries tables populate. Revenue numbers are non-negative. | <span class="p-critical">Critical</span> |
| ATT-02 | Missing GA4 | Only GSC connected | 1. Open page. | — | Warning banner + button linking to Settings → Connect GA4. Run disabled. | <span class="p-high">High</span> |
| ATT-03 | Missing GSC | Only GA4 connected | 1. Open page. | — | Warning banner pointing to Settings → Connect GSC. Run disabled. | <span class="p-high">High</span> |
| ATT-04 | Range toggle persists | Connected | 1. Pick `90d`. 2. Reload. | — | Range selection persists for the session. | <span class="p-low">Low</span> |

# Competitor Monitor

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| CMP-01 | Empty state | Project has had no AI Research yet | 1. `/dashboard/competitors`. 2. Pick project. | — | Empty-state explains competitors are discovered via AI Research. | <span class="p-medium">Medium</span> |
| CMP-02 | First scan | Research has populated competitors | 1. Click `Scan Competitors`. 2. Wait ~2 min. 3. Refresh. | — | Cards appear with entities + content snapshot. KPI strip populates. | <span class="p-critical">Critical</span> |
| CMP-03 | Expand card | Cards present | 1. Click a card. | — | Entities, snapshot, and backlink profile slide in. | <span class="p-high">High</span> |
| CMP-04 | External link | Cards present | 1. Click the ↗ icon next to domain. | — | Opens the source URL in a new tab. | <span class="p-low">Low</span> |

# Technical SEO Audit

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| AUD-01 | Single-page audit | PageSpeed key configured | 1. `/dashboard/audit`. 2. Tab `Single-page`. 3. Submit. | URL: `SAMPLE-URL` | Lighthouse score cards render within ~30s. Issues list appears. | <span class="p-critical">Critical</span> |
| AUD-02 | Full-site crawl start | DataForSEO configured | 1. Tab `Full-site crawl`. 2. Submit. | Domain: `SAMPLE-DOMAIN`. Max pages: 50 | Status shows `crawling` with task id. | <span class="p-critical">Critical</span> |
| AUD-03 | Full-site crawl finishes | AUD-02 ran | 1. Wait. 2. Poll completes. | — | Status flips to `finished`. On-page score, broken links, duplicates, sample pages render. | <span class="p-high">High</span> |
| AUD-04 | Crawl with invalid domain | DataForSEO configured | 1. Submit. | Domain: `not_a_domain` | Status flips to `failed` with reason. | <span class="p-medium">Medium</span> |
| AUD-05 | Issue severity colours | Issues present | 1. Inspect badges. | — | Critical = red, High = orange, Medium = amber. | <span class="p-low">Low</span> |

# Schema Markup

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| SCH-01 | Detect + generate | LLM key configured | 1. `/dashboard/schema`. 2. Fill form. 3. `Analyze`. | URL: `SAMPLE-URL`. Type: `Restaurant`. Name: `Govindas Restaurant` | Detected types render. Missing types listed. Generated JSON-LD cards appear. | <span class="p-critical">Critical</span> |
| SCH-02 | Copy generated stub | SCH-01 produced output | 1. Click `Copy` on a stub. | — | Clipboard contains valid JSON-LD. Toast confirms. | <span class="p-high">High</span> |
| SCH-03 | URL fetch fails | — | 1. Submit unreachable URL. | URL: `https://offline.invalid` | Error toast / inline message; no markup generated. | <span class="p-medium">Medium</span> |

# Content Brief & Score

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| BRF-01 | Generate brief | Claude + SERP API configured | 1. `/dashboard/brief`. 2. Fill form. 3. `Generate brief`. | Keyword: `SAMPLE-KEYWORD`. Domain: `SAMPLE-DOMAIN` | Within ~60s: target words, H2 list, entities chips, FAQs, meta suggestions. Top-5 competitors table. | <span class="p-critical">Critical</span> |
| BRF-02 | Score a URL | Brief generated | 1. Paste a URL. 2. `Score`. | URL: `SAMPLE-URL` | Score /100 + per-axis breakdown + recommendations checklist. | <span class="p-critical">Critical</span> |
| BRF-03 | Score pasted markdown | Brief generated | 1. Paste markdown. 2. `Score`. | Use `SAMPLE-MD-DRAFT` below | Score renders the same way as URL scoring. | <span class="p-high">High</span> |
| BRF-04 | Copy brief as markdown | Brief generated | 1. Click `Copy as Markdown`. | — | Clipboard contains a well-formed markdown brief. | <span class="p-medium">Medium</span> |

**`SAMPLE-MD-DRAFT`** (paste into the markdown box for BRF-03):

```
# Pure Veg Restaurant in Chennai
Govindas serves pure-veg thalis and mini meals across Chennai.
## Menu highlights
- North Indian thali
- South Indian mini meals
- Daily specials
## Visit us
T Nagar branch open 11am-10pm.
```

# Content Studio

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| CON-01 | Create draft | Active project | 1. `/dashboard/content`. 2. `+ New Draft`. 3. Fill form. 4. Create. | Title: `Pure Veg Thali Guide`. Keyword: `SAMPLE-KEYWORD` | New draft appears in table with `draft` status. | <span class="p-critical">Critical</span> |
| CON-02 | Save markdown | Draft open | 1. Type markdown. 2. `Save`. | `SAMPLE-MD-DRAFT` | Word count updates live. Toast `Saved`. PATCH issued. | <span class="p-critical">Critical</span> |
| CON-03 | AI Rewrite | Draft has body, Claude key set | 1. Click `AI Rewrite`. 2. Wait. | — | Markdown rewritten. New word count differs. Diff visible. | <span class="p-high">High</span> |
| CON-04 | Status workflow | Draft open | 1. Change status to `review`. 2. Then `approved`. 3. Then `published`. | — | Each change is persisted. Status badge colour matches the value. | <span class="p-high">High</span> |
| CON-05 | Empty draft AI rewrite | Empty body | 1. `AI Rewrite`. | — | Form blocks request with `Add content first` toast. | <span class="p-medium">Medium</span> |

# Programmatic SEO

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| PRG-01 | Generate pages | Claude / Gemini configured | 1. `/dashboard/programmatic`. 2. Paste template. 3. Paste CSV. 4. Max pages = 50. 5. `Generate`. | Use `SAMPLE-CSV` below | Stats: rows = 4, generated = 4, skipped = 0. Page previews render with merged values. | <span class="p-critical">Critical</span> |
| PRG-02 | Unknown variable in template | — | 1. Use template with `{{nonexistent}}`. 2. Submit. | Template: includes `{{nonexistent}}` | Warning surfaces; per-row warnings list the unknown variable. | <span class="p-high">High</span> |
| PRG-03 | CSV without headers | — | 1. Paste data without a header row. 2. Submit. | Headerless CSV | Backend rejects with `header row required`. | <span class="p-medium">Medium</span> |
| PRG-04 | Cap at max pages | — | 1. Paste a 5000-row CSV. 2. Max pages = 10. | Big CSV | Only 10 pages generated. `Skipped` = 4990. | <span class="p-medium">Medium</span> |
| PRG-05 | Export JSON | Generation succeeded | 1. Click `Export JSON`. | — | Download starts. JSON parses; one record per page. | <span class="p-low">Low</span> |

**`SAMPLE-CSV`** (paste into the CSV textarea for PRG-01):

```
city,dish,price
Chennai,Thali,180
Bangalore,Thali,200
Hyderabad,Mini Meals,160
Mumbai,Mini Meals,210
```

**Template body suggestion:**

```
# Best {{dish}} in {{city}}
Govindas Restaurant serves {{dish}} starting at ₹{{price}} in {{city}}.
```

Slug template: `best-{{dish}}-in-{{city}}`. Title: `Best {{dish}} in {{city}} — Govindas`.

# Link Building

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| LNK-01 | Add prospect | Active project | 1. `/dashboard/links`. 2. Tab `Outreach Pipeline`. 3. Fill form. 4. `Add prospect`. | Domain: `chennaifoodblog.com`. URL: `https://chennaifoodblog.com/best-veg-2026`. Contact: `Anita R`. Email: `anita@chennaifoodblog.com`. DR: `42` | Row appears in table with `new` status. | <span class="p-critical">Critical</span> |
| LNK-02 | Status workflow | LNK-01 done | 1. Change row status to `contacted`. 2. Then `replied`. 3. Then `agreed`. 4. Then `placed`. | — | Each PATCH persists. Status pill colour matches. | <span class="p-high">High</span> |
| LNK-03 | Draft email | Prospect with email exists | 1. Click `Draft Email`. | Defaults: Sender Name: `Suresh`. Site: `SAMPLE-DOMAIN`. Value prop: `share a vegetarian directory`. Template: `guest_post` | Email card renders with non-empty Subject + Body. `Copy` button works. | <span class="p-critical">Critical</span> |
| LNK-04 | Filter by status | Multiple prospects | 1. Pick `agreed` from filter. | — | Only `agreed` rows visible. | <span class="p-medium">Medium</span> |
| LNK-05 | Live backlinks | DataForSEO configured | 1. Tab `Live Backlinks`. 2. Submit. | Domain: `SAMPLE-DOMAIN` | KPI strip + anchors + referring domains populate. | <span class="p-high">High</span> |
| LNK-06 | Track from referring domain | Backlinks loaded | 1. Click `+ track` on a referring domain row. | — | Prospect added with that domain prefilled. | <span class="p-medium">Medium</span> |
| LNK-07 | Delete prospect | Row exists | 1. Click trash icon. 2. Confirm. | — | Row removed. | <span class="p-medium">Medium</span> |

# Reports

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| RPT-01 | Generate a report | Active project, Claude configured | 1. `/dashboard/reports`. 2. `Generate Report`. | — | New row appears within ~60s. Click renders iframe with HTML. | <span class="p-critical">Critical</span> |
| RPT-02 | Download PDF | RPT-01 ran | 1. Open a report. 2. `Download PDF`. | — | PDF downloads. Opens in OS viewer without error. | <span class="p-high">High</span> |
| RPT-03 | Branding applied | Branding enabled for project | 1. Generate report. 2. Inspect cover. | — | Agency name + logo + palette match Branding config. | <span class="p-high">High</span> |
| RPT-04 | No reports | Fresh project | 1. Visit page. | — | Empty-state CTA `Generate Report`. | <span class="p-low">Low</span> |

# White-label Branding

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| BRA-01 | Save branding | Active project | 1. `/dashboard/branding`. 2. Enable. 3. Fill fields. 4. `Save branding`. | Agency: `Acme Digital`. Logo: `https://cdn.acme.com/logo.png`. Palette: defaults | Toast `Branding saved`. Validation block clean. | <span class="p-critical">Critical</span> |
| BRA-02 | Generate preview | Branding saved | 1. Click `Generate preview`. | — | Iframe renders sample report using saved settings. | <span class="p-critical">Critical</span> |
| BRA-03 | Validation warning | Insecure logo URL | 1. Logo: `http://acme.com/logo.png`. 2. Save. | Logo: HTTP not HTTPS | Save succeeds but `validation_warnings` lists the insecure URL. | <span class="p-high">High</span> |
| BRA-04 | Colour picker | Branding open | 1. Pick a hex via picker. | Primary: `#A3E635` | Hex field updates. Preview reflects new colour. | <span class="p-medium">Medium</span> |
| BRA-05 | Disable branding | Was enabled | 1. Uncheck Enable. 2. Save. | — | New reports stop using custom branding (verify via Reports). | <span class="p-high">High</span> |

# Settings

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| SET-01 | Update API key | — | 1. `/dashboard/settings`. 2. Type new key. 3. `Save`. | API key: `SAMPLE-API-KEY` | Stored in localStorage. Subsequent calls use it. | <span class="p-critical">Critical</span> |
| SET-02 | Connect GA4 | Google account with GA4 property | 1. `Connect GA4`. 2. Complete OAuth. | — | Card shows `Connected` + property id. | <span class="p-critical">Critical</span> |
| SET-03 | Connect GSC | Google account with GSC site | 1. `Connect GSC`. 2. Complete OAuth. | — | Card shows `Connected` + site URL. | <span class="p-critical">Critical</span> |
| SET-04 | Disconnect | GA4 connected | 1. `Disconnect`. | — | Card returns to `Not connected`. Attribution widget shows `—`. | <span class="p-high">High</span> |
| SET-05 | Attribution widget live | Both connected | 1. Reload. | — | Widget pulls last-7-day organic sessions / revenue / clicks. | <span class="p-high">High</span> |
| SET-06 | Wrong scope OAuth | Google account without GA4 access | 1. Connect. 2. Choose limited account. | — | Backend stores no usable token; error toast. | <span class="p-medium">Medium</span> |

# Billing & Plans

| # | Scenario | Preconditions | Steps | Data inputs | Expected result | Priority |
|---|---|---|---|---|---|---|
| BIL-01 | Usage bars render | At least 1 project + keywords | 1. `/dashboard/billing`. | — | 3 progress bars (Projects, Keywords, AI reports) with `used / limit` text. | <span class="p-high">High</span> |
| BIL-02 | Upgrade to Growth | Razorpay configured | 1. Click `Upgrade to Growth`. | Plan: `growth`. Email: `SAMPLE-EMAIL` | New tab opens with Razorpay checkout. Toast `Redirecting to Razorpay…`. | <span class="p-critical">Critical</span> |
| BIL-03 | Missing Razorpay creds | `RAZORPAY_KEY_ID` unset | 1. Click `Upgrade`. | — | Error toast surfaces backend `detail`. | <span class="p-high">High</span> |
| BIL-04 | Near-limit warning | Project count near limit | 1. Inspect bar. | — | Bar text turns amber when ≥ 80% of limit. | <span class="p-medium">Medium</span> |
| BIL-05 | Current plan badge | Plan = starter | 1. Inspect cards. | — | Starter card shows `Current` pill; its button is disabled. | <span class="p-medium">Medium</span> |

# End-to-end smoke test

This is the single must-pass walkthrough before any release.

| # | Step | Expected |
|---|---|---|
| 1 | Onboard with `SAMPLE-DOMAIN`, Chennai, Restaurant, 3 keywords. | Lands on `/dashboard`. |
| 2 | Create project `Govindas Chennai`. Set active. | Project active. |
| 3 | Open AI Research, accept auto-fill, submit. | Score + competitors + recommendations within 90s. |
| 4 | Open Keywords. Use seed `SAMPLE-SEED`. | Opportunities table populates. |
| 5 | Open Rank Tracker. Add `SAMPLE-KEYWORD`. Trigger check. | Position recorded within 2 min. |
| 6 | Open AI Visibility. Submit 3 keywords across all engines. | Citation matrix populated. |
| 7 | Open Audit. Single-page on `SAMPLE-URL`. | Lighthouse scores rendered. |
| 8 | Open Schema. Generate JSON-LD for `Restaurant`. | Stubs generated. |
| 9 | Open Brief. Generate + score. | Score /100 visible. |
| 10 | Open Content. Create + AI rewrite a draft. | Body changed; word count differs. |
| 11 | Open Programmatic. Generate 4 pages via `SAMPLE-CSV`. | 4 pages previewed. |
| 12 | Open Links. Add a prospect, draft an email. | Email card renders. |
| 13 | Open Reports. Generate, then download PDF. | PDF opens cleanly. |
| 14 | Open Branding. Enable + save + preview. | Iframe preview matches palette. |
| 15 | Open Settings. Verify GA4 + GSC connected. | Both green. |
| 16 | Open Attribution. Pick 30d, run. | Tables populated. |
| 17 | Open Billing. Verify usage bars + try Growth upgrade. | Razorpay tab opens. |

Any failure at any step blocks release.
