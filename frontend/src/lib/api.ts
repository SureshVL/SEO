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
}, apiKey: string) {
  const qs = new URLSearchParams({
    seed_keyword: params.seed_keyword,
    domain: params.domain,
    locale: params.locale || "en-US",
    region: params.region || "IN",
    industry: params.industry || "",
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
