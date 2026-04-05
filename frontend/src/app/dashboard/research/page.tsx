"use client";

import { useState } from "react";
import { Bot, ExternalLink, Loader2, Search, TrendingUp } from "lucide-react";
import { cn, scoreColor, scoreBg } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { createResearchJob, getJob } from "@/lib/api";
import { toast } from "sonner";

export default function ResearchPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [url, setUrl] = useState("");
  const [keyword, setKeyword] = useState("");
  const [region, setRegion] = useState("IN");
  const [locale, setLocale] = useState("en-US");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

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
          project_id: "",
        },
      }, apiKey);

      setLogs((l) => [...l, `Job created: ${job_id.slice(0, 8)}...`]);

      // Poll for completion
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const job = await getJob(job_id, apiKey);
          if (job.logs) {
            setLogs(job.logs.map((l: any) => l.message));
          }
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
          if (attempts > 120) {
            clearInterval(poll);
            setLoading(false);
            toast.error("Job timed out");
          }
        } catch {
          // retry silently
        }
      }, 3000);
    } catch (err: any) {
      toast.error(err.message || "Failed to start research");
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bot className="w-6 h-6 text-brand-400" /> AI Research Agent
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Analyze any URL against top competitors. Claude AI scores your page and generates actionable recommendations.
        </p>
      </div>

      {/* Input Form */}
      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Website URL</label>
              <input
                type="url" value={url} onChange={(e) => setUrl(e.target.value)}
                className="input-field" placeholder="https://yoursite.com/page" required
              />
            </div>
            <div>
              <label className="label">Target Keyword</label>
              <input
                type="text" value={keyword} onChange={(e) => setKeyword(e.target.value)}
                className="input-field" placeholder="e.g. best crm software india" required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="label">Region</label>
              <select value={region} onChange={(e) => setRegion(e.target.value)} className="input-field">
                <option value="IN">India</option>
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
                <option value="AU">Australia</option>
                <option value="SG">Singapore</option>
              </select>
            </div>
            <div>
              <label className="label">Language</label>
              <select value={locale} onChange={(e) => setLocale(e.target.value)} className="input-field">
                <option value="en-US">English</option>
                <option value="hi-IN">Hindi</option>
                <option value="es-ES">Spanish</option>
              </select>
            </div>
            <div className="col-span-2 flex items-end">
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {loading ? "Analyzing..." : "Run AI Analysis"}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Live Logs */}
      {logs.length > 0 && (
        <div className="card p-4 mb-6">
          <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider mb-3">Agent Log</h3>
          <div className="space-y-1 max-h-48 overflow-y-auto font-mono text-xs">
            {logs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 text-zinc-400">
                <span className="text-zinc-600 select-none">{String(i + 1).padStart(2, "0")}</span>
                <span>{log}</span>
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-brand-400">
                <Loader2 className="w-3 h-3 animate-spin" /> Processing...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Score Card */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={cn("card p-6 border", scoreBg(result.final_score))}>
              <div className="metric-label">SEO Score</div>
              <div className={cn("text-4xl font-bold mt-2", scoreColor(result.final_score))}>
                {Math.round(result.final_score)}
              </div>
              <div className="text-xs text-zinc-500 mt-1">out of 100</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Analysis Passes</div>
              <div className="metric-value text-brand-400">{result.attempts}</div>
              <div className="text-xs text-zinc-500 mt-1">{result.passed_threshold ? "Threshold met" : "Needs improvement"}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Competitors Analyzed</div>
              <div className="metric-value text-teal-400">{result.result?.competitor_profiles?.length || 0}</div>
              <div className="text-xs text-zinc-500 mt-1">Top SERP results</div>
            </div>
          </div>

          {/* Recommendations */}
          {result.result?.recommendations && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-brand-400" /> AI Recommendations
              </h3>
              <div className="space-y-3">
                {result.result.recommendations.map((rec: string, i: number) => {
                  const isCritical = rec.startsWith("[CRITICAL]");
                  const isHigh = rec.startsWith("[HIGH]");
                  return (
                    <div
                      key={i}
                      className={cn(
                        "p-3 rounded-lg border text-sm",
                        isCritical ? "bg-red-500/5 border-red-500/20 text-red-300" :
                        isHigh ? "bg-amber-500/5 border-amber-500/20 text-amber-300" :
                        "bg-zinc-800/30 border-zinc-700/50 text-zinc-300"
                      )}
                    >
                      {rec}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Gap Analysis */}
          {result.result?.gap_analysis && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="card p-5">
                <h4 className="text-sm font-medium text-zinc-400 mb-3">Missing Entities</h4>
                <div className="flex flex-wrap gap-1.5">
                  {result.result.gap_analysis.missing_entities?.map((e: string) => (
                    <span key={e} className="badge bg-red-500/10 text-red-400 border-red-500/20 text-xs">{e}</span>
                  ))}
                  {(!result.result.gap_analysis.missing_entities?.length) && <span className="text-xs text-zinc-500">None — good coverage!</span>}
                </div>
              </div>
              <div className="card p-5">
                <h4 className="text-sm font-medium text-zinc-400 mb-3">Missing Questions</h4>
                <div className="space-y-1.5">
                  {result.result.gap_analysis.missing_questions?.slice(0, 5).map((q: string) => (
                    <p key={q} className="text-xs text-zinc-400">{q}</p>
                  ))}
                  {(!result.result.gap_analysis.missing_questions?.length) && <span className="text-xs text-zinc-500">All questions covered!</span>}
                </div>
              </div>
              <div className="card p-5">
                <h4 className="text-sm font-medium text-zinc-400 mb-3">Heading Gaps</h4>
                <div className="space-y-1.5">
                  {result.result.gap_analysis.heading_gaps?.slice(0, 5).map((h: string) => (
                    <p key={h} className="text-xs text-zinc-400">→ {h}</p>
                  ))}
                  {(!result.result.gap_analysis.heading_gaps?.length) && <span className="text-xs text-zinc-500">No gaps!</span>}
                </div>
              </div>
            </div>
          )}

          {/* Competitor Profiles */}
          {result.result?.competitor_profiles && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Competitor Breakdown</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800">
                      <th className="text-left px-4 py-2 text-zinc-500 text-xs uppercase">URL</th>
                      <th className="text-right px-4 py-2 text-zinc-500 text-xs uppercase">Words</th>
                      <th className="text-right px-4 py-2 text-zinc-500 text-xs uppercase">Density</th>
                      <th className="text-right px-4 py-2 text-zinc-500 text-xs uppercase">Entities</th>
                      <th className="text-right px-4 py-2 text-zinc-500 text-xs uppercase">Questions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.result.competitor_profiles.map((c: any) => (
                      <tr key={c.url} className="border-b border-zinc-800/50">
                        <td className="px-4 py-2.5">
                          <a href={c.url} target="_blank" rel="noopener" className="text-brand-400 hover:text-brand-300 flex items-center gap-1 text-xs">
                            {new URL(c.url).hostname} <ExternalLink className="w-3 h-3" />
                          </a>
                        </td>
                        <td className="px-4 py-2.5 text-right text-zinc-300">{c.word_count.toLocaleString()}</td>
                        <td className="px-4 py-2.5 text-right text-zinc-300">{c.keyword_density}%</td>
                        <td className="px-4 py-2.5 text-right text-zinc-300">{c.top_entities?.length || 0}</td>
                        <td className="px-4 py-2.5 text-right text-zinc-300">{c.top_questions?.length || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
