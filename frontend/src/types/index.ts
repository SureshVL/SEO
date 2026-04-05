// ── Auth & Users ──
export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  org_id: string;
  role: "owner" | "admin" | "member" | "viewer";
  onboarded: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: "starter" | "growth" | "agency" | "enterprise";
  plan_status: "active" | "past_due" | "cancelled" | "trialing";
  max_projects: number;
  max_keywords: number;
  max_reports_per_month: number;
  razorpay_subscription_id: string | null;
  trial_ends_at: string | null;
  created_at: string;
}

// ── Projects ──
export interface Project {
  id: string;
  name: string;
  client_url: string;
  domain: string | null;
  target_niche: string | null;
  status: "active" | "paused" | "archived";
  goal_keywords: string[];
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  client_url: string;
  domain?: string;
  target_niche?: string;
  goal_keywords?: string[];
}

// ── Keywords ──
export interface Keyword {
  id: string;
  keyword: string;
  locale: string;
  target_region: string;
  search_volume: number | null;
  difficulty: number | null;
  intent: "informational" | "transactional" | "navigational" | "commercial" | null;
  is_primary: boolean;
  tags: string[];
  latest_position: number | null;
  previous_position: number | null;
}

export interface RankHistoryPoint {
  position: number | null;
  url: string | null;
  serp_features: string[];
  checked_at: string;
}

// ── Research ──
export interface ResearchRequest {
  client_url: string;
  primary_keyword: string;
  locale?: string;
  target_region?: string;
  project_id?: string;
}

export interface CompetitorProfile {
  url: string;
  title: string;
  h1: string | null;
  h2: string[];
  top_entities: string[];
  top_questions: string[];
  word_count: number;
  keyword_density: number;
}

export interface GapAnalysis {
  missing_entities: string[];
  missing_questions: string[];
  heading_gaps: string[];
  density_gap: number;
}

export interface ResearchResult {
  seo_score: number;
  competitor_profiles: CompetitorProfile[];
  client_profile: CompetitorProfile;
  gap_analysis: GapAnalysis;
  recommendations: string[];
  raw_metrics: Record<string, unknown>;
}

export interface WorkflowResponse {
  attempts: number;
  final_score: number;
  passed_threshold: boolean;
  trace: { steps: string[] };
  result: ResearchResult;
}

// ── Jobs ──
export interface Job {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  result: WorkflowResponse | null;
  error: string | null;
  logs: JobLog[];
}

export interface JobLog {
  seq: number;
  at: string;
  level: string;
  message: string;
}

// ── Content ──
export interface ContentDraft {
  id: string;
  title: string;
  slug: string | null;
  body_markdown: string;
  target_keyword: string | null;
  queue_status: "draft" | "review" | "approved" | "published";
  publish_target: string | null;
  created_at: string;
  updated_at: string;
}

// ── Audit ──
export interface TechnicalAuditResult {
  url: string;
  scores: {
    performance: number | null;
    accessibility: number | null;
    seo: number | null;
    best_practices: number | null;
  };
  core_web_vitals: Record<string, number>;
  actions: AuditAction[];
  issues_count: number;
}

export interface AuditAction {
  category: string;
  action: string;
  impact: "critical" | "high" | "medium" | "low";
  details: string;
  auto_fixable: string;
  status: string;
}

// ── Keyword Research ──
export interface KeywordOpportunity {
  keyword: string;
  volume: "high" | "medium" | "low";
  difficulty: "easy" | "medium" | "hard";
  intent: string;
  content_type: string;
  priority: number;
  cluster: string;
}

export interface KeywordResearchResult {
  primary_keyword: string;
  opportunities: KeywordOpportunity[];
  clusters: Record<string, string[]>;
  content_plan: ContentPlanItem[];
  competitor_keywords: string[];
}

export interface ContentPlanItem {
  order: number;
  keyword: string;
  content_type: string;
  title: string;
  rationale: string;
}

// ── Reports ──
export interface Report {
  id: string;
  project_id: string;
  report_type: string;
  title: string;
  summary: string | null;
  data: Record<string, unknown>;
  created_at: string;
}

// ── Billing ──
export interface BillingPlan {
  id: string;
  name: string;
  price: string;
  priceNum: number;
  features: string[];
  popular?: boolean;
}

export interface SubscriptionResult {
  subscription_id: string;
  checkout_url: string;
  status: string;
}
