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

// ── ASO ──
export async function runAso(payload: any, apiKey: string) {
  return request("/aso/run", { method: "POST", body: JSON.stringify(payload) }, apiKey);
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
