import { useAppStore } from "./store";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(humanizeApiError(status, message));
  }
}

/**
 * Backend errors arrive as FastAPI JSON — either {"detail": "..."} or, for
 * validation failures, {"detail": [{loc, msg, ...}]}. Toasts show err.message
 * directly, so translate those shapes into plain sentences here rather than
 * at every call site.
 */
function humanizeApiError(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body);
    const detail = parsed?.detail ?? parsed;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const msgs = detail.slice(0, 3).map((d: any) => {
        const field = Array.isArray(d?.loc)
          ? d.loc.filter((p: any) => p !== "body" && typeof p === "string").join(".")
          : "";
        return field ? `${field}: ${d?.msg ?? "invalid value"}` : d?.msg ?? "invalid value";
      });
      return msgs.join(" · ") || `Request failed (${status})`;
    }
  } catch {
    /* not JSON — fall through */
  }
  return body || `Request failed (${status})`;
}

/**
 * fetch() wrapper that authenticates as the logged-in user (Supabase JWT as
 * a Bearer token) and scopes the request to the selected project. The backend
 * confines JWT callers to their own org, so this is the real tenant boundary.
 * Falls back to the API key only if there is no user session (service/CLI use).
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { apiKey, currentProject } = useAppStore.getState();
  const headers: Record<string, string> = {
    ...(currentProject?.id ? { "X-Project-ID": String(currentProject.id) } : {}),
    ...((init.headers as Record<string, string>) || {}),
  };

  let token: string | null = null;
  try {
    const { createClient } = await import("./supabase");
    const { data } = await createClient().auth.getSession();
    token = data.session?.access_token ?? null;
  } catch {
    /* no session available */
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else if (apiKey) {
    headers["X-API-KEY"] = apiKey;
  }

  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  return fetch(url, { ...init, headers });
}

// ── Wins / ROI counter ──
export interface WinsSummary {
  project_id: string;
  period_days: number;
  stats: Record<string, number>;
  total_actions: number;
  value_inr: number;
  value_usd: number;
}

