# OMNI-RANK — End-to-End Test Plan

Three real-time test scenarios to exercise every feature of the app against a
running local stack (frontend + backend + Supabase). Run the steps in order and
tick the checkboxes.

**Keys required for the "green" (unflagged) steps:** Gemini + Serper + Firecrawl
+ Supabase. Steps marked 🔒 need extra connections (GA4/GSC, GitHub, Stripe).

**Timing:** AI steps (research, audit, competitor, content) run a live crawl +
LLM call and take **15–40s**. Watch the backend window for progress and errors.

---

## Test Data (real, content-rich domains)

| Set | Domain | Keywords | Competitors | Used in |
|---|---|---|---|---|
| **A — E-commerce** | `allbirds.com` | `wool running shoes`, `sustainable sneakers`, `merino shoes` | `rothys.com`, `atoms.com` | Scenario 1 |
| **B — SaaS** | `notion.so` | `note taking app`, `team wiki software`, `project management tool` | `evernote.com`, `clickup.com` | Scenario 2 |
| **C — Your site** | `surrvik.com` | your real keywords | your real rivals | any (real relevance) |

Sets A/B produce rich, verifiable output (large sites = lots of SEO data).
Set C shows results about your own site.

---

## Scenario 1 — Market Intelligence (Research & Discovery)

**Goal:** the research/analysis engines produce real, substantive output.
**Keys:** Gemini + Serper + Firecrawl.

- [ ] **1. Projects** — Create project `Allbirds Test`, URL `https://allbirds.com`.
  - Expected: project saved and selected; visible on dashboard.
- [ ] **2. AI Research** — URL `https://allbirds.com`, keyword `sustainable sneakers`.
  - Expected: multi-section report — content gaps, target keywords, page-level
    recommendations, summary. **Pass:** not empty / not an error.
- [ ] **3. Keywords** — Seed `wool running shoes`, domain `allbirds.com`.
  - Expected: 10–30 keyword ideas with volume, difficulty, intent, priority.
    **Pass:** ≥10 rows with scores.
- [ ] **4. Competitors** — Add `rothys.com`, then Analyze.
  - Expected: competitor strengths, content strategy, an outrank plan.
    **Pass:** strategy text generated.
- [ ] **5. AI Visibility** — Keywords `best sustainable sneakers`, domain
  `allbirds.com`, engine **Gemini**.
  - Expected: per-engine presence (cited/mentioned or not) + a visibility score.
    **Pass:** returns presence + score.

---

## Scenario 2 — Technical & Content Execution (Audit → Optimize)

**Goal:** crawl-based auditing and content generation work.
**Keys:** Gemini + Firecrawl + Serper.

- [ ] **1. Technical Audit** — URL `https://notion.so`; run audit / crawl.
  - Expected: score 0–100 + categorized issues (titles, meta, headings, mobile,
    speed, links) across the crawled pages. **Pass:** score + issue list.
- [ ] **2. Schema Markup (Detect)** — a Notion page URL; detect schema.
  - Expected: list of existing JSON-LD types found. **Pass:** types listed.
- [ ] **3. Schema Markup (Generate)** — page type Product/FAQ; generate.
  - Expected: valid, copyable JSON-LD block. **Pass:** well-formed JSON-LD.
- [ ] **4. Content Brief** — keyword `team wiki software`.
  - Expected: title options, H2/H3 outline, target keywords, word-count target,
    questions to answer. **Pass:** structured brief.
- [ ] **5. Content (Studio)** — generate a draft from the brief, then Score it.
  - Expected: draft article + SEO score with suggestions. **Pass:** draft + score.
- [ ] **6. Internal Linking** — analyze `notion.so`, view Opportunities.
  - Expected: suggested internal links (source → target, anchor) + orphan pages.
    **Pass:** opportunity list.
- [ ] **7. Programmatic** — template + list (e.g. cities); generate pages.
  - Expected: N generated page drafts from the template. **Pass:** ≥N drafts.

---

## Scenario 3 — Tracking, Reporting & Growth Ops

**Goal:** tracking, reporting, and ops features. 🔒 = needs extra setup.
**Keys:** Gemini + Serper (flagged items need more).

- [ ] **1. Rank Tracker** — add `wool running shoes` to the Allbirds project, check rank.
  - Expected: Google position (1–100 or "not in top 100") via Serper + a history
    point. **Pass:** position returned.
- [ ] **2. Reports** — generate a report for the Allbirds project.
  - Expected: HTML report (keywords, ranks, audit summary, wins). **Pass:** renders.
- [ ] **3. Dashboard / Wins** — view Overview after a project + data exist.
  - Expected: ROI / wins counter populates. **Pass:** `wins/summary` returns 200
    (was 400 with 0 projects).
- [ ] **4. Multilingual** — translate a content draft to Spanish.
  - Expected: localized version of the content. **Pass:** translated text.
- [ ] **5. Workflow / Autopilot** — set a weekly schedule, view runs.
  - Expected: schedule saved; run history list. **Pass:** schedule persists.
- [ ] **6. Branding / Settings** — set logo color / agency name, save.
  - Expected: settings persist across reload. **Pass:** values saved.
- [ ] 🔒 **7. Attribution** — needs GA4 + GSC OAuth (Settings → Connect).
  - Expected: revenue-per-keyword / per-page report.
- [ ] 🔒 **8. Git Write-back** — needs a GitHub PAT.
  - Expected: SEO fixes shipped as a pull request.
- [ ] 🔒 **9. Edge Injection** — generate an edge token, add the `<script>` to a site.
  - Expected: live SEO snippet injection.
- [ ] 🔒 **10. Billing** — needs Stripe/Razorpay keys.
  - Expected: plan upgrade / checkout flow.

---

## Running notes

- Watch the **backend window** during each AI step — it logs the work and any traceback.
- A step returning **400 "No projects found"** means: create/select a project first.
- If a step hangs or errors, capture the backend-window output for debugging.
- Don't assume a step is stuck before ~45s — live crawl + LLM is slow.

## Feature → endpoint reference

| Feature | Endpoint |
|---|---|
| AI Research | `POST /research/run` |
| Keyword research | `POST /keywords/research` |
| AI Visibility | `POST /geo/check`, `POST /projects/{id}/ai-visibility` |
| Technical Audit | `POST /audit/technical`, `POST /audit/crawl` |
| Schema | `POST /schema/detect`, `POST /schema/generate` |
| Content Brief / Score | `POST /content/brief`, `POST /content/score` |
| Internal Linking | `POST /linking/analyze`, `GET /linking/opportunities` |
| Programmatic | `POST /programmatic/generate` |
| Competitors | `POST /competitors/add`, `POST /competitors/{id}/analyze` |
| Rank check | `POST /projects/{id}/rank-check` |
| Reports | `POST` generate report, `GET` report HTML |
| Wins/ROI | `GET /wins/summary` |
| Attribution | `POST /attribution` (needs GA4/GSC) |
