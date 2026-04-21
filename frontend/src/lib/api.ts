const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
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
  if (apiKey) headers["X-API-KEY"] = apiKey;

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
  return request<Array<{ job_id: string; status: string; created_at: string; updated_at: string }>>(
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
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/projects/${projectId}/reports/${reportId}/html`,
    { headers: { "X-API-KEY": apiKey } }
  );
  if (!res.ok) throw new Error(await res.text());
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
