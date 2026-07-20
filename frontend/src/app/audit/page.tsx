"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle, ArrowRight, CheckCircle2, Globe, Loader2, Lock, Search, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AuditIssue {
  issue_type: string;
  severity: "critical" | "warning" | "info";
  affected_url: string;
  description: string;
  recommendation: string;
}

interface AuditReport {
  domain: string;
  score: number;
  pages_crawled: number;
  crawl_seconds: number;
  issues_found: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  avg_load_time_ms: number;
  sitemap_found: boolean;
  robots_found: boolean;
  issues: AuditIssue[];
}

const CRAWL_MESSAGES = [
  "Fetching your homepage...",
  "Reading robots.txt and sitemap...",
  "Crawling your pages...",
  "Checking every link for errors...",
  "Measuring page speed...",
  "Scanning for structured data...",
  "Scoring your site...",
];

export default function FreeAuditPage() {
  const [domain, setDomain] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState("");
  const [msgIndex, setMsgIndex] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const msgRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (msgRef.current) clearInterval(msgRef.current);
    };
  }, []);

  const startAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!domain.trim() || !email.trim()) {
      setError("Enter your website and email to run the free audit.");
      return;
    }
    setStatus("running");
    setMsgIndex(0);
    msgRef.current = setInterval(
      () => setMsgIndex((i) => Math.min(i + 1, CRAWL_MESSAGES.length - 1)),
      2500,
    );

    try {
      const res = await fetch(`${API}/public/audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: domain.trim(), email: email.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Could not start the audit.");
      }
      const { audit_id } = await res.json();

      pollRef.current = setInterval(async () => {
        try {
          const poll = await fetch(`${API}/public/audit/${audit_id}`);
          if (!poll.ok) return;
          const data = await poll.json();
          if (data.status === "completed" && data.report) {
            if (pollRef.current) clearInterval(pollRef.current);
            if (msgRef.current) clearInterval(msgRef.current);
            setReport(data.report);
            setStatus("done");
          } else if (data.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            if (msgRef.current) clearInterval(msgRef.current);
            setError(data.error || "We couldn't crawl that site. Check the domain and try again.");
            setStatus("error");
          }
        } catch {
          /* keep polling */
        }
      }, 2000);
    } catch (err: any) {
      if (msgRef.current) clearInterval(msgRef.current);
      setError(err.message || "Something went wrong.");
      setStatus("error");
    }
  };

  const scoreColor = (score: number) =>
    score >= 80 ? "#84CC16" : score >= 50 ? "#F59E0B" : "#EF4444";

  const severityStyles: Record<string, string> = {
    critical: "bg-red-500/10 text-red-400 border-red-500/30",
    warning: "bg-orange-500/10 text-orange-400 border-orange-500/30",
    info: "bg-sky-500/10 text-sky-400 border-sky-500/30",
  };

  return (
    <div className="min-h-screen bg-[#0b1020] text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 max-w-5xl mx-auto">
        <Link href="/" className="flex items-center gap-2">
          <span className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center font-bold">OR</span>
          <span className="font-semibold">OMNI-RANK</span>
        </Link>
        <Link
          href="/auth/signup"
          className="text-sm px-4 py-2 rounded-lg bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:opacity-90 transition"
        >
          Get started
        </Link>
      </header>

      <main className="max-w-5xl mx-auto px-6 pb-24">
        {status !== "done" && (
          <div className="text-center pt-16 pb-10">
            <h1 className="text-4xl md:text-5xl font-bold leading-tight">
              Free Instant <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">SEO Audit</span>
            </h1>
            <p className="mt-4 text-gray-400 max-w-xl mx-auto">
              We crawl your site live — broken links, page speed, missing schema,
              orphan pages and more. Results in about a minute. No credit card.
            </p>
          </div>
        )}

        {status === "idle" || status === "error" ? (
          <form onSubmit={startAudit} className="max-w-xl mx-auto space-y-4">
            <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3">
              <Globe className="w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="yourwebsite.com"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="flex-1 bg-transparent outline-none placeholder:text-gray-500"
              />
            </div>
            <div className="flex items-center gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3">
              <Search className="w-5 h-5 text-gray-400" />
              <input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 bg-transparent outline-none placeholder:text-gray-500"
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              type="submit"
              className="w-full py-3 rounded-xl font-semibold bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:opacity-90 transition flex items-center justify-center gap-2"
            >
              <Zap className="w-5 h-5" />
              Audit my site free
            </button>
            <p className="text-xs text-center text-gray-500">
              We&apos;ll email you the report. No spam, ever.
            </p>
          </form>
        ) : null}

        {(status === "idle" || status === "error") && (
          <section className="max-w-3xl mx-auto mt-20 space-y-6">
            <div>
              <h2 className="text-2xl font-bold">What our free SEO audit checks</h2>
              <p className="mt-3 text-gray-400">
                Search engines and AI answer engines can only rank pages they can
                crawl, understand and trust. Our audit fetches your site the same way
                Googlebot does and grades it against the technical signals that
                actually move rankings — so you see exactly what&apos;s holding you
                back before a competitor does.
              </p>
            </div>

            <p className="text-gray-400">
              In a single pass we inspect <span className="text-white font-medium">crawlability</span>{" "}
              (robots.txt, sitemaps, indexability and orphan pages), your{" "}
              <span className="text-white font-medium">titles and meta descriptions</span>{" "}
              for duplicates and missing tags, and whether pages ship valid{" "}
              <span className="text-white font-medium">structured data (JSON-LD schema)</span>{" "}
              that helps you win rich results and AI citations. We flag{" "}
              <span className="text-white font-medium">thin or duplicate content</span>,{" "}
              <span className="text-white font-medium">broken links and redirect chains</span>,
              and measure real load times and{" "}
              <span className="text-white font-medium">Core Web Vitals</span> so slow,
              unstable pages don&apos;t quietly bleed traffic.
            </p>

            <p className="text-gray-400">
              Every issue comes with a plain-English explanation and a recommended
              fix, prioritized by severity so you tackle the highest-impact problems
              first. It&apos;s the same technical foundation the biggest SEO tools
              charge for — free, instant, and with no credit card required.
            </p>

            <div className="grid sm:grid-cols-2 gap-3 pt-2">
              {[
                { title: "Crawlability & indexing", desc: "Robots.txt, sitemaps, noindex tags and orphan pages." },
                { title: "Titles, meta & headings", desc: "Duplicate, missing or truncated tags across your site." },
                { title: "Structured data", desc: "Valid JSON-LD schema for rich results and AI citations." },
                { title: "Content quality", desc: "Thin, duplicate or low-value pages that dilute rankings." },
                { title: "Links & redirects", desc: "Broken links, 404s and long redirect chains." },
                { title: "Speed & Core Web Vitals", desc: "Load times, LCP, CLS and other performance signals." },
              ].map((f) => (
                <div key={f.title} className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <CheckCircle2 className="w-5 h-5 text-lime-400" />
                  <p className="font-semibold mt-2">{f.title}</p>
                  <p className="text-sm text-gray-400 mt-1">{f.desc}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {status === "running" && (
          <div className="max-w-xl mx-auto text-center py-16">
            <Loader2 className="w-12 h-12 animate-spin mx-auto text-fuchsia-400" />
            <p className="mt-6 text-lg font-medium">{CRAWL_MESSAGES[msgIndex]}</p>
            <p className="mt-2 text-sm text-gray-500">Crawling {domain} — this takes about a minute</p>
          </div>
        )}

        {status === "done" && report && (
          <div className="pt-10 space-y-8">
            {/* Score header */}
            <div className="flex flex-col md:flex-row items-center gap-8 bg-white/5 border border-white/10 rounded-2xl p-8">
              <div className="relative w-36 h-36 shrink-0">
                <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                  <circle cx="60" cy="60" r="52" fill="none" stroke="#ffffff14" strokeWidth="10" />
                  <circle
                    cx="60" cy="60" r="52" fill="none"
                    stroke={scoreColor(report.score)} strokeWidth="10" strokeLinecap="round"
                    strokeDasharray={`${(report.score / 100) * 326.7} 326.7`}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-4xl font-bold" style={{ color: scoreColor(report.score) }}>
                    {report.score}
                  </span>
                  <span className="text-xs text-gray-400">SEO score</span>
                </div>
              </div>
              <div className="flex-1 text-center md:text-left">
                <h2 className="text-2xl font-bold">{report.domain}</h2>
                <p className="text-gray-400 mt-1">
                  {report.pages_crawled} pages crawled in {report.crawl_seconds}s ·
                  avg load {(report.avg_load_time_ms / 1000).toFixed(1)}s
                </p>
                <div className="flex flex-wrap justify-center md:justify-start gap-3 mt-4">
                  <span className="px-3 py-1.5 rounded-full text-sm bg-red-500/10 text-red-400 border border-red-500/30">
                    {report.critical_count} critical
                  </span>
                  <span className="px-3 py-1.5 rounded-full text-sm bg-orange-500/10 text-orange-400 border border-orange-500/30">
                    {report.warning_count} warnings
                  </span>
                  <span className="px-3 py-1.5 rounded-full text-sm bg-sky-500/10 text-sky-400 border border-sky-500/30">
                    {report.info_count} minor
                  </span>
                </div>
              </div>
              <Link
                href="/auth/signup"
                className="px-6 py-3 rounded-xl font-semibold bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:opacity-90 transition flex items-center gap-2 whitespace-nowrap"
              >
                Fix all of this automatically <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {/* Issues */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">
                {report.issues_found} issues found — here&apos;s what&apos;s hurting your rankings
              </h3>
              {report.issues.slice(0, 12).map((issue, idx) => (
                <div key={idx} className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn("px-2 py-0.5 rounded-full text-xs border", severityStyles[issue.severity])}>
                          {issue.severity}
                        </span>
                        <span className="font-medium">{issue.issue_type.replace(/_/g, " ")}</span>
                      </div>
                      <p className="text-sm text-gray-400 mt-1 truncate">{issue.affected_url}</p>
                      <p className="text-sm mt-2">{issue.description}</p>
                    </div>
                    <Link
                      href="/auth/signup"
                      className="shrink-0 flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg border border-white/15 text-gray-300 hover:bg-white/10 transition"
                    >
                      <Lock className="w-3.5 h-3.5" /> Fix it
                    </Link>
                  </div>
                </div>
              ))}
              {report.issues_found > 12 && (
                <div className="relative">
                  <div className="bg-white/5 border border-white/10 rounded-xl p-4 blur-[3px] select-none">
                    <p className="font-medium">+ {report.issues_found - 12} more issues detected</p>
                    <p className="text-sm text-gray-400 mt-1">Full breakdown, fixes and monitoring inside</p>
                  </div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Link
                      href="/auth/signup"
                      className="px-5 py-2.5 rounded-xl font-semibold bg-gradient-to-r from-violet-500 to-fuchsia-500 hover:opacity-90 transition flex items-center gap-2"
                    >
                      <Lock className="w-4 h-4" /> Unlock the full report — free account
                    </Link>
                  </div>
                </div>
              )}
            </div>

            {/* Value strip */}
            <div className="grid md:grid-cols-3 gap-4">
              {[
                { title: "Autopilot fixes", desc: "Schema, internal links & redirects pushed straight to your CMS." },
                { title: "Beat your competitors", desc: "AI analyzes who outranks you and generates the plan to pass them." },
                { title: "Content that ranks", desc: "Briefs, articles and publishing calendar — generated and scheduled." },
              ].map((f) => (
                <div key={f.title} className="bg-white/5 border border-white/10 rounded-xl p-5">
                  <CheckCircle2 className="w-5 h-5 text-lime-400" />
                  <p className="font-semibold mt-2">{f.title}</p>
                  <p className="text-sm text-gray-400 mt-1">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {status === "done" && report && report.critical_count > 0 && (
          <div className="mt-10 flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
            <p>
              <span className="font-semibold">{report.critical_count} critical issues</span> are actively
              costing you rankings. Every week they stay unfixed, competitors pull further ahead.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