export async function getWinsSummary(days = 30): Promise<WinsSummary> {
  const res = await apiFetch(`/wins/summary?days=${days}`);
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  apiKey?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Prefer the logged-in user's Supabase JWT (org-scoped on the backend);
  // fall back to an explicit API key for service/CLI callers.
  let token: string | null = null;
  try {
    const { createClient } = await import("./supabase");
    const { data } = await createClient().auth.getSession();
    token = data.session?.access_token ?? null;
  } catch {
    /* no session */
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;
  else if (apiKey) headers["X-API-KEY"] = apiKey;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.json();
}

// ── Research ──
export async function runResearch(payload: {
  client_url: string;
  primary_keyword: string;
  locale?: string;
  target_region?: string;
  project_id?: string;
}, apiKey: string) {
  return request("/research/run", { method: "POST", body: JSON.stringify(payload) }, apiKey);
}

export async function createResearchJob(payload: {
  research_request: {
    client_url: string;
    primary_keyword: string;
    locale?: string;
    target_region?: string;
    project_id?: string;
  };
}, apiKey: string) {
  return request<{ job_id: string; status: string }>(
    "/jobs/research",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey
  );
}

export interface BudgetKeyword {
  keyword: string;
  cpc_inr: number;
  monthly_searches: number;
  competition: string;
  intent: string;
  relevance: number;
  priority: number;
  allocated_budget_inr: number;
  estimated_clicks: number;
}
export interface BudgetKeywordsResult {
  seed_keyword: string;
  mode: string;
  budget_inr: number;
  region: string;
  total_estimated_clicks: number;
  keywords_selected: number;
  recommended_mix: BudgetKeyword[];
  all_candidates: Array<Omit<BudgetKeyword, "allocated_budget_inr" | "estimated_clicks">>;
  notes: string;
}
export async function optimisedKeywords(payload: {
  budget_inr: number;
  seed_keyword: string;
  url?: string;
  mode?: string;
  region?: string;
  locale?: string;
}, apiKey: string) {
  return request<BudgetKeywordsResult>(
    "/keywords/optimised",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey
  );
}

export interface CroIssue {
  category: string;
  severity: "high" | "medium" | "low";
  finding: string;
  fix: string;
}
export interface CroAuditResult {
  url: string;
  goal: string;
  score: number | null;
  summary: string;
  issues: CroIssue[];
  quick_wins: string[];
  ctas_detected: string[];
}
export async function croAudit(payload: { url: string; goal?: string }, apiKey: string) {
  return request<CroAuditResult>(
    "/cro/audit",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey
  );
}

export async function createCroJob(payload: { url: string; goal?: string }, apiKey: string) {
  return request<{ job_id: string; status: string }>(
    "/jobs/cro",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey
  );
}

export async function getJob(jobId: string, apiKey: string) {
  return request<{
    job_id: string;
    status: string;
    created_at: string;
    updated_at: string;
    result: any;
    error: string | null;
    logs: Array<{ seq: number; at: string; level: string; message: string }>;
  }>(`/jobs/${jobId}`, {}, apiKey);
}

export async function listJobs(apiKey: string) {
  return request<Array<{ job_id: string; status: string; created_at: string; updated_at: string; result?: any }>>(
    "/jobs",
    {},
    apiKey
  );
}

// ── Keyword Research ──
export async function keywordResearch(params: {
  seed_keyword: string;
  domain: string;
  locale?: string;
  region?: string;
  industry?: string;
  city?: string;
}, apiKey: string) {
  const qs = new URLSearchParams({
    seed_keyword: params.seed_keyword,
    domain: params.domain,
    locale: params.locale || "en-US",
    region: params.region || "IN",
    industry: params.industry || "",
    city: params.city || "",
  });
  return request(`/keywords/research?${qs}`, { method: "POST" }, apiKey);
}

// ── Technical Audit ──
export async function technicalAudit(url: string, apiKey: string) {
  const qs = new URLSearchParams({ url });
  return request(`/audit/technical?${qs}`, { method: "POST" }, apiKey);
}

// ── Full site crawl (DataForSEO on-page) ──
export interface SiteCrawlResult {
  domain: string;
  task_id: string;
  status: "pending" | "crawling" | "finished" | "failed";
  error: string | null;
  pages_crawled: number;
  pages_in_queue: number;
  max_crawl_pages: number | null;
  onpage_score: number | null;
  issues_by_check: Record<string, number>;
  actions: Array<{
    category: string;
    action: string;
    impact: "critical" | "high" | "medium" | "low";
    details: string;
    auto_fixable: boolean;
  }>;
  sample_pages: Array<{
    url: string;
    status_code: number | null;
    onpage_score: number | null;
    title: string | null;
    description: string | null;
    word_count: number | null;
    h1: string[];
    internal_links: number | null;
    external_links: number | null;
    issues: string[];
  }>;
  duplicate_titles: Array<{ value: string; pages: string[]; total_count: number | null }>;
  duplicate_descriptions: Array<{ value: string; pages: string[]; total_count: number | null }>;
  broken_links: Array<{
    link_from: string | null;
    link_to: string | null;
    type: string | null;
    anchor: string | null;
  }>;
}

export async function startSiteCrawl(
  domain: string,
  maxPages: number,
  apiKey: string,
): Promise<SiteCrawlResult> {
  const qs = new URLSearchParams({ domain, max_pages: String(maxPages) });
  return request<SiteCrawlResult>(`/audit/crawl?${qs}`, { method: "POST" }, apiKey);
}

export async function getSiteCrawl(
  taskId: string,
  domain: string,
  apiKey: string,
): Promise<SiteCrawlResult> {
  const qs = new URLSearchParams({ domain });
  return request<SiteCrawlResult>(`/audit/crawl/${taskId}?${qs}`, {}, apiKey);
}

// ── ASO ──
export async function runAso(payload: any, apiKey: string) {
  return request("/aso/run", { method: "POST", body: JSON.stringify(payload) }, apiKey);
}

// ── AI Visibility (GEO) ──
export type LLMEngine = "chat_gpt" | "perplexity" | "gemini";

export interface KeywordVisibility {
  keyword: string;
  visibility_score: number;
  ai_overview_present: boolean;
  ai_overview_cited: boolean;
  ai_overview_position: number | null;
  ai_overview_snippet: string;
  ai_overview_citations: Array<{ position: number; domain: string; url: string; title: string }>;
  ai_mode_present: boolean;
  ai_mode_cited: boolean;
  ai_mode_snippet: string;
  llm_results: Record<
    string,
    {
      mentioned: boolean;
      citation_position: number | null;
      reference_count: number;
      snippet: string;
      error?: string | null;
    }
  >;
}

export interface AIVisibilityReport {
  domain: string;
  total_keywords: number;
  engines: string[];
  overall_score: number;
  ai_overview_coverage: number;
  ai_overview_citation_rate: number;
  llm_mention_rate: Record<string, number>;
  keywords: KeywordVisibility[];
}

export async function geoCheck(
  payload: {
    keywords: string[];
    domain: string;
    engines?: LLMEngine[];
    location_code?: number;
    language_code?: string;
    include_ai_mode?: boolean;
    prompt_template?: string;
  },
  apiKey: string,
): Promise<AIVisibilityReport> {
  return request<AIVisibilityReport>(
    "/geo/check",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function projectAiVisibility(
  projectId: string,
  opts: { engines?: string; includeAiMode?: boolean; maxKeywords?: number },
  apiKey: string,
): Promise<AIVisibilityReport> {
  const qs = new URLSearchParams();
  if (opts.engines) qs.set("engines", opts.engines);
  if (opts.includeAiMode) qs.set("include_ai_mode", "true");
  if (opts.maxKeywords) qs.set("max_keywords", String(opts.maxKeywords));
  return request<AIVisibilityReport>(
    `/projects/${projectId}/ai-visibility?${qs}`,
    { method: "POST" },
    apiKey,
  );
}

// ── Schema markup ──
export interface SchemaDetectionResult {
  url: string;
  blocks_found: number;
  detected_types: string[];
  detected: Array<{ type: string; name: string | null; raw: Record<string, any> }>;
  missing_recommended: string[];
  generated: Array<Record<string, any>>;
  parse_errors: string[];
}

export async function detectSchema(
  payload: {
    url: string;
    html?: string;
    business_type?: string;
    business_name?: string;
  },
  apiKey: string,
): Promise<SchemaDetectionResult> {
  return request<SchemaDetectionResult>(
    "/schema/detect",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function generateSchema(
  payload: {
    schema_types: string[];
    url?: string;
    business_name?: string;
    city?: string;
  },
  apiKey: string,
): Promise<{ generated: Array<{ type: string; jsonld: Record<string, any> }>; unsupported: string[] }> {
  return request(
    "/schema/generate",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

// ── SSE stream for job logs ──
export function streamJobLogs(
  jobId: string,
  apiKey: string,
  onLog: (log: any) => void,
  onDone: (data: any) => void,
  onError: (err: any) => void
) {
  const evtSource = new EventSource(`${API_BASE}/jobs/${jobId}/stream?x_api_key=${apiKey}`);
  evtSource.addEventListener("log", (e) => onLog(JSON.parse(e.data)));
  evtSource.addEventListener("done", (e) => { onDone(JSON.parse(e.data)); evtSource.close(); });
  evtSource.addEventListener("error", (e) => { onError(e); evtSource.close(); });
  return () => evtSource.close();
}

// ── Health ──
export async function healthCheck() {
  return request<{ status: string; service: string; ai: string }>("/health");
}

// ── Projects ──
export async function listProjects(apiKey: string) {
  return request<Array<{
    id: string; name: string; client_url: string; domain: string | null;
    target_niche: string | null; status: string; goal_keywords: string[];
    created_at: string; updated_at: string;
  }>>("/projects", {}, apiKey);
}

export async function createProject(payload: {
  name: string;
  client_url: string;
  target_niche?: string | null;
  goal_keywords?: string[];
}, apiKey: string) {
  return request<{ id: string; name: string }>(
    "/projects",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function deleteProject(projectId: string, apiKey: string) {
  return request<{ deleted: boolean }>(`/projects/${projectId}`, { method: "DELETE" }, apiKey);
}

export async function getProject(projectId: string, apiKey: string) {
  return request<{
    id: string; name: string; client_url: string; domain: string | null;
    target_niche: string | null; status: string; goal_keywords: string[];
    created_at: string; updated_at: string;
  }>(`/projects/${projectId}`, {}, apiKey);
}

export async function listProjectKeywords(projectId: string, apiKey: string) {
  return request<Array<{
    id: string; keyword: string; locale: string; target_region: string;
    search_volume: number | null; difficulty: number | null; intent: string | null;
    is_primary: boolean; tags: string[];
    latest_position: number | null; previous_position: number | null;
  }>>(`/projects/${projectId}/keywords`, {}, apiKey);
}

export async function addKeyword(projectId: string, payload: {
  keyword: string; target_region?: string; locale?: string; is_primary?: boolean;
}, apiKey: string) {
  return request(`/projects/${projectId}/keywords`, {
    method: "POST", body: JSON.stringify(payload),
  }, apiKey);
}

export async function deleteKeyword(keywordId: string, apiKey: string) {
  return request(`/keywords/${keywordId}`, { method: "DELETE" }, apiKey);
}

export async function getKeywordHistory(keywordId: string, apiKey: string, limit = 30) {
  return request<Array<{
    position: number | null; url: string | null;
    serp_features: string[]; checked_at: string;
  }>>(`/keywords/${keywordId}/rank-history?limit=${limit}`, {}, apiKey);
}

export async function triggerRankCheck(projectId: string, apiKey: string) {
  return request(`/projects/${projectId}/rank-check`, { method: "POST" }, apiKey);
}

// ── Reports ──
export async function listReports(projectId: string, apiKey: string) {
  return request<Array<{
    id: string; title: string; report_type: string;
    summary: string | null; created_at: string;
  }>>(`/projects/${projectId}/reports`, {}, apiKey);
}

export async function generateReport(projectId: string, reportType = "seo_audit", apiKey: string) {
  return request(`/projects/${projectId}/reports/generate?report_type=${reportType}`, {
    method: "POST",
  }, apiKey);
}

export async function getReportHtml(projectId: string, reportId: string, apiKey: string): Promise<string> {
  const res = await apiFetch(`/projects/${projectId}/reports/${reportId}/html`);
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.text();
}

// ── Content Studio ──
export async function listContent(projectId: string, apiKey: string) {
  return request<Array<{
    id: string; title: string; slug: string | null; body_markdown: string;
    target_keyword: string | null; queue_status: string;
    publish_target: string | null; created_at: string; updated_at: string;
  }>>(`/projects/${projectId}/content`, {}, apiKey);
}

export async function createContentDraft(projectId: string, payload: {
  title: string; body_markdown: string; target_keyword: string;
  meta_description?: string; publish_target?: string;
}, apiKey: string) {
  return request(`/projects/${projectId}/content`, {
    method: "POST", body: JSON.stringify(payload),
  }, apiKey);
}

export async function updateContent(contentId: string, payload: {
  body_markdown?: string; queue_status?: string; title?: string; target_keyword?: string;
}, apiKey: string) {
  return request(`/content/${contentId}`, {
    method: "PATCH", body: JSON.stringify(payload),
  }, apiKey);
}

export async function aiRewriteContent(contentId: string, instruction: string, apiKey: string) {
  const qs = new URLSearchParams({ instruction });
  return request<{ rewritten: boolean; word_count: number }>(
    `/content/${contentId}/ai-rewrite?${qs}`, { method: "POST" }, apiKey,
  );
}

// ── Competitors ──
export async function listCompetitors(projectId: string, apiKey: string) {
  return request<Array<{
    id: string; source_url: string; scraped_content: string | null;
    entity_maps: Record<string, any>; backlink_profiles: Record<string, any>;
    captured_at: string;
  }>>(`/projects/${projectId}/competitors`, {}, apiKey);
}

export async function triggerCompetitorScan(projectId: string, apiKey: string) {
  return request(`/projects/${projectId}/competitors/check`, { method: "POST" }, apiKey);
}

// ── Job PDF report ──
export function getJobReportUrl(jobId: string): string {
  return `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/jobs/${jobId}/report`;
}

// ── Content generation with AI ──
export async function generateContentWithAI(projectId: string, payload: {
  primary_keyword: string;
  city?: string;
  business_type?: string;
  content_type?: string;
}, apiKey: string) {
  return request<{ job_id: string; status: string }>(
    "/jobs/content",
    { method: "POST", body: JSON.stringify({ project_id: projectId, ...payload }) },
    apiKey,
  );
}

// ── Content brief + scoring ──
export interface ContentBriefCompetitor {
  url: string;
  title: string;
  word_count: number;
  headings: string[];
  position: number | null;
}

export interface ContentBrief {
  keyword: string;
  target_word_count: number;
  serp_median_words: number;
  competitors: ContentBriefCompetitor[];
  recommended_headings: string[];
  must_cover_entities: string[];
  questions_to_answer: string[];
  meta_title_suggestion: string;
  meta_description_suggestion: string;
  internal_links: { anchor: string; path: string }[];
  ai_overview_present: boolean;
  ai_overview_snippet: string;
  ai_generated: boolean;
}

export interface ContentScore {
  keyword: string;
  total: number;
  word_count: number;
  serp_median_words: number;
  breakdown: {
    length: number;
    headings: number;
    entities: number;
    questions: number;
    keyword_usage: number;
  };
  missing_headings: string[];
  missing_entities: string[];
  missing_questions: string[];
  recommendations: string[];
}

export async function generateContentBrief(
  payload: {
    keyword: string;
    domain?: string;
    location_code?: number;
    language_code?: string;
    scrape_top_n?: number;
  },
  apiKey: string,
) {
  return request<ContentBrief>(
    "/content/brief",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function scoreContent(
  payload: {
    keyword: string;
    url?: string;
    markdown?: string;
    brief?: ContentBrief;
  },
  apiKey: string,
) {
  return request<ContentScore>(
    "/content/score",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

// ── Revenue attribution (GA4 + GSC merged) ──
export interface AttributionPage {
  page_path: string;
  sessions: number;
  organic_sessions: number;
  revenue: number;
  organic_revenue: number;
  conversions: number;
  gsc_clicks: number;
  gsc_impressions: number;
  avg_position: number;
  top_queries: { query: string; clicks: number; impressions: number; position: number }[];
}

export interface AttributionQuery {
  query: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  landing_pages: string[];
  attributed_revenue: number;
}

export interface AttributionReport {
  date_range_days: number;
  ga4_property_id: string;
  gsc_site_url: string;
  ga4: {
    total_sessions: number;
    organic_sessions: number;
    organic_share_pct: number;
    total_revenue: number;
    organic_revenue: number;
    organic_revenue_share_pct: number;
    total_conversions: number;
    organic_conversions: number;
  };
  gsc: {
    total_clicks: number;
    total_impressions: number;
    avg_position: number;
  };
  top_pages: AttributionPage[];
  top_queries: AttributionQuery[];
  warnings: string[];
}

export async function attributionReport(
  payload: {
    ga4_access_token?: string;
    ga4_property_id: string;
    gsc_access_token?: string;
    gsc_site_url: string;
    date_range_days?: number;
    top_n?: number;
    project_id?: string;
  },
  apiKey: string,
) {
  return request<AttributionReport>(
    "/analytics/attribution",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

// ── Link building ────────────────────────────────────────────────

export interface BacklinkAnchor {
  anchor: string;
  backlinks: number;
  referring_domains: number;
  dofollow: boolean;
}

export interface BacklinkReferrer {
  domain: string;
  rank: number;
  backlinks: number;
  dofollow: boolean;
  first_seen?: string | null;
}

export interface BacklinkProfile {
  domain: string;
  total_backlinks: number;
  referring_domains: number;
  domain_rank: number;
  dofollow_ratio: number;
  top_anchors: BacklinkAnchor[];
  top_referring: BacklinkReferrer[];
  warnings: string[];
}

export type LinkProspectStatus =
  | "new"
  | "researching"
  | "contacted"
  | "replied"
  | "agreed"
  | "placed"
  | "declined";

export interface LinkProspect {
  id: string;
  project_id: string;
  domain: string;
  url: string | null;
  contact_name: string | null;
  contact_email: string | null;
  domain_rating: number | null;
  referring_domains: number | null;
  status: LinkProspectStatus;
  template: string | null;
  subject: string | null;
  notes: string | null;
  opportunity_score: number | null;
  already_linking: boolean;
  outreach_sent_at: string | null;
  response_at: string | null;
  placed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutreachEmailDraft {
  subject: string;
  body: string;
  template: string;
  model_used?: string;
  cost_usd?: number;
  fallback?: boolean;
}

export async function fetchBacklinkProfile(
  payload: { domain: string; anchors_limit?: number; referring_limit?: number },
  apiKey: string,
) {
  return request<BacklinkProfile>(
    "/links/backlinks",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function draftOutreachEmail(
  payload: {
    prospect: Record<string, unknown>;
    campaign?: Record<string, unknown>;
    template?: "intro" | "broken_link" | "guest_post" | "resource_page";
  },
  apiKey: string,
) {
  return request<OutreachEmailDraft>(
    "/links/outreach/draft",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function listLinkProspects(
  projectId: string,
  apiKey: string,
  status?: LinkProspectStatus,
) {
  const qs = status ? `?status=${status}` : "";
  return request<LinkProspect[]>(
    `/projects/${projectId}/link-prospects${qs}`,
    { method: "GET" },
    apiKey,
  );
}

export async function createLinkProspect(
  projectId: string,
  payload: Partial<LinkProspect> & { domain: string },
  apiKey: string,
) {
  return request<LinkProspect>(
    `/projects/${projectId}/link-prospects`,
    {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, ...payload }),
    },
    apiKey,
  );
}

export async function updateLinkProspect(
  prospectId: string,
  payload: Partial<LinkProspect>,
  apiKey: string,
) {
  return request<LinkProspect>(
    `/link-prospects/${prospectId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function deleteLinkProspect(prospectId: string, apiKey: string) {
  return request<{ deleted: boolean }>(
    `/link-prospects/${prospectId}`,
    { method: "DELETE" },
    apiKey,
  );
}

export async function draftProspectEmail(
  prospectId: string,
  payload: {
    prospect?: Record<string, unknown>;
    campaign?: Record<string, unknown>;
    template?: "intro" | "broken_link" | "guest_post" | "resource_page";
  },
  apiKey: string,
) {
  return request<OutreachEmailDraft>(
    `/link-prospects/${prospectId}/draft-email`,
    { method: "POST", body: JSON.stringify({ prospect: {}, ...payload }) },
    apiKey,
  );
}

// ── White-label branding ─────────────────────────────────────────

export interface BrandingConfig {
  agency_name: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  text_color: string;
  background_color: string;
  cover_title: string;
  cover_subtitle: string;
  footer_text: string;
  website: string;
  email: string;
  enabled: boolean;
}

export interface BrandingResponse {
  branding: BrandingConfig;
  validation_warnings: string[];
}

export async function getProjectBranding(projectId: string, apiKey: string) {
  return request<BrandingResponse>(
    `/projects/${projectId}/branding`,
    { method: "GET" },
    apiKey,
  );
}

export async function updateProjectBranding(
  projectId: string,
  updates: Partial<BrandingConfig>,
  apiKey: string,
) {
  return request<{ branding: BrandingConfig }>(
    `/projects/${projectId}/branding`,
    { method: "PATCH", body: JSON.stringify(updates) },
    apiKey,
  );
}

export function brandingPreviewUrl(projectId: string) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return `${base}/projects/${projectId}/branding/preview`;
}

// ── Programmatic SEO ─────────────────────────────────────────────

export interface ProgrammaticTemplate {
  name?: string;
  slug_template: string;
  title_template: string;
  meta_description_template: string;
  h1_template?: string;
  body_template: string;
}

export interface ProgrammaticPage {
  slug: string;
  title: string;
  meta_description: string;
  h1: string;
  body_markdown: string;
  variables: Record<string, unknown>;
  warnings: string[];
}

export interface ProgrammaticResult {
  template_name: string;
  total_rows: number;
  generated: number;
  skipped: number;
  variables_used: string[];
  warnings: string[];
  pages: ProgrammaticPage[];
}

export async function generateProgrammaticPages(
  payload: {
    template: ProgrammaticTemplate;
    rows?: Record<string, unknown>[];
    csv?: string;
    dedupe_on?: string;
    max_pages?: number;
  },
  apiKey: string,
) {
  return request<ProgrammaticResult>(
    "/programmatic/generate",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

// ── Social Media Studio ──────────────────────────────────────────

export type SocialPlatform = "instagram" | "facebook" | "tiktok" | "youtube" | "linkedin";

export type SocialPostStatus =
  | "draft"
  | "pending_approval"
  | "revision_requested"
  | "approved"
  | "scheduled"
  | "published";

export interface SocialGenerated {
  hook: string;
  caption: string;
  hashtags: string[];
  cta: string;
  best_time_hint: string;
  error?: string;
}

export interface SocialGenerateResult {
  topic: string;
  tone: string;
  content_goal: string;
  platforms: Record<string, SocialGenerated>;
  model_used: string | null;
}

export interface SocialPost {
  id: string;
  project_id: string;
  platform: SocialPlatform;
  topic: string;
  caption: string;
  hashtags: string[];
  content_goal: string;
  media_notes: string;
  scheduled_date: string | null;
  status: SocialPostStatus;
  revision_count: number;
  revision_notes: Array<{ round: number; note: string; at: string }>;
  created_at: string;
  updated_at: string;
}

export async function generateSocialPosts(
  payload: {
    topic: string;
    platforms: SocialPlatform[];
    tone?: string;
    business_context?: string;
    content_goal?: string;
  },
  apiKey: string,
) {
  return request<SocialGenerateResult>(
    "/social/generate",
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function listSocialPosts(
  projectId: string,
  apiKey: string,
  filters?: { status?: SocialPostStatus; platform?: SocialPlatform },
) {
  const qs = new URLSearchParams();
  if (filters?.status) qs.set("status", filters.status);
  if (filters?.platform) qs.set("platform", filters.platform);
  const suffix = qs.toString() ? `?${qs}` : "";
  return request<SocialPost[]>(`/projects/${projectId}/social-posts${suffix}`, {}, apiKey);
}

export async function createSocialPost(
  projectId: string,
  payload: {
    platform: SocialPlatform;
    topic?: string;
    caption: string;
    hashtags?: string[];
    content_goal?: string;
    media_notes?: string;
    scheduled_date?: string | null;
  },
  apiKey: string,
) {
  return request<SocialPost>(
    `/projects/${projectId}/social-posts`,
    { method: "POST", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function updateSocialPost(
  postId: string,
  payload: Partial<Pick<SocialPost, "caption" | "hashtags" | "topic" | "content_goal" | "media_notes" | "scheduled_date" | "status" | "platform">>,
  apiKey: string,
) {
  return request<SocialPost>(
    `/social-posts/${postId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function approveSocialPost(postId: string, apiKey: string) {
  return request<SocialPost>(`/social-posts/${postId}/approve`, { method: "POST" }, apiKey);
}

export async function requestSocialRevision(postId: string, note: string, apiKey: string) {
  return request<SocialPost>(
    `/social-posts/${postId}/request-revision`,
    { method: "POST", body: JSON.stringify({ note }) },
    apiKey,
  );
}

export async function deleteSocialPost(postId: string, apiKey: string) {
  return request<{ deleted: boolean }>(`/social-posts/${postId}`, { method: "DELETE" }, apiKey);
}

export interface SocialMetrics {
  platform: SocialPlatform;
  month: string; // 'YYYY-MM'
  reach: number;
  impressions: number;
  engagement: number;
  followers: number;
  website_clicks: number;
  whatsapp_clicks: number;
  enquiries: number;
  posts_published: number;
  notes?: string;
}

export async function upsertSocialMetrics(
  projectId: string,
  payload: SocialMetrics,
  apiKey: string,
) {
  return request<SocialMetrics>(
    `/projects/${projectId}/social-metrics`,
    { method: "PUT", body: JSON.stringify(payload) },
    apiKey,
  );
}

export async function listSocialMetrics(projectId: string, month: string, apiKey: string) {
  return request<SocialMetrics[]>(
    `/projects/${projectId}/social-metrics?month=${month}`,
    {},
    apiKey,
  );
}

export async function getSocialReportHtml(
  projectId: string,
  month: string,
  apiKey: string,
): Promise<string> {
  const res = await apiFetch(`/projects/${projectId}/social-report/${month}`);
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.text();
}

// ── Monthly workflow (Week 1-4 cadence) ──────────────────────────

export interface WorkflowSchedule {
  project_id: string;
  week: number;
  week_label: string;
  tasks: string[];
  as_of: string;
}

export interface WorkflowTaskResult {
  name: string;
  status: "completed" | "skipped" | "failed";
  detail: string;
  data: Record<string, unknown>;
}

export interface WorkflowRun {
  project_id: string;
  week: number;
  week_label: string;
  started_at: string;
  finished_at: string;
  completed: number;
  skipped: number;
  failed: number;
  tasks: WorkflowTaskResult[];
}

export async function getWorkflowSchedule(projectId: string, apiKey: string) {
  return request<WorkflowSchedule>(
    `/workflow/schedule/${projectId}`,
    { method: "GET" },
    apiKey,
  );
}

// ── Content decay (GSC refresh loop) ──────────────────────────────

export interface DecayQueryStat {
  query: string;
  impressions: number;
  clicks: number;
  position: number;
}

export interface DecayItem {
  page: string;
  clicks_prev: number;
  clicks_now: number;
  clicks_lost: number;
  impressions_prev: number;
  impressions_now: number;
  position_prev: number;
  position_now: number;
  reasons: string[];
  severity: "warning" | "critical";
  top_queries: DecayQueryStat[];
}

export interface ContentDecayReport {
  project_id: string;
  site_url: string;
  window_days: number;
  current_window: [string, string];
  previous_window: [string, string];
  pages_analyzed: number;
  decayed_count: number;
  decayed: DecayItem[];
}

export async function getContentDecay(
  projectId: string,
  apiKey: string,
  siteUrl = "",
  days = 28,
) {
  const params = new URLSearchParams();
  if (siteUrl) params.set("site_url", siteUrl);
  params.set("days", String(days));
  return request<ContentDecayReport>(
    `/projects/${projectId}/content-decay?${params}`,
    {},
    apiKey,
  );
}

export async function createDecayRefresh(
  projectId: string,
  body: { page: string; queries: string[]; reasons: string[] },
  apiKey: string,
) {
  return request<{ page: string; title: string; sections: any[]; draft_id: string | null }>(
    `/projects/${projectId}/content-decay/refresh`,
    { method: "POST", body: JSON.stringify(body) },
    apiKey,
  );
}

export async function runWorkflow(
  projectId: string,
  apiKey: string,
  only?: string[],
) {
  return request<WorkflowRun>(
    `/workflow/run/${projectId}`,
    { method: "POST", body: JSON.stringify({ only, triggered_by: "manual" }) },
    apiKey,
  );
}

export async function listWorkflowRuns(
  projectId: string,
  apiKey: string,
  limit = 20,
) {
  return request<{ runs: Array<WorkflowRun & { id: string; created_at: string; triggered_by: string }> }>(
    `/workflow/runs/${projectId}?limit=${limit}`,
    { method: "GET" },
    apiKey,
  );
}
