"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, BarChart3, Bot, FileText, Globe, Search, Shield, TrendingUp } from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { healthCheck, listJobs } from "@/lib/api";

export default function DashboardPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [aiStatus, setAiStatus] = useState<string>("checking...");
  const [jobs, setJobs] = useState<any[]>([]);

  useEffect(() => {
    healthCheck().then((d) => setAiStatus(d.ai)).catch(() => setAiStatus("offline"));
    listJobs(apiKey).then(setJobs).catch(() => {});
  }, [apiKey]);

  const stats = [
    { label: "Active Projects", value: "—", icon: Globe, color: "text-brand-400" },
    { label: "Tracked Keywords", value: "—", icon: Search, color: "text-teal-400" },
    { label: "AI Reports Generated", value: jobs.length.toString(), icon: Bot, color: "text-amber-400" },
    { label: "Avg SEO Score", value: "—", icon: TrendingUp, color: "text-emerald-400" },
  ];

  const quickActions = [
    { label: "Run AI Research", href: "/dashboard/research", icon: Bot, desc: "Analyze a URL against competitors" },
    { label: "Keyword Research", href: "/dashboard/keywords", icon: Search, desc: "Find opportunities with AI" },
    { label: "Technical Audit", href: "/dashboard/audit", icon: Shield, desc: "Full PageSpeed + SEO audit" },
    { label: "Generate Content", href: "/dashboard/content", icon: FileText, desc: "AI-written SEO articles" },
  ];

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-zinc-400 mt-1">
          AI engine: <span className={aiStatus === "enabled" ? "text-emerald-400" : "text-amber-400"}>{aiStatus}</span>
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <div key={s.label} className="metric-card">
            <div className="flex items-center justify-between mb-3">
              <span className="metric-label">{s.label}</span>
              <s.icon className={cn("w-4 h-4", s.color)} />
            </div>
            <div className={cn("metric-value", s.color)}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <h2 className="text-lg font-semibold mb-4">Quick actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {quickActions.map((a) => (
          <Link key={a.href} href={a.href} className="card-hover p-5 group">
            <div className="flex items-center justify-between mb-3">
              <div className="w-9 h-9 rounded-lg bg-brand-500/10 flex items-center justify-center">
                <a.icon className="w-4.5 h-4.5 text-brand-400" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-zinc-600 group-hover:text-brand-400 transition-colors" />
            </div>
            <h3 className="font-medium text-sm mb-1">{a.label}</h3>
            <p className="text-xs text-zinc-500">{a.desc}</p>
          </Link>
        ))}
      </div>

      {/* Recent Jobs */}
      <h2 className="text-lg font-semibold mb-4">Recent jobs</h2>
      {jobs.length === 0 ? (
        <div className="card p-8 text-center">
          <Bot className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <p className="text-zinc-400 text-sm mb-4">No research jobs yet. Run your first AI analysis to get started.</p>
          <Link href="/dashboard/research" className="btn-primary text-sm inline-flex items-center gap-1.5">
            Run first analysis <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left px-5 py-3 text-zinc-500 font-medium text-xs uppercase tracking-wider">Job ID</th>
                <th className="text-left px-5 py-3 text-zinc-500 font-medium text-xs uppercase tracking-wider">Status</th>
                <th className="text-left px-5 py-3 text-zinc-500 font-medium text-xs uppercase tracking-wider">Created</th>
                <th className="text-right px-5 py-3 text-zinc-500 font-medium text-xs uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 5).map((job) => (
                <tr key={job.job_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20">
                  <td className="px-5 py-3 font-mono text-xs text-zinc-300">{job.job_id.slice(0, 8)}...</td>
                  <td className="px-5 py-3">
                    <span className={cn("badge", {
                      "badge-success": job.status === "completed",
                      "badge-warning": job.status === "running",
                      "badge-error": job.status === "failed",
                      "badge-info": job.status === "pending",
                    })}>{job.status}</span>
                  </td>
                  <td className="px-5 py-3 text-zinc-400">{new Date(job.created_at).toLocaleDateString()}</td>
                  <td className="px-5 py-3 text-right">
                    <Link href={`/dashboard/research?job=${job.job_id}`} className="text-brand-400 hover:text-brand-300 text-xs">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
