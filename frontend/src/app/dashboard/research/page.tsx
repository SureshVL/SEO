"use client";

import { useState, useEffect } from "react";
import { Bot, ExternalLink, Globe2, Languages, Loader2, MapPin, Search, Sparkles, TrendingUp } from "lucide-react";
import { cn, scoreColor, scoreBg } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { createResearchJob, getJob } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

export default function ResearchPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [url, setUrl] = useState("");
  const [keyword, setKeyword] = useState("");
  const [region, setRegion] = useState("IN");
  const [locale, setLocale] = useState("en-US");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

  // Auto-fill from business profile
  useEffect(() => {
    if (businessProfile) {
      if (!url && businessProfile.websiteUrl) setUrl(businessProfile.websiteUrl);
      if (!keyword && businessProfile.keywords.length > 0) {
        const kw = businessProfile.keywords[0];
        setKeyword(businessProfile.city ? `${kw} in ${businessProfile.city}` : kw);
      }
    }
  }, [businessProfile]);

  // Deep-link: /dashboard/research?job=<id> opens that job's report (from the
  // "View" link on the dashboard's Recent Jobs) instead of a blank form.
  useEffect(() => {
    const jobId = new URLSearchParams(window.location.search).get("job");
    if (!jobId) return;
    setLoading(true);
    setLogs(["Loading job report…"]);
    getJob(jobId, apiKey)
      .then((job) => {
        setLogs((job.logs ?? []).map((l: any) => l.message ?? String(l)));
        if (job.status === "completed" && job.result) {
          setResult(job.result);
        } else if (job.status === "failed") {
          toast.error(job.error || "This job failed.");
        } else {
          toast.message("This job is still running — check back shortly.");
        }
      })
      .catch(() => toast.error("Could not load that job."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const profileContext = businessProfile
    ? `${businessProfile.city ? businessProfile.city + " · " : ""}${businessProfile.businessTypeLabel}`
    : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url || !keyword) return;
    setLoading(true);
    setLogs(["Starting AI research job..."]);
    setResult(null);

    try {
      const { job_id } = await createResearchJob({
        research_request: {
          client_url: url,
          primary_keyword: keyword,
          target_region: region,
          locale,
          project_id: businessProfile?.projectId || "",
          ...(businessProfile && {
            city: businessProfile.cityCode,
            business_type: businessProfile.businessType,
          }),
        },
      }, apiKey);

      setLogs((l) => [...l, `Job created: ${job_id.slice(0, 8)}...`]);

      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const job = await getJob(job_id, apiKey);
          if (job.logs) setLogs(job.logs.map((l: any) => l.message));
          if (job.status === "completed") {
            clearInterval(poll);
            setResult(job.result);
            setLoading(false);
            toast.success("Research complete!");
          } else if (job.status === "failed") {
            clearInterval(poll);
            setLoading(false);
            toast.error(job.error || "Job failed");
          }
          if (attempts > 120) { clearInterval(poll); setLoading(false); toast.error("Timed out"); }
        } catch { /* retry */ }
      }, 3000);
    } catch (err: any) {
      toast.error(err.message || "Failed to start research");
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="AI Research Agent"
        subtitle="Deep competitive analysis, content gaps, and AI-driven recommendations for any URL + keyword."
        icon={Bot}
        accent="#8B5CF6"
        chips={profileContext && (
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium rounded-full px-3 py-1"
            style={{ background: "rgba(139,92,246,0.12)", color: "#A78BFA", border: "1px solid rgba(139,92,246,0.3)" }}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {profileContext}
          </span>
        )}
      />

      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Website URL</label>
              <input type="url" value={url} onChange={e => setUrl(e.target.value)}
                className="input-field" placeholder="https://example.com" required />
            </div>
            <div>
              <label className="label flex items-center gap-1.5">
                Primary Keyword
                {businessProfile?.city && (
                  <span className="text-[10px] bg-zinc-700/50 text-zinc-400 rounded px-1.5 py-0.5 flex items-center gap-1">
                    <MapPin className="w-2.5 h-2.5" /> {businessProfile.city}
                  </span>
                )}
              </label>
              <input type="text" value={keyword} onChange={e => setKeyword(e.target.value)}
                className="input-field" placeholder="e.g. best seo tools india" required />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Target Region</label>
              <Select
                icon={Globe2}
                accent="#22D3EE"
                widthClass="w-full"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                options={[
                  { value: "IN", label: "India" },
                  { value: "US", label: "United States" },
                  { value: "GB", label: "United Kingdom" },
                  { value: "SG", label: "Singapore" },
                ]}
              />
            </div>
            <div>
              <label className="label">Language</label>
              <Select
                icon={Languages}
                accent="#EC4899"
                widthClass="w-full"
                value={locale}
                onChange={(e) => setLocale(e.target.value)}
                options={[
                  { value: "en-US", label: "English (US)" },
                  { value: "en-IN", label: "English (India)" },
                  { value: "hi-IN", label: "Hindi" },
                ]}
              />
            </div>
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 px-6">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Analysing…" : "Run AI Research"}
          </button>
        </form>
      </div>

      {/* Suggested keywords from profile */}
      {businessProfile && businessProfile.keywords.length > 1 && !loading && !result && (
        <div className="card p-4 mb-6">
          <p className="text-xs text-zinc-500 mb-2 font-medium uppercase tracking-wider">Your project keywords — click to analyse</p>
          <div className="flex flex-wrap gap-2">
            {businessProfile.keywords.map((kw) => {
              const localKw = businessProfile.city ? `${kw} in ${businessProfile.city}` : kw;
              return (
                <button
                  key={kw}
                  onClick={() => setKeyword(localKw)}
                  className="text-xs bg-zinc-800/60 border border-zinc-700/40 text-zinc-300 rounded-full px-3 py-1.5 hover:bg-brand-600/20 hover:border-brand-500/30 hover:text-brand-300 transition-all"
                >
                  {localKw}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Logs */}
      {loading && logs.length > 0 && (
        <div className="card p-4 mb-6 font-mono text-xs space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-2 text-zinc-400">
              <span className="text-zinc-600">{String(i + 1).padStart(2, "0")}</span>
              <span>{log}</span>
            </div>
          ))}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Score row */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "SEO Score", value: Math.round(result.result?.seo_score ?? result.seo_score ?? 0), unit: "/100" },
              { label: "Competitors", value: result.result?.competitor_profiles?.length ?? result.competitor_profiles?.length ?? 0, unit: " found" },
              { label: "Content Gaps", value: result.result?.gap_analysis?.missing_entities?.length ?? result.gap_analysis?.missing_entities?.length ?? 0, unit: " items" },
            ].map((m) => (
              <div key={m.label} className="card p-4 text-center">
                <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">{m.label}</div>
                <div className={cn("text-3xl font-bold font-serif", m.label === "SEO Score" ? scoreColor(m.value) : "")}>
                  {m.value}<span className="text-sm font-normal text-zinc-500">{m.unit}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Analyst summary — what this means in plain language */}
          {(result.result?.analyst_summary ?? result.analyst_summary) && (
            <div className="card p-6 border border-brand-500/25 bg-brand-500/5">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-brand-400" /> What this means
              </h3>
              <p className="text-sm text-zinc-300 leading-relaxed">
                {result.result?.analyst_summary ?? result.analyst_summary}
              </p>
            </div>
          )}

          {/* Who you're up against */}
          {(result.result?.competitor_profiles ?? result.competitor_profiles ?? []).length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-3 text-sm text-zinc-300">Pages currently ranking for this keyword</h3>
              <div className="flex flex-wrap gap-2">
                {(result.result?.competitor_profiles ?? result.competitor_profiles ?? []).map((c: any, i: number) => {
                  let domain = c.url;
                  try { domain = new URL(c.url).hostname.replace(/^www\./, ""); } catch { /* keep raw */ }
                  return (
                    <span key={i} className="px-3 py-1.5 rounded-full text-xs bg-zinc-800/60 border border-zinc-700 text-zinc-300">
                      #{i + 1} {domain}
                      <span className="text-zinc-500 ml-1.5">{c.word_count?.toLocaleString?.() ?? c.word_count} words</span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {(result.result?.recommendations ?? result.recommendations ?? []).length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-brand-400" /> AI Recommendations</h3>
              <div className="space-y-3">
                {(result.result?.recommendations ?? result.recommendations ?? []).slice(0, 8).map((r: string, i: number) => {
                  const isCrit = r.includes("[CRITICAL]");
                  const isWarn = r.includes("[WARNING]");
                  const isHigh = r.includes("[HIGH]");
                  const clean = r.replace("[CRITICAL] ", "").replace("[WARNING] ", "").replace("[HIGH] ", "").replace("[MEDIUM] ", "");
                  return (
                    <div key={i} className={cn("p-3 rounded-lg border text-sm", isCrit ? "bg-red-500/5 border-red-500/20" : isWarn ? "bg-orange-500/5 border-orange-500/20" : isHigh ? "bg-amber-500/5 border-amber-500/20" : "bg-zinc-800/30 border-zinc-700/30")}>
                      <span className={cn("text-[10px] font-bold uppercase mr-2", isCrit ? "text-red-400" : isWarn ? "text-orange-400" : isHigh ? "text-amber-400" : "text-blue-400")}>
                        {isCrit ? "Critical" : isWarn ? "Warning" : isHigh ? "High" : "Medium"}
                      </span>
                      {clean}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
