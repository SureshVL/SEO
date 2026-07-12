"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft, Check, Download, Loader2, Play, Plus, Trash2, X,
  Eye, EyeOff, Copy, AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Article {
  slug: string;
  title: string;
  meta_description: string;
  h1: string;
  body: string;
  word_count: number;
  reading_time_minutes: number;
  ai_enhanced: boolean;
  errors: string[];
}

interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  total_articles: number;
  completed_articles: number;
  failed_articles: number;
  export_url?: string;
  error_message?: string;
}

const TEMPLATE_PLACEHOLDER = {
  name: "Blog Article Template",
  title_template: "{{topic}} - A Complete Guide",
  slug_template: "guide-{{topic_slug}}",
  meta_template: "Learn about {{topic}}. Complete guide with tips and best practices.",
  h1_template: "{{topic}}: Everything You Need to Know",
  body_template: `# {{topic}}

## Introduction
{{ai:Write a compelling introduction about {{topic}} that hooks the reader}}

## Main Content
{{ai:Write 3 detailed sections about {{topic}} with examples}}

## Key Takeaways
{{ai:Summarize the most important points about {{topic}}}}`,
};

export default function BulkContentPage() {
  const { apiKey, businessProfile } = useAppStore();

  const [tab, setTab] = useState<"create" | "history">("create");
  const [templateJson, setTemplateJson] = useState(JSON.stringify(TEMPLATE_PLACEHOLDER, null, 2));
  const [csvInput, setCsvInput] = useState("topic,topic_slug\npython,python\nnode.js,nodejs");
  const [enhance, setEnhance] = useState(true);
  const [exportFormat, setExportFormat] = useState("json");
  const [scheduleDatetime, setScheduleDatetime] = useState("");

  const [loading, setLoading] = useState(false);
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [articles, setArticles] = useState<Article[]>([]);
  const [jobs, setJobs] = useState<JobStatus[]>([]);

  const [showPreview, setShowPreview] = useState(false);
  const [previewArticle, setPreviewArticle] = useState<Article | null>(null);

  const parseTemplate = (json: string) => {
    try {
      return JSON.parse(json);
    } catch {
      toast.error("Invalid JSON template");
      return null;
    }
  };

  const parseCsv = (csv: string): Array<Record<string, string>> => {
    const lines = csv.trim().split("\n");
    if (lines.length < 2) return [];

    const headers = lines[0].split(",").map((h) => h.trim());
    const rows: Array<Record<string, string>> = [];

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(",").map((v) => v.trim());
      const row: Record<string, string> = {};
      headers.forEach((header, idx) => {
        row[header] = values[idx] || "";
      });
      rows.push(row);
    }

    return rows;
  };

  const handleCreateJob = async () => {
    if (!apiKey) {
      toast.error("API key not configured");
      return;
    }

    const template = parseTemplate(templateJson);
    if (!template) return;

    const csvData = parseCsv(csvInput);
    if (csvData.length === 0) {
      toast.error("No CSV rows to process");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/bulk/jobs`, {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          template,
          csv_data: csvData,
          enhance_with_ai: enhance,
          export_format: exportFormat,
          schedule_publish: scheduleDatetime,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create job");
      }

      const job = await res.json();
      setCurrentJob(job);
      setJobProgress(0);
      toast.success(`Job created: ${job.job_id}`);

      // Start polling
      pollJobStatus(job.job_id);
    } catch (err: any) {
      toast.error(err.message || "Failed to create job");
    } finally {
      setLoading(false);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    const poll = async () => {

      try {
        const res = await fetch(`${API}/bulk/jobs/${jobId}`, {
          headers: { "X-API-KEY": apiKey },
        });

        if (!res.ok) return;

        const job = await res.json() as JobStatus;
        setCurrentJob(job);

        const progress = job.total_articles > 0
          ? Math.round(((job.completed_articles + job.failed_articles) / job.total_articles) * 100)
          : 0;
        setJobProgress(progress);

        // Fetch articles if completed
        if (job.status === "completed") {
          fetchArticles(jobId);
        }

        // Continue polling if still running
        if (job.status === "queued" || job.status === "running") {
          setTimeout(poll, 2000);
        }
      } catch (err) {
        console.error("Poll error:", err);
      }
    };

    poll();
  };

  const fetchArticles = async (jobId: string) => {

    try {
      const res = await fetch(`${API}/bulk/jobs/${jobId}/articles?limit=100`, {
        headers: { "X-API-KEY": apiKey },
      });

      if (!res.ok) return;

      const data = await res.json();
      setArticles(data.articles || []);
    } catch (err) {
      console.error("Failed to fetch articles:", err);
    }
  };

  const handleCancel = async () => {
    if (!apiKey || !currentJob) return;

    if (!confirm("Cancel this job?")) return;

    try {
      const res = await fetch(`${API}/bulk/jobs/${currentJob.job_id}`, {
        method: "DELETE",
        headers: { "X-API-KEY": apiKey },
      });

      if (!res.ok) throw new Error("Cancel failed");
      toast.success("Job cancelled");
      setCurrentJob(null);
      setArticles([]);
    } catch (err: any) {
      toast.error(err.message || "Cancel failed");
    }
  };

  const handleDownload = () => {
    if (!currentJob) return;

    const content = articles.map((a) => ({
      title: a.title,
      slug: a.slug,
      meta: a.meta_description,
      h1: a.h1,
      word_count: a.word_count,
      reading_time: a.reading_time_minutes,
      ai_enhanced: a.ai_enhanced,
    }));

    const json = JSON.stringify(content, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `articles-${currentJob.job_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const csvRowCount = csvInput.trim().split("\n").length - 1;

  return (
    <div className="min-h-screen bg-zinc-950">
      <PageHeader
        title="Bulk Content Generation"
        subtitle="Generate hundreds of SEO articles from templates and CSV data"
      />

      <div className="max-w-6xl mx-auto p-6">
        {!currentJob ? (
          // Create new job
          <div className="space-y-6">
            <div className="flex gap-2 border-b border-zinc-800">
              <button
                onClick={() => setTab("create")}
                className={cn(
                  "px-4 py-3 text-sm font-medium transition-colors",
                  tab === "create"
                    ? "border-b-2 border-violet-500 text-violet-400"
                    : "text-zinc-400 hover:text-zinc-300"
                )}
              >
                Create Job
              </button>
              <button
                onClick={() => setTab("history")}
                className={cn(
                  "px-4 py-3 text-sm font-medium transition-colors",
                  tab === "history"
                    ? "border-b-2 border-violet-500 text-violet-400"
                    : "text-zinc-400 hover:text-zinc-300"
                )}
              >
                Job History
              </button>
            </div>

            {tab === "create" && (
              <div className="grid grid-cols-2 gap-6">
                {/* Template Editor */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-zinc-300">
                    Article Template (JSON)
                  </label>
                  <textarea
                    value={templateJson}
                    onChange={(e) => setTemplateJson(e.target.value)}
                    className="input-field w-full h-80 font-mono text-xs resize-none"
                    placeholder="Template JSON..."
                  />
                  <p className="text-xs text-zinc-500">
                    Use {`{{variable}}`} for substitution and {`{{ai:prompt}}`} for AI enhancement
                  </p>
                </div>

                {/* CSV Data */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-zinc-300">
                    CSV Data ({csvRowCount} rows)
                  </label>
                  <textarea
                    value={csvInput}
                    onChange={(e) => setCsvInput(e.target.value)}
                    className="input-field w-full h-80 font-mono text-xs resize-none"
                    placeholder="CSV format..."
                  />
                  <p className="text-xs text-zinc-500">
                    First line: column headers. Data variables match template placeholders.
                  </p>
                </div>
              </div>
            )}

            {tab === "history" && (
              <div className="text-center py-12 text-zinc-400">
                <p>No job history yet. Create your first bulk content job.</p>
              </div>
            )}

            {tab === "create" && (
              <div className="grid grid-cols-3 gap-4">
                {/* AI Enhancement */}
                <div className="space-y-2">
                  <label className="block text-xs text-zinc-500 uppercase tracking-wider">
                    AI Enhancement
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enhance}
                      onChange={(e) => setEnhance(e.target.checked)}
                      className="w-4 h-4 rounded border-zinc-700"
                    />
                    <span className="text-sm text-zinc-300">
                      {enhance ? "Enabled" : "Disabled"}
                    </span>
                  </label>
                </div>

                {/* Export Format */}
                <div className="space-y-2">
                  <label className="block text-xs text-zinc-500 uppercase tracking-wider">
                    Export Format
                  </label>
                  <select
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value)}
                    className="input-field w-full text-sm"
                  >
                    <option value="json">JSON</option>
                    <option value="csv">CSV</option>
                    <option value="markdown">Markdown</option>
                  </select>
                </div>

                {/* Schedule Publish */}
                <div className="space-y-2">
                  <label className="block text-xs text-zinc-500 uppercase tracking-wider">
                    Schedule Publish (Optional)
                  </label>
                  <input
                    type="datetime-local"
                    value={scheduleDatetime}
                    onChange={(e) => setScheduleDatetime(e.target.value)}
                    className="input-field w-full text-sm"
                  />
                </div>
              </div>
            )}

            {tab === "create" && (
              <div className="flex gap-2 pt-4">
                <button
                  onClick={handleCreateJob}
                  disabled={loading}
                  className="btn-primary flex items-center justify-center gap-2 flex-1"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Start Generation ({csvRowCount} articles)
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        ) : (
          // Job in progress / completed
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
                  Job: {currentJob.job_id}
                  <span className={cn(
                    "text-xs px-2 py-1 rounded font-medium uppercase",
                    currentJob.status === "running" && "bg-cyan-500/20 text-cyan-300",
                    currentJob.status === "completed" && "bg-emerald-500/20 text-emerald-300",
                    currentJob.status === "failed" && "bg-red-500/20 text-red-300",
                    currentJob.status === "queued" && "bg-zinc-700 text-zinc-300",
                  )}>
                    {currentJob.status}
                  </span>
                </h2>
              </div>
              <button
                onClick={() => setCurrentJob(null)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-zinc-400">Progress</span>
                <span className="text-zinc-300 font-medium">
                  {currentJob.completed_articles + currentJob.failed_articles} / {currentJob.total_articles}
                </span>
              </div>
              <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-violet-500 to-cyan-500 transition-all"
                  style={{ width: `${jobProgress}%` }}
                />
              </div>
              <div className="text-xs text-zinc-500">{jobProgress}% complete</div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-500 mb-1">Total</div>
                <div className="text-2xl font-bold text-zinc-100">
                  {currentJob.total_articles}
                </div>
              </div>
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
                <div className="text-xs text-emerald-400 mb-1">Completed</div>
                <div className="text-2xl font-bold text-emerald-300">
                  {currentJob.completed_articles}
                </div>
              </div>
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <div className="text-xs text-red-400 mb-1">Failed</div>
                <div className="text-2xl font-bold text-red-300">
                  {currentJob.failed_articles}
                </div>
              </div>
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
                <div className="text-xs text-zinc-500 mb-1">Success Rate</div>
                <div className="text-2xl font-bold text-zinc-100">
                  {currentJob.total_articles > 0
                    ? Math.round((currentJob.completed_articles / currentJob.total_articles) * 100)
                    : 0}%
                </div>
              </div>
            </div>

            {currentJob.error_message && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-red-300">Error</div>
                  <div className="text-xs text-red-200">{currentJob.error_message}</div>
                </div>
              </div>
            )}

            {/* Articles Preview */}
            {currentJob.status === "completed" && articles.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-zinc-100">
                  Generated Articles ({articles.length})
                </h3>

                <div className="grid gap-3 max-h-96 overflow-y-auto">
                  {articles.slice(0, 10).map((article, idx) => (
                    <div
                      key={idx}
                      className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 cursor-pointer transition-colors"
                      onClick={() => {
                        setPreviewArticle(article);
                        setShowPreview(true);
                      }}
                    >
                      <div className="flex justify-between items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-zinc-100 truncate">{article.title}</h4>
                          <p className="text-xs text-zinc-500 line-clamp-2 mt-1">
                            {article.meta_description}
                          </p>
                          <div className="flex gap-3 mt-2 text-xs text-zinc-400">
                            <span>{article.word_count} words</span>
                            <span>{article.reading_time_minutes} min read</span>
                            {article.ai_enhanced && (
                              <span className="text-cyan-400">✓ AI Enhanced</span>
                            )}
                          </div>
                        </div>
                        <Eye className="w-4 h-4 text-zinc-600" />
                      </div>
                    </div>
                  ))}
                </div>

                {articles.length > 10 && (
                  <p className="text-xs text-zinc-500">
                    Showing first 10 of {articles.length} articles
                  </p>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-4">
              {(currentJob.status === "running" || currentJob.status === "queued") && (
                <button
                  onClick={handleCancel}
                  className="btn-secondary flex items-center justify-center gap-2 flex-1"
                >
                  <X className="w-4 h-4" />
                  Cancel Job
                </button>
              )}
              {currentJob.status === "completed" && articles.length > 0 && (
                <button
                  onClick={handleDownload}
                  className="btn-primary flex items-center justify-center gap-2 flex-1"
                >
                  <Download className="w-4 h-4" />
                  Download Articles
                </button>
              )}
              <button
                onClick={() => setCurrentJob(null)}
                className="btn-secondary flex-1"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Article Preview Modal */}
      {showPreview && previewArticle && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-zinc-900 border-b border-zinc-800 p-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-zinc-100">
                {previewArticle.title}
              </h2>
              <button
                onClick={() => setShowPreview(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <div className="text-xs text-zinc-500 mb-1">Meta Description</div>
                <p className="text-sm text-zinc-300">{previewArticle.meta_description}</p>
              </div>
              <div>
                <div className="text-xs text-zinc-500 mb-1">H1</div>
                <h1 className="text-2xl font-bold text-zinc-100">{previewArticle.h1}</h1>
              </div>
              <div className="prose prose-invert max-w-none">
                <div className="text-sm text-zinc-300 whitespace-pre-wrap">
                  {previewArticle.body.substring(0, 500)}...
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="bg-zinc-800/50 rounded p-2">
                  <div className="text-zinc-500">Word Count</div>
                  <div className="text-zinc-300 font-medium">{previewArticle.word_count}</div>
                </div>
                <div className="bg-zinc-800/50 rounded p-2">
                  <div className="text-zinc-500">Reading Time</div>
                  <div className="text-zinc-300 font-medium">
                    {previewArticle.reading_time_minutes} min
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
