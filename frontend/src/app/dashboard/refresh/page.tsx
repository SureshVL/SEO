"use client";

import { useState } from "react";
import { RefreshCw, Loader2, TrendingDown, FileText, ExternalLink } from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  createDecayRefresh,
  getContentDecay,
  type ContentDecayReport,
  type DecayItem,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export default function ContentRefreshPage() {
  const { apiKey, businessProfile, gscConnected, gscSiteUrl } = useAppStore() as any;
  const projectId = businessProfile?.projectId || "";
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<ContentDecayReport | null>(null);
  const [drafting, setDrafting] = useState<string | null>(null);

  async function scan() {
    if (!projectId) { toast.error("Select a project first."); return; }
    setLoading(true);
    try {
      const r = await getContentDecay(projectId, apiKey, gscSiteUrl || "");
      setReport(r);
      if (r.decayed_count === 0) toast.success(`Checked ${r.pages_analyzed} pages — no decay detected.`);
      else toast.warning(`${r.decayed_count} page(s) losing search traffic.`);
    } catch (err: any) {
      toast.error(err?.message || "Decay scan failed");
    } finally {
      setLoading(false);
    }
  }

  async function draftRefresh(item: DecayItem) {
    setDrafting(item.page);
    try {
      const res = await createDecayRefresh(projectId, {
        page: item.page,
        queries: item.top_queries.map(q => q.query),
        reasons: item.reasons,
      }, apiKey);
      toast.success(
        res.draft_id
          ? `Refresh plan saved to Content Studio: "${res.title}"`
          : `Refresh plan generated: "${res.title}"`,
      );
    } catch (err: any) {
      toast.error(err?.message || "Could not draft refresh");
    } finally {
      setDrafting(null);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Content Refresh"
        subtitle="Watches Search Console for pages losing clicks, impressions or position — then drafts a targeted refresh plan to win the traffic back."
        icon={RefreshCw}
        accent="#34D399"
      />

      <div className="card p-6 mb-6 flex items-center justify-between flex-wrap gap-4">
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>
          Compares the last 28 days against the 28 days before.
          {!gscConnected && (
            <span className="block mt-1 text-amber-400">
              Google Search Console is not connected — connect it in{" "}
              <a href="/dashboard/settings" className="underline">Settings</a> first.
            </span>
          )}
        </div>
        <button onClick={scan} disabled={loading || !projectId} className="btn-primary flex items-center gap-2 px-6">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingDown className="w-4 h-4" />}
          {loading ? "Scanning…" : "Scan for decay"}
        </button>
      </div>

      {report && (
        <div className="space-y-4">
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            {report.pages_analyzed} page(s) analyzed on {report.site_url} ·{" "}
            {report.current_window[0]} → {report.current_window[1]} vs {report.previous_window[0]} → {report.previous_window[1]}
          </div>

          {report.decayed_count === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                No content decay detected. Your pages are holding their ground — re-run after the next content cycle.
              </p>
            </div>
          ) : (
            report.decayed.map((d) => (
              <div key={d.page} className="card p-5">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn(
                        "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
                        d.severity === "critical" ? "bg-rose-500/10 text-rose-300" : "bg-amber-500/10 text-amber-300",
                      )}>
                        {d.severity}
                      </span>
                      <a
                        href={d.page}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm font-medium truncate hover:underline inline-flex items-center gap-1"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {d.page.replace(/^https?:\/\/[^/]+/, "") || d.page}
                        <ExternalLink className="w-3 h-3 opacity-60" />
                      </a>
                    </div>
                    <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {d.reasons.join(" · ")}
                    </div>
                  </div>
                  <button
                    onClick={() => draftRefresh(d)}
                    disabled={drafting !== null}
                    className="btn-secondary flex items-center gap-2 text-xs px-4 py-2 shrink-0"
                  >
                    {drafting === d.page ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                    Draft refresh
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-3 mt-4 text-center">
                  <Metric label="Clicks" prev={d.clicks_prev} now={d.clicks_now} />
                  <Metric label="Impressions" prev={d.impressions_prev} now={d.impressions_now} />
                  <Metric label="Avg position" prev={d.position_prev} now={d.position_now} invert />
                </div>

                {d.top_queries.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {d.top_queries.map((q, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-md text-[10px]"
                        style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}
                        title={`${q.impressions} impressions · pos ${q.position}`}
                      >
                        {q.query}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {!report && !loading && (
        <div className="card p-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Run a scan to see which pages are silently losing search traffic.
        </div>
      )}
    </div>
  );
}

function Metric({ label, prev, now, invert = false }: {
  label: string; prev: number; now: number; invert?: boolean;
}) {
  // For position, up is bad (invert); for clicks/impressions, down is bad.
  const worse = invert ? now > prev : now < prev;
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
      <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>{label}</div>
      <div className="text-sm font-mono">
        <span style={{ color: "var(--text-muted)" }}>{prev}</span>
        <span style={{ color: "var(--text-muted)" }}> → </span>
        <span className={worse ? "text-rose-400 font-semibold" : "text-emerald-400 font-semibold"}>{now}</span>
      </div>
    </div>
  );
}
