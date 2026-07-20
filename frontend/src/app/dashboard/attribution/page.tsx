"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  BarChart3,
  Coins,
  DollarSign,
  Loader2,
  MousePointer,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { attributionReport, type AttributionReport } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const DATE_RANGES = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];

export default function AttributionPage() {
  const {
    apiKey,
    ga4Connected,
    gscConnected,
    ga4PropertyId,
    gscSiteUrl,
    ga4AccessToken,
    gscAccessToken,
  } = useAppStore();

  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AttributionReport | null>(null);

  const bothConnected = ga4Connected && gscConnected;
  const haveTokens = Boolean(ga4AccessToken && gscAccessToken);

  async function handleRun() {
    if (!haveTokens) {
      toast.error("Reconnect GA4 and GSC from Settings to refresh tokens.");
      return;
    }
    setLoading(true);
    setReport(null);
    try {
      const data = await attributionReport(
        {
          // tokens are used server-side by project_id; any in-memory tokens
          // are sent only as a same-session fallback.
          ga4_access_token: ga4AccessToken || undefined,
          ga4_property_id: ga4PropertyId,
          gsc_access_token: gscAccessToken || undefined,
          gsc_site_url: gscSiteUrl,
          date_range_days: days,
          top_n: 15,
          project_id: useAppStore.getState().currentProject?.id,
        },
        apiKey,
      );
      setReport(data);
      if (data.warnings.length) {
        data.warnings.forEach(w => toast.warning(w));
      } else {
        toast.success(
          `$${data.ga4.organic_revenue.toLocaleString()} organic revenue over ${days}d`,
        );
      }
    } catch (err: any) {
      toast.error(err.message || "Attribution report failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Revenue Attribution"
        subtitle="Which keywords and pages actually drive organic revenue — GA4 landing-page revenue merged with Search Console query data."
        icon={Coins}
        accent="#F97316"
      />

      {!bothConnected && (
        <div className="card p-6 border border-amber-500/30 bg-amber-500/5 mb-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-200 mb-1">
                Connect GA4 and Search Console
              </h3>
              <p className="text-sm text-zinc-300 mb-3">
                Attribution needs both GA4 (for revenue) and Google Search
                Console (for keyword-level clicks). Connect them from Settings.
              </p>
              <Link
                href="/dashboard/settings"
                className="btn-primary inline-flex items-center gap-2 text-sm"
              >
                Go to Settings
              </Link>
            </div>
          </div>
        </div>
      )}

      {bothConnected && !haveTokens && (
        <div className="card p-4 border border-rose-500/30 bg-rose-500/5 mb-6 text-sm text-rose-200">
          Google access tokens are missing or expired. Reconnect from{" "}
          <Link href="/dashboard/settings" className="underline">
            Settings
          </Link>
          .
        </div>
      )}

      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            {DATE_RANGES.map(r => (
              <button
                key={r.days}
                onClick={() => setDays(r.days)}
                className={cn(
                  "px-3 py-1.5 text-sm rounded-lg border transition",
                  days === r.days
                    ? "bg-amber-500/10 border-amber-500/50 text-amber-200"
                    : "border-zinc-700 text-zinc-400 hover:text-zinc-200",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleRun}
            disabled={loading || !bothConnected || !haveTokens}
            className="btn-primary flex items-center gap-2 px-6 h-[42px]"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {loading ? "Pulling data..." : "Run attribution"}
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat
              icon={<DollarSign className="w-4 h-4" />}
              label="Organic revenue"
              value={`$${report.ga4.organic_revenue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`}
              sub={`${report.ga4.organic_revenue_share_pct}% of total`}
              accent="ok"
            />
            <Stat
              icon={<TrendingUp className="w-4 h-4" />}
              label="Organic sessions"
              value={report.ga4.organic_sessions.toLocaleString()}
              sub={`${report.ga4.organic_share_pct}% of total`}
            />
            <Stat
              icon={<MousePointer className="w-4 h-4" />}
              label="GSC clicks"
              value={report.gsc.total_clicks.toLocaleString()}
              sub={`${report.gsc.total_impressions.toLocaleString()} impressions`}
            />
            <Stat
              icon={<BarChart3 className="w-4 h-4" />}
              label="Avg position"
              value={report.gsc.avg_position.toFixed(1)}
              sub={`over top ${report.top_queries.length} queries`}
            />
          </div>

          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200">
              Top pages by organic revenue
            </h3>
            {report.top_pages.length === 0 ? (
              <div className="text-sm text-zinc-500">
                No revenue-attributable pages in this window.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-zinc-500 border-b border-zinc-800">
                      <th className="py-2">Page</th>
                      <th className="py-2 text-right">Organic revenue</th>
                      <th className="py-2 text-right">Organic sessions</th>
                      <th className="py-2 text-right">GSC clicks</th>
                      <th className="py-2 text-right">Avg pos</th>
                      <th className="py-2">Top queries</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_pages.map((p, i) => (
                      <tr key={i} className="border-b border-zinc-800/50 align-top">
                        <td className="py-2 max-w-[260px] truncate text-amber-300">
                          {p.page_path}
                        </td>
                        <td className="py-2 text-right text-emerald-300 font-medium">
                          ${p.organic_revenue.toLocaleString()}
                        </td>
                        <td className="py-2 text-right text-zinc-300">
                          {p.organic_sessions.toLocaleString()}
                        </td>
                        <td className="py-2 text-right text-zinc-300">
                          {p.gsc_clicks.toLocaleString()}
                        </td>
                        <td className="py-2 text-right text-zinc-400">
                          {p.avg_position ? p.avg_position.toFixed(1) : "—"}
                        </td>
                        <td className="py-2 text-zinc-400">
                          {p.top_queries.length === 0
                            ? "—"
                            : p.top_queries.map(q => q.query).slice(0, 3).join(" · ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200">
              Top queries by attributed revenue
            </h3>
            {report.top_queries.length === 0 ? (
              <div className="text-sm text-zinc-500">
                No GSC queries matched. Check the connected site URL.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-zinc-500 border-b border-zinc-800">
                      <th className="py-2">Query</th>
                      <th className="py-2 text-right">Attributed $</th>
                      <th className="py-2 text-right">Clicks</th>
                      <th className="py-2 text-right">Impr.</th>
                      <th className="py-2 text-right">CTR</th>
                      <th className="py-2 text-right">Pos</th>
                      <th className="py-2">Landing pages</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_queries.map((q, i) => (
                      <tr key={i} className="border-b border-zinc-800/50 align-top">
                        <td className="py-2 text-zinc-200 font-medium">{q.query}</td>
                        <td className="py-2 text-right text-emerald-300 font-medium">
                          {q.attributed_revenue
                            ? `$${q.attributed_revenue.toLocaleString()}`
                            : "—"}
                        </td>
                        <td className="py-2 text-right text-zinc-300">
                          {q.clicks.toLocaleString()}
                        </td>
                        <td className="py-2 text-right text-zinc-400">
                          {q.impressions.toLocaleString()}
                        </td>
                        <td className="py-2 text-right text-zinc-400">
                          {q.ctr.toFixed(1)}%
                        </td>
                        <td className="py-2 text-right text-zinc-400">
                          {q.position.toFixed(1)}
                        </td>
                        <td className="py-2 max-w-[260px] truncate text-zinc-500">
                          {q.landing_pages.slice(0, 2).join(" · ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  accent?: "ok" | "warn";
}) {
  const color =
    accent === "ok"
      ? "text-emerald-400"
      : accent === "warn"
      ? "text-amber-400"
      : "text-zinc-100";
  return (
    <div className="bg-zinc-800/30 rounded-lg p-4 border border-zinc-800">
      <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-wider mb-2">
        <span className="text-zinc-400">{icon}</span>
        {label}
      </div>
      <div className={cn("text-3xl font-semibold font-serif", color)}>{value}</div>
      {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
    </div>
  );
}
