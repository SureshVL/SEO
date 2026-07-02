"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowRight, ArrowUpRight, BarChart3, Bot, Calendar, FileText, Grid3x3,
  Link2, MapPin, Palette, Search, Shield, Sparkles, Zap,
} from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  healthCheck, listJobs, listProjects, listProjectKeywords, getJobReportUrl,
} from "@/lib/api";

type KpiTab = "projects" | "keywords" | "score";

// ── Electric palette ──────────────────────────────────────────────
const VIOLET = "#8B5CF6";
const MAGENTA = "#EC4899";
const CYAN = "#22D3EE";
const LIME = "#A3E635";
const SUN = "#FACC15";
const ORANGE = "#F97316";
const INK = "#17191F";  // card body bg

export default function DashboardPage() {
  const { apiKey, businessProfile, ga4Connected, gscConnected } = useAppStore();

  const [aiStatus, setAiStatus] = useState<string>("checking...");
  const [jobs, setJobs] = useState<any[]>([]);
  const [projectCount, setProjectCount] = useState<number | null>(null);
  const [keywordCount, setKeywordCount] = useState<number | null>(null);
  const [avgScore, setAvgScore] = useState<number | null>(null);
  const [kpiTab, setKpiTab] = useState<KpiTab>("projects");

  useEffect(() => {
    healthCheck().then(d => setAiStatus(d.ai)).catch(() => setAiStatus("offline"));
    listJobs(apiKey).then(j => {
      setJobs(j);
      const scores = j
        .filter(x => x.status === "completed" && x.result?.result?.seo_score != null)
        .map(x => x.result.result.seo_score as number);
      if (scores.length) setAvgScore(Math.round(scores.reduce((a, b) => a + b, 0) / scores.length));
    }).catch(() => {});
    listProjects(apiKey).then(ps => {
      setProjectCount(ps.length);
      const targetId = businessProfile?.projectId || ps[0]?.id;
      if (targetId) listProjectKeywords(targetId, apiKey).then(kw => setKeywordCount(kw.length)).catch(() => {});
    }).catch(() => {});
  }, [apiKey, businessProfile]);

  const completedJobs = jobs.filter(j => j.status === "completed");
  const runningJobs = jobs.filter(j => j.status === "running" || j.status === "pending");

  // Week of month for workflow badge
  const now = new Date();
  const day = now.getDate();
  const month = now.toLocaleDateString("en-US", { month: "short" });
  const weekOfMonth = day <= 7 ? 1 : day <= 14 ? 2 : day <= 21 ? 3 : 4;
  const weekLabels = ["Technical", "Content", "Rankings", "Links"];
  const weekColors = [CYAN, LIME, MAGENTA, ORANGE];

  const kpiValue =
    kpiTab === "projects" ? (projectCount ?? 0) :
    kpiTab === "keywords" ? (keywordCount ?? 0) :
    (avgScore ?? 0);
  const kpiSuffix =
    kpiTab === "projects" ? "Project" + (kpiValue === 1 ? "" : "s") :
    kpiTab === "keywords" ? "Keyword" + (kpiValue === 1 ? "" : "s") :
    "/100";
  const kpiColor =
    kpiTab === "projects" ? VIOLET :
    kpiTab === "keywords" ? CYAN :
    LIME;
  const kpiStrip =
    kpiTab === "projects" ? "Active Projects · Strategic KPI" :
    kpiTab === "keywords" ? "Tracked Keywords · Strategic KPI" :
    "Average SEO Score · Strategic KPI";

  const actions = [
    { label: "AI Research",    href: "/dashboard/research",     icon: Bot,       bg: VIOLET,  text: "#fff" },
    { label: "Keywords",       href: "/dashboard/keywords",     icon: Search,    bg: CYAN,    text: "#0b1020" },
    { label: "Rank Tracker",   href: "/dashboard/rank-tracker", icon: BarChart3, bg: MAGENTA, text: "#fff" },
    { label: "Audit",          href: "/dashboard/audit",        icon: Shield,    bg: LIME,    text: "#0b1020" },
    { label: "Brief",          href: "/dashboard/brief",        icon: Sparkles,  bg: ORANGE,  text: "#fff" },
    { label: "Content Studio", href: "/dashboard/content",      icon: FileText,  bg: "#6366F1", text: "#fff" },
    { label: "Bulk Content",   href: "/dashboard/bulk-content", icon: Grid3x3,   bg: "#EC4899", text: "#fff" },
    { label: "Calendar",       href: "/dashboard/calendar",     icon: Calendar,  bg: "#F97316", text: "#fff" },
    { label: "Programmatic",   href: "/dashboard/programmatic", icon: Grid3x3,   bg: SUN,     text: "#0b1020" },
    { label: "Link Building",  href: "/dashboard/links",        icon: Link2,     bg: "#14B8A6", text: "#fff" },
    { label: "White-label",    href: "/dashboard/branding",     icon: Palette,   bg: "#F43F5E", text: "#fff" },
    { label: "Workflow",       href: "/dashboard/workflow",     icon: Calendar,  bg: "#0EA5E9", text: "#fff" },
  ];

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {businessProfile ? `Welcome back · ${businessProfile.projectName}` : "Dashboard"}
          </h1>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className={cn(
              "inline-flex items-center gap-1.5 text-xs font-semibold rounded-full px-3 py-1",
              aiStatus === "enabled" ? "text-emerald-300" : "text-amber-300",
            )} style={{ background: aiStatus === "enabled" ? "rgba(163,230,53,0.12)" : "rgba(250,204,21,0.12)" }}>
              <span className={cn("w-1.5 h-1.5 rounded-full", aiStatus === "enabled" ? "bg-emerald-400" : "bg-amber-400")} />
              AI {aiStatus}
            </span>
            {businessProfile?.city && (
              <span className="inline-flex items-center gap-1 text-xs rounded-full px-3 py-1" style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-muted)" }}>
                <MapPin className="w-3 h-3" /> {businessProfile.city}
              </span>
            )}
            {businessProfile?.businessTypeLabel && (
              <span className="text-xs rounded-full px-3 py-1" style={{ background: "rgba(255,255,255,0.06)", color: "var(--text-muted)" }}>
                {businessProfile.businessTypeLabel}
              </span>
            )}
            {(ga4Connected || gscConnected) && (
              <span className="inline-flex items-center gap-1 text-xs rounded-full px-3 py-1" style={{ background: "rgba(34,211,238,0.12)", color: CYAN }}>
                <Zap className="w-3 h-3" />
                {[ga4Connected && "GA4", gscConnected && "GSC"].filter(Boolean).join(" + ")} connected
              </span>
            )}
          </div>
        </div>
        {runningJobs.length > 0 && (
          <div className="inline-flex items-center gap-2 text-xs font-semibold rounded-full px-3 py-2" style={{ background: `${SUN}22`, color: SUN }}>
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: SUN }} />
            {runningJobs.length} job{runningJobs.length > 1 ? "s" : ""} running
          </div>
        )}
      </div>

      {/* Onboarding nudge — only if no profile yet */}
      {!businessProfile && (
        <Link href="/onboarding" className="block rounded-3xl p-5 mb-4 group transition-transform hover:scale-[1.005]"
              style={{ background: `linear-gradient(135deg, ${VIOLET}, ${MAGENTA})`, color: "#fff" }}>
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5" />
            <div className="flex-1">
              <p className="text-sm font-bold">Complete your business profile</p>
              <p className="text-xs opacity-90 mt-0.5">Add your city, business type, and keywords to auto-fill every tool.</p>
            </div>
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      )}

      {/* ── Bento row 1: KPI hero · jobs stat · workflow week ── */}
      <div className="grid grid-cols-12 gap-4 mb-4">
        {/* Strategic KPIs — tabbed hero */}
        <div className="col-span-12 lg:col-span-7 rounded-3xl overflow-hidden shadow-2xl" style={{ background: INK }}>
          <div className="grid grid-cols-3">
            {([
              ["projects", "Active", VIOLET],
              ["keywords", "Tracked", CYAN],
              ["score", "SEO Score", LIME],
            ] as const).map(([k, label, color]) => {
              const active = kpiTab === k;
              return (
                <button
                  key={k}
                  onClick={() => setKpiTab(k)}
                  className="px-4 py-3 text-xs font-bold uppercase tracking-[0.15em] transition-all"
                  style={{
                    background: active ? color : `${color}26`,
                    color: active ? (color === LIME ? "#0b1020" : "#fff") : "#d7d9e0",
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
          <div className="px-8 py-10 flex items-baseline gap-3 flex-wrap">
            <span className="text-[6.5rem] font-extrabold leading-none tracking-tight" style={{ color: kpiColor }}>
              {kpiValue}
            </span>
            <span className="text-3xl font-semibold text-white/70">{kpiSuffix}</span>
          </div>
          <div className="h-10 flex items-center justify-center text-[11px] font-bold uppercase tracking-[0.25em]"
               style={{ background: kpiColor, color: kpiColor === LIME ? "#0b1020" : "#fff" }}>
            {kpiStrip}
          </div>
        </div>

        {/* Jobs run — big number */}
        <Link href="/dashboard/research"
              className="col-span-6 lg:col-span-3 rounded-3xl overflow-hidden shadow-2xl flex flex-col group transition-transform hover:scale-[1.01]"
              style={{ background: INK }}>
          <div className="flex-1 flex flex-col items-center justify-center p-8">
            <span className="text-7xl font-extrabold leading-none text-white">{jobs.length}</span>
            <span className="text-sm text-white/60 mt-2 font-medium">AI jobs run</span>
          </div>
          <div className="h-10 flex items-center justify-center text-[11px] font-bold uppercase tracking-[0.25em] text-white"
               style={{ background: MAGENTA }}>
            Research Activity
          </div>
        </Link>

        {/* Workflow week — big yellow slab */}
        <Link href="/dashboard/workflow"
              className="col-span-6 lg:col-span-2 rounded-3xl overflow-hidden shadow-2xl flex flex-col p-5 group transition-transform hover:scale-[1.01]"
              style={{ background: SUN, color: "#0b1020" }}>
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.2em] opacity-70">
            Workflow <Calendar className="w-4 h-4" />
          </div>
          <div className="flex-1 flex flex-col justify-end">
            <div className="text-6xl font-black leading-none">W{weekOfMonth}</div>
            <div className="text-sm font-bold mt-1" style={{ color: weekColors[weekOfMonth - 1] === SUN ? "#0b1020" : "#0b1020" }}>
              {weekLabels[weekOfMonth - 1]}
            </div>
            <div className="text-[11px] font-semibold opacity-60 mt-0.5">{month} {day}</div>
          </div>
        </Link>
      </div>

      {/* ── Bento row 2: quick action tiles ── */}
      <h2 className="text-[11px] font-bold uppercase tracking-[0.2em] mb-3" style={{ color: "var(--text-faint)" }}>
        Quick actions
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        {actions.map(a => (
          <Link key={a.href} href={a.href}
                className="rounded-3xl p-5 aspect-square flex flex-col justify-between group transition-transform hover:scale-[1.03] shadow-lg"
                style={{ background: a.bg, color: a.text }}>
            <a.icon className="w-6 h-6" />
            <div>
              <div className="text-sm font-bold leading-tight">{a.label}</div>
              <ArrowUpRight className="w-4 h-4 mt-1.5 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
            </div>
          </Link>
        ))}
      </div>

      {/* ── Recent jobs (kept, but freshened) ── */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--text-faint)" }}>Recent jobs</h2>
        {completedJobs.length > 0 && (
          <Link href="/dashboard/reports" className="text-xs font-semibold" style={{ color: VIOLET }}>
            View reports →
          </Link>
        )}
      </div>
      {jobs.length === 0 ? (
        <div className="rounded-3xl p-10 text-center" style={{ background: INK }}>
          <Bot className="w-10 h-10 mx-auto mb-3 text-white/30" />
          <p className="text-white/60 text-sm mb-4">No jobs yet. Run your first AI analysis.</p>
          <Link href="/dashboard/research"
                className="inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-sm font-bold"
                style={{ background: VIOLET, color: "#fff" }}>
            Run first analysis <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <div className="rounded-3xl overflow-hidden" style={{ background: INK }}>
          <table className="w-full text-sm">
            <thead>
              <tr>
                {["Job ID", "Status", "Score", "Created", ""].map(h => (
                  <th key={h}
                      className={cn("px-5 py-3 font-bold text-[10px] uppercase tracking-[0.2em] text-white/50",
                        h === "" ? "text-right" : "text-left")}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 8).map((job, i) => {
                const score = job.result?.result?.seo_score ?? job.result?.final_score ?? null;
                const pillBg =
                  job.status === "completed" ? `${LIME}33` :
                  job.status === "running" ? `${SUN}33` :
                  job.status === "failed" ? `${MAGENTA}33` : `${CYAN}33`;
                const pillColor =
                  job.status === "completed" ? LIME :
                  job.status === "running" ? SUN :
                  job.status === "failed" ? MAGENTA : CYAN;
                return (
                  <tr key={job.job_id}
                      className="transition-colors"
                      style={{ borderTop: i === 0 ? "none" : "1px solid rgba(255,255,255,0.06)" }}>
                    <td className="px-5 py-3 font-mono text-xs text-white/70">{job.job_id.slice(0, 8)}…</td>
                    <td className="px-5 py-3">
                      <span className="inline-block text-[10px] font-bold uppercase tracking-[0.1em] rounded-full px-2.5 py-1"
                            style={{ background: pillBg, color: pillColor }}>
                        {job.status}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      {score !== null ? (
                        <span className={cn("font-bold text-sm", scoreColor(score))}>{Math.round(score)}</span>
                      ) : <span className="text-white/30 text-xs">—</span>}
                    </td>
                    <td className="px-5 py-3 text-white/50 text-xs">
                      {new Date(job.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <Link href={`/dashboard/research?job=${job.job_id}`} className="text-xs font-semibold" style={{ color: VIOLET }}>
                          View →
                        </Link>
                        {job.status === "completed" && (
                          <a href={getJobReportUrl(job.job_id)} target="_blank" rel="noopener noreferrer"
                             className="flex items-center gap-1 text-xs font-semibold" style={{ color: LIME }}>
                            <FileText className="w-3 h-3" /> PDF
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
