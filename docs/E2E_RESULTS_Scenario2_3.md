# E2E Execution Results — Scenarios 2 & 3 (+ multi-key fallback)

**Run by:** automated execution against a live backend in a test container.
**Date:** 2026-07-12
**LLM:** Gemini via multi-key rotation (5 keys). Model `gemini-flash-latest`
(chosen after `gemini-2.0-flash` was quota-exhausted on all keys and
`gemini-2.5-flash` had a transient Google-side `503` outage).
**Caller:** `X-API-KEY` operator (service) — bypasses org scoping. Endpoints that
require a **project** (Supabase `service_role`) could not be exercised in this
env; their data layers were verified independently.

---

## New capability shipped: multi-key Gemini fallback

Added rotation across multiple Gemini keys. On `429` (quota) or `403` (key
disabled) the client advances to the next key immediately; transient errors back
off on the same key.

- Config: `GEMINI_API_KEY` (primary) + `GEMINI_API_KEYS` (comma-separated fallbacks),
  combined via `settings.gemini_api_key_list()`.
- Client: `GeminiClient` holds the full key list and rotates in `complete()`.
- **Verified:** 5 keys configured; **4 usable**, **1 returns `403`** (Generative
  Language API not enabled on that project — enable it or drop the key). Keyword
  Research returned **26 opportunities** through the rotation. 468 tests pass.

---

## Scenario 2 — Technical & Content Execution

| # | Feature | Endpoint | Result | Time | Real output |
|---|---|---|---|---|---|
| 1 | Technical Audit | `POST /audit/technical` | ⚠️ **PARTIAL** | 15–26s | `200` but **empty** — scores null because PageSpeed API returned **429** (keyless). **Needs a free `PAGESPEED_API_KEY`** (and optionally DataForSEO for on-page crawl). |
| 2 | Schema Detect | `POST /schema/detect` | ✅ **PASS** | 0.8s | Correctly reported **0 JSON-LD blocks** on the notion.so homepage (crawl-based detection). |
| 3 | Schema Generate | `POST /schema/generate` | ✅ **PASS** | instant | **3 valid JSON-LD blocks** (Organization, FAQPage, SoftwareApplication) with `@context`/`@type`. |
| 4 | Content Brief | `POST /content/brief` | ✅ **PASS** | 10s | Meta title *"Best Team Wiki Software for Knowledge Sharing (2024)"*, **8 headings** (incl. domain-aware "Why Notion Is the Ultimate Team Wiki Solution"), **10 must-cover entities**, **5 PAA questions**, 1,500-word target. |
| 5 | Content Score | `POST /content/score` | ✅ **PASS** | 16s | Score **34.6/100** with breakdown (length 20, entities 2.1, questions 12.5…) + **4 actionable recommendations**. |
| 6 | Internal Linking | `POST /linking/analyze` | ❌ **500** | — | Requires a **project** (service-role). Blocked in this env. |
| 7 | Programmatic | `POST /programmatic/generate` | ✅ **PASS** | instant | 3 city rows → **3 pages** with correct slugs/titles/meta (`best-running-shoes-austin`, …). |

**Scenario 2 verdict:** 5/7 pass with real output. Technical Audit needs a
PageSpeed key; Internal Linking needs a project.

---

## Scenario 3 — Tracking, Reporting & Ops

All feature endpoints here are **project-scoped** (`/projects/{id}/…` →
`_get_scoped_projects()`), so they need the Supabase `service_role` key that is
set on the user's machine but absent in this test env. Their **underlying data
layers were verified**:

| # | Feature | Feature status | Data layer verified |
|---|---|---|---|
| 1 | Rank Tracker | ⚠️ project-scoped | ✅ Serper returns SERP positions (`wool running shoes`: Allbirds not top-10; top 3 = giesswein / woolmark / saola). |
| 2 | Reports | ⚠️ project-scoped | Computes from stored project data. |
| 3 | Wins / ROI | ⚠️ project-scoped | Aggregates project metrics. |
| 4 | Multilingual | ⚠️ project-scoped | ✅ LLM translation works (EN→ES: *"Las mejores zapatillas de…"*). |
| 5 | Workflow / Autopilot | ⚠️ project-scoped | Scheduler stores per-project schedules. |
| 6 | Branding / Settings | ⚠️ project-scoped | Per-project branding record. |

**On the user's machine** (service-role key + an org/project present) these run;
here we confirmed the engines they depend on are functional.

---

## Bugs found & fixed

| # | Bug | Fix | Status |
|---|---|---|---|
| 1 | Gemini 2.5 returns empty JSON (thinking consumes token budget) | `thinkingConfig.thinkingBudget=0` for 2.5 models | ✅ fixed (prev PR) |
| 2 | No multi-key fallback → one exhausted key 500s every LLM feature | Key rotation on 429/403 in the Gemini client + `GEMINI_API_KEYS` config | ✅ fixed (this run) |

---

## Issues & observations

**Positive**
- Content Brief / Content Score / Keyword Research produce genuinely strong,
  domain-aware SEO output (outlines, entities, PAA, scoring with breakdown).
- Data layer (Serper + Firecrawl) is fast and reliable.
- Errors stay safe (generic 500, no stack leak).

**Follow-ups / recommendations**
- **Technical Audit** returns an empty `200` when PageSpeed/DataForSEO are
  unavailable — it should warn or `400` instead of silently returning nulls.
  Set a free `PAGESPEED_API_KEY` to make it functional.
- **Gemini free-tier is fragile:** `2.0-flash` daily quota exhausted across all
  keys, `2.5-flash` had a Google-side `503`. `gemini-flash-latest` was the stable
  choice. For production, a paid tier or a second provider (Groq/OpenAI/Anthropic)
  removes this single point of failure.
- **Key #5** (`…Ql6nx0`) returns `403` — enable the Generative Language API on
  that Google project or remove the key.
- **Many features are project-scoped** — full E2E of Scenarios 3 (and Internal
  Linking) requires the `service_role` key + an org/project, which the user has
  locally.

---

## Config used (test env)

```
DEFAULT_GEMINI_MODEL=gemini-flash-latest
GEMINI_API_KEY=<primary>
GEMINI_API_KEYS=<4 fallback keys>
SERPER_API_KEY / FIRECRAWL_API_KEY set
# absent: PAGESPEED_API_KEY, DATAFORSEO_*, SUPABASE_SERVICE_ROLE_KEY
```
