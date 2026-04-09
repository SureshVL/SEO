"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowRight, ArrowUpRight, BarChart3, Bot, FileText,
  Globe, MapPin, Search, Shield, Sparkles, TrendingUp, Zap,
} from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  healthCheck, listJobs, listProjects, listProjectKeywords, getJobReportUrl,
} from "@/lib/api";

export default function DashboardPage() {
  const { apiKey, businessProfile, ga4Connected, gscConnected } = useAppStore();

  const [aiStatus, setAiStatus] = useState<string>("checking...");
  const [jobs, setJobs] = useState<any[]>([]);
  const [projectCount, setProjectCount] = useState<number | null>(null);
  const [keywordCount, setKeywordCount] = useState<number | null>(null);
  const [avgScore, setAvgScore] = useState<number | null>(null);

  useEffect(() => {
    healthCheck()
      .then((d) => setAiStatus(d.ai))
      .catch(() => setAiStatus("offline"));

    listJobs(apiKey)
      .then((j) => {
        setJobs(j);
        // Derive avg SEO score from completed job results
        const scores = j
          .filter((x) => x.status === "completed" && x.result?.result?.seo_score != null)
          .map((x) => x.result.result.seo_score as number);
        if (scores.length) setAvgScore(Math.round(scores.reduce((a, b) => a + b, 0) / scores.length));
      })
      .catch(() => {});

    listProjects(apiKey)
      .then((ps) => {
        setProjectCount(ps.length);
        // Count keywords for the profile project or first project
        const targetId = businessProfile?.projectId || ps[0]?.id;
        if (targetId) {
          listProjectKeywords(targetId, apiKey)
            .then((kws) => setKeywordCount(kws.length))
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, [apiKey, businessProfile]);

  const stats = [
    {
      label: "Active Projects",
      value: projectCount !== null ? projectCount.toString() : "—",
      icon: Globe,
      color: "text-brand-400",
      href: "/dashboard/projects",
    },
    {
      label: "Tracked Keywords",
      value: keywordCount !== null ? keywordCount.toString() : "—",
      icon: Search,
      color: "text-teal-400",
      href: "/dashboard/rank-tracker",
    },
    {
      label: "AI Jobs Run",
      value: jobs.length.toString(),
      icon: Bot,
      color: "text-amber-400",
      href: "/dashboard/research",
    },
    {
      label: "Avg SEO Score",
      value: avgScore !== null ? avgScore.toString() : "—",
      icon: TrendingUp,
      color: avgScore !== null ? scoreColor(avgScore) : "text-emerald-400",
      href: "/dashboard/research",
    },
  ];

  const quickActions = [
    { label: "AI Research", href: "/dashboard/research", icon: Bot, desc: "Analyse a URL vs competitors", color: "text-brand-400", bg: "bg-brand-500/10" },
    { label: "Keyword Research", href: "/dashboard/keywords", icon: Search, desc: "Opportunities with Claude", color: "text-teal-400", bg: "bg-teal-500/10" },
    { label: "Technical Audit", href: "/dashboard/audit", icon: Shield, desc: "PageSpeed + SEO audit", color: "text-amber-400", bg: "bg-amber-500/10" },
    { label: "SEO Report", href: "/dashboard/reports", icon: FileText, desc: "AI report with trend table", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  ];

  const completedJobs = jobs.filter((j) => j.status === "completed");
  const runningJobs = jobs.filter((j) => j.status === "running" || j.status === "pending");

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">
            {businessProfile ? `Welcome back · ${businessProfile.projectName}` : "Dashboard"}
          </h1>
          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className="text-sm text-zinc-400">
              AI engine:{" "}
              <span className={aiStatus === "enabled" ? "text-emerald-400" : "text-amber-400"}>
                {aiStatus}
              </span>
            </span>
            {businessProfile?.city && (
              <span className="flex items-center gap-1 text-xs bg-zinc-800/60 border border-zinc-700/40 text-zinc-400 rounded-full px-2.5 py-1">
                <MapPin className="w-3 h-3" /> {businessProfile.city}
              </span>
            )}
            {businessProfile?.businessTypeLabel && (
              <span className="text-xs bg-zinc-800/60 border border-zinc-700/40 text-zinc-400 rounded-full px-2.5 py-1">
                {businessProfile.businessTypeLabel}
              </span>
            )}
            {(ga4Connected || gscConnected) && (
              <span className="flex items-center gap-1 text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full px-2.5 py-1">
                <Zap className="w-3 h-3" />
                {[ga4Connected && "GA4", gscConnected && "GSC"].filter(Boolean).join(" + ")} connected
              </span>
            )}
          </div>
        </div>

        {runningJobs.length > 0 && (
          <div className="flex items-center gap-2 text-xs bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg px-3 py-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            {runningJobs.length} job{runningJobs.length > 1 ? "s" : ""} running
          </div>
        )}
      </div>

      {/* Onboarding nudge */}
      {!businessProfile && (
        <Link href="/onboarding" className="block card p-4 mb-6 border-brand-500/20 bg-brand-500/5 hover:bg-brand-500/10 transition-colors group">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-brand-400" />
            <div className="flex-1">
              <p className="text-sm font-medium text-brand-300">Complete your business profile</p>
              <p className="text-xs text-zinc-500 mt-0.5">Add your city, business type, and keywords to auto-fill all tools.</p>
            </div>
            <ArrowRight className="w-4 h-4 text-brand-400 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <Link key={s.label} href={s.href} className="metric-card hover:border-zinc-600/50 transition-colors group">
            <div className="flex items-center justify-between mb-3">
              <span className="metric-label">{s.label}</span>
              <s.icon className={cn("w-4 h-4", s.color)} />
            </div>
            <div className={cn("metric-value", s.color)}>{s.value}</div>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-3">Quick actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {quickActions.map((a) => (
          <Link key={a.href} href={a.href} className="card-hover p-5 group">
            <div className="flex items-center justify-between mb-3">
              <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center", a.bg)}>
                <a.icon className={cn("w-4 h-4", a.color)} />
              </div>
              <ArrowUpRight className="w-4 h-4 text-zinc-600 group-hover:text-brand-400 transition-colors" />
            </div>
            <h3 className="font-medium text-sm mb-1">{a.label}</h3>
            <p className="text-xs text-zinc-500">{a.desc}</p>
          </Link>
        ))}
      </div>

      {/* Recent jobs */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">Recent jobs</h2>
        {completedJobs.length > 0 && (
          <Link href="/dashboard/reports" className="text-xs text-brand-400 hover:text-brand-300">
            View reports →
          </Link>
        )}
      </div>

      {jobs.length === 0 ? (
        <div className="card p-10 text-center">
          <Bot className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <p className="text-zinc-400 text-sm mb-4">No jobs yet. Run your first AI analysis.</p>
          <Link href="/dashboard/research" className="btn-primary text-sm inline-flex items-center gap-1.5">
            Run first analysis <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                {["Job ID", "Status", "Score", "Created", ""].map((h) => (
                  <th key={h} className={cn(
                    "px-5 py-3 text-zinc-500 font-medium text-xs uppercase tracking-wider",
                    h === "" ? "text-right" : "text-left"
                  )}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 8).map((job) => {
                const score = job.result?.result?.seo_score ?? job.result?.final_score ?? null;
                return (
                  <tr key={job.job_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-zinc-300">{job.job_id.slice(0, 8)}…</td>
                    <td className="px-5 py-3">
                      <span className={cn("badge", {
                        "badge-success": job.status === "completed",
                        "badge-warning": job.status === "running",
                        "badge-error": job.status === "failed",
                        "badge-info": job.status === "pending",
                      })}>{job.status}</span>
                    </td>
                    <td className="px-5 py-3">
                      {score !== null ? (
                        <span className={cn("font-semibold text-sm", scoreColor(score))}>
                          {Math.round(score)}
                        </span>
                      ) : (
                        <span className="text-zinc-600 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-zinc-400 text-xs">
                      {new Date(job.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <Link href={`/dashboard/research?job=${job.job_id}`} className="text-brand-400 hover:text-brand-300 text-xs">
                          View →
                        </Link>
                        {job.status === "completed" && (
                          <a
                            href={getJobReportUrl(job.job_id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-zinc-500 hover:text-emerald-400 text-xs transition-colors"
                            title="Download PDF report"
                          >
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
