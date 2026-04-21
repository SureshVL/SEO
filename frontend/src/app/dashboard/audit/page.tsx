"use client";

import { useState, useEffect, useRef } from "react";
import { Loader2, Shield, Sparkles, Globe, Gauge } from "lucide-react";
import { cn, scoreColor, scoreBg } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  technicalAudit,
  startSiteCrawl,
  getSiteCrawl,
  type SiteCrawlResult,
} from "@/lib/api";
import { toast } from "sonner";

type Tab = "single" | "crawl";

export default function AuditPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [tab, setTab] = useState<Tab>("single");

  // Single-page audit state
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Site crawl state
  const [domain, setDomain] = useState("");
  const [maxPages, setMaxPages] = useState(50);
  const [crawling, setCrawling] = useState(false);
  const [crawl, setCrawl] = useState<SiteCrawlResult | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (businessProfile?.websiteUrl) {
      if (!url) setUrl(businessProfile.websiteUrl);
      if (!domain) {
        const d = businessProfile.websiteUrl
          .replace(/^https?:\/\//, "")
          .replace(/\/$/, "");
        setDomain(d);
      }
    }
  }, [businessProfile]);

  useEffect(() => () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
  }, []);

  async function handleSingleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await technicalAudit(url, apiKey);
      setResult(data);
      toast.success("Audit complete");
    } catch (err: any) {
      toast.error(err.message || "Audit failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCrawlStart(e: React.FormEvent) {
    e.preventDefault();
    if (!domain.trim()) return;
    setCrawling(true);
    setCrawl(null);
    try {
      const started = await startSiteCrawl(domain, maxPages, apiKey);
      setCrawl(started);
      if (started.status === "failed") {
        toast.error(started.error || "Crawl failed to start");
        setCrawling(false);
        return;
      }
      toast.success("Crawl started — polling for results");
      pollTimer.current = setInterval(async () => {
        try {
          const latest = await getSiteCrawl(started.task_id, domain, apiKey);
          setCrawl(latest);
          if (latest.status === "finished" || latest.status === "failed") {
            if (pollTimer.current) clearInterval(pollTimer.current);
            pollTimer.current = null;
            setCrawling(false);
            if (latest.status === "finished") toast.success("Crawl complete");
            else toast.error(latest.error || "Crawl failed");
          }
        } catch (err: any) {
          console.error("poll failed", err);
        }
      }, 6000);
    } catch (err: any) {
      toast.error(err.message || "Crawl start failed");
      setCrawling(false);
    }
  }

  const scoreLabel = (v: number | null) => (v !== null ? Math.round(v) : "—");

  const impactColor = (impact: string) =>
    impact === "critical"
      ? "text-red-400 bg-red-500/10 border-red-500/30"
      : impact === "high"
      ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
      : impact === "medium"
      ? "text-blue-400 bg-blue-500/10 border-blue-500/30"
      : "text-zinc-400 bg-zinc-500/10 border-zinc-500/30";

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-amber-400" /> Technical SEO Audit
        </h1>
        {businessProfile?.websiteUrl && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded-lg px-3 py-1.5 w-fit">
            <Sparkles className="w-3.5 h-3.5" /> Auto-filled from your project
          </div>
        )}
      </div>

      <div className="flex gap-2 mb-6 border-b border-zinc-800">
        <button
          onClick={() => setTab("single")}
          className={cn(
            "px-4 py-2 text-sm font-medium flex items-center gap-2 border-b-2 -mb-px transition",
            tab === "single"
              ? "border-amber-400 text-amber-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200",
          )}
        >
          <Gauge className="w-4 h-4" /> Single-page (PageSpeed)
        </button>
        <button
          onClick={() => setTab("crawl")}
          className={cn(
            "px-4 py-2 text-sm font-medium flex items-center gap-2 border-b-2 -mb-px transition",
            tab === "crawl"
              ? "border-amber-400 text-amber-400"
              : "border-transparent text-zinc-400 hover:text-zinc-200",
          )}
        >
          <Globe className="w-4 h-4" /> Full-site crawl (DataForSEO)
        </button>
      </div>

      {tab === "single" && (
        <>
          <div className="card p-6 mb-6">
            <form onSubmit={handleSingleSubmit} className="flex gap-4">
              <input
                type="url"
                value={url}
                onChange={e => setUrl(e.target.value)}
                className="input-field flex-1"
                placeholder="https://example.com"
                required
              />
              <button
                type="submit"
                disabled={loading}
                className="btn-primary flex items-center gap-2 px-6"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Shield className="w-4 h-4" />
                )}
                {loading ? "Auditing..." : "Run Audit"}
              </button>
            </form>
          </div>

          {result && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Performance", key: "performance" },
                  { label: "Accessibility", key: "accessibility" },
                  { label: "Best Practices", key: "best_practices" },
                  { label: "SEO", key: "seo" },
                ].map(({ label, key }) => {
                  const val =
                    result.lighthouse_scores?.[key] ?? result.scores?.[key] ?? null;
                  return (
                    <div
                      key={key}
                      className={cn(
                        "card p-4 text-center border",
                        val !== null ? scoreBg(val) : "",
                      )}
                    >
                      <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
                        {label}
                      </div>
                      <div
                        className={cn(
                          "text-3xl font-bold font-serif",
                          val !== null ? scoreColor(val) : "text-zinc-400",
                        )}
                      >
                        {scoreLabel(val)}
                      </div>
                    </div>
                  );
                })}
              </div>

              {result.issues?.length > 0 && (
                <div className="card p-6">
                  <h3 className="font-semibold mb-4 text-amber-400">Issues Found</h3>
                  <div className="space-y-2">
                    {result.issues.slice(0, 10).map((issue: any, i: number) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-3 bg-zinc-800/30 rounded-lg text-sm"
                      >
                        <span
                          className={cn(
                            "text-[10px] font-bold uppercase mt-0.5 shrink-0",
                            issue.severity === "critical"
                              ? "text-red-400"
                              : issue.severity === "high"
                              ? "text-amber-400"
                              : "text-blue-400",
                          )}
                        >
                          {issue.severity}
                        </span>
                        <span className="text-zinc-300">
                          {issue.description || issue.message || JSON.stringify(issue)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {tab === "crawl" && (
        <>
          <div className="card p-6 mb-6">
            <form onSubmit={handleCrawlStart} className="grid md:grid-cols-[1fr_140px_auto] gap-3 items-end">
              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Domain
                </label>
                <input
                  type="text"
                  value={domain}
                  onChange={e => setDomain(e.target.value)}
                  className="input-field w-full"
                  placeholder="example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                  Max pages
                </label>
                <input
                  type="number"
                  value={maxPages}
                  min={10}
                  max={1000}
                  step={10}
                  onChange={e => setMaxPages(Number(e.target.value))}
                  className="input-field w-full"
                />
              </div>
              <button
                type="submit"
                disabled={crawling}
                className="btn-primary flex items-center gap-2 px-6 h-[42px]"
              >
                {crawling ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Globe className="w-4 h-4" />
                )}
                {crawling ? "Crawling..." : "Start Crawl"}
              </button>
            </form>
            <p className="text-xs text-zinc-500 mt-3">
              Crawls up to {maxPages} pages via DataForSEO On-Page API. A typical
              50-page crawl finishes in 60–180 seconds.
            </p>
          </div>

          {crawl && (
            <div className="space-y-6">
              <div className="card p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <div className="text-xs text-zinc-500 uppercase tracking-wider">
                      Crawl status
                    </div>
                    <div className="text-lg font-semibold capitalize">
                      {crawl.status}
                      {crawl.status === "crawling" && (
                        <Loader2 className="inline-block w-4 h-4 ml-2 animate-spin text-zinc-400" />
                      )}
                    </div>
                    {crawl.task_id && (
                      <div className="text-[10px] text-zinc-600 mt-1 font-mono">
                        task_id: {crawl.task_id}
                      </div>
                    )}
                  </div>
                  {crawl.onpage_score !== null && crawl.onpage_score !== undefined && (
                    <div className={cn("px-4 py-2 rounded-lg border", scoreBg(crawl.onpage_score))}>
                      <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
                        On-Page Score
                      </div>
                      <div className={cn("text-2xl font-bold font-serif", scoreColor(crawl.onpage_score))}>
                        {Math.round(crawl.onpage_score)}
                      </div>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <Stat label="Pages crawled" value={crawl.pages_crawled} />
                  <Stat label="In queue" value={crawl.pages_in_queue} />
                  <Stat
                    label="Distinct issues"
                    value={Object.keys(crawl.issues_by_check).length}
                  />
                  <Stat label="Actions" value={crawl.actions.length} />
                </div>
                {crawl.error && (
                  <div className="mt-4 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                    {crawl.error}
                  </div>
                )}
              </div>

              {crawl.actions.length > 0 && (
                <div className="card p-6">
                  <h3 className="font-semibold mb-4 text-amber-400">
                    Prioritized Actions ({crawl.actions.length})
                  </h3>
                  <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
                    {crawl.actions.map((a, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-3 bg-zinc-800/30 rounded-lg text-sm"
                      >
                        <span
                          className={cn(
                            "text-[10px] font-bold uppercase mt-0.5 shrink-0 px-2 py-0.5 rounded border",
                            impactColor(a.impact),
                          )}
                        >
                          {a.impact}
                        </span>
                        <div className="flex-1">
                          <div className="text-zinc-200">{a.action}</div>
                          <div className="text-xs text-zinc-500 mt-0.5">
                            {a.category}
                            {a.auto_fixable && " · auto-fixable"}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {crawl.broken_links.length > 0 && (
                <div className="card p-6">
                  <h3 className="font-semibold mb-4 text-red-400">
                    Broken Links ({crawl.broken_links.length})
                  </h3>
                  <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-2 text-xs font-mono">
                    {crawl.broken_links.slice(0, 50).map((l, i) => (
                      <div key={i} className="p-2 bg-zinc-800/30 rounded">
                        <div className="text-red-300 truncate">→ {l.link_to}</div>
                        <div className="text-zinc-500 truncate">from {l.link_from}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {crawl.duplicate_titles.length > 0 && (
                <div className="card p-6">
                  <h3 className="font-semibold mb-4 text-amber-400">
                    Duplicate Titles ({crawl.duplicate_titles.length} groups)
                  </h3>
                  <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 text-sm">
                    {crawl.duplicate_titles.slice(0, 10).map((g, i) => (
                      <div key={i} className="p-3 bg-zinc-800/30 rounded">
                        <div className="text-zinc-200 font-medium truncate">{g.value}</div>
                        <div className="text-xs text-zinc-500 mt-1">
                          {g.pages.length} pages
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {crawl.sample_pages.length > 0 && (
                <div className="card p-6">
                  <h3 className="font-semibold mb-4 text-zinc-200">
                    Sample Pages ({crawl.sample_pages.length})
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="text-xs text-zinc-500 uppercase tracking-wider">
                        <tr className="border-b border-zinc-800">
                          <th className="text-left py-2 pr-3">URL</th>
                          <th className="text-right py-2 px-2">Status</th>
                          <th className="text-right py-2 px-2">Score</th>
                          <th className="text-right py-2 px-2">Words</th>
                          <th className="text-right py-2 pl-2">Issues</th>
                        </tr>
                      </thead>
                      <tbody>
                        {crawl.sample_pages.map((p, i) => (
                          <tr key={i} className="border-b border-zinc-900">
                            <td className="py-2 pr-3 font-mono text-xs text-zinc-300 truncate max-w-md">
                              {p.url}
                            </td>
                            <td
                              className={cn(
                                "text-right py-2 px-2",
                                p.status_code && p.status_code >= 400
                                  ? "text-red-400"
                                  : "text-zinc-400",
                              )}
                            >
                              {p.status_code ?? "—"}
                            </td>
                            <td className="text-right py-2 px-2 text-zinc-400">
                              {p.onpage_score !== null
                                ? Math.round(p.onpage_score)
                                : "—"}
                            </td>
                            <td className="text-right py-2 px-2 text-zinc-400">
                              {p.word_count ?? "—"}
                            </td>
                            <td className="text-right py-2 pl-2 text-amber-400">
                              {p.issues.length}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string | null }) {
  return (
    <div className="bg-zinc-800/30 rounded-lg p-3 border border-zinc-800">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-2xl font-semibold font-serif text-zinc-100">
        {value ?? "—"}
      </div>
    </div>
  );
}
