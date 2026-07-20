"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ArrowRight, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

const verticalTitles: Record<string, string> = {
  saas: "SaaS", ecommerce: "Ecommerce", healthcare: "Healthcare",
  fintech: "Fintech", b2b: "B2B", legal: "Legal", realestate: "Real Estate",
  local: "Local Services", accounting: "Accounting", consulting: "Consulting",
  education: "Education", insurance: "Insurance", nonprofit: "Nonprofit",
};

interface ReportSummary {
  id: string;
  month: string;
  key_findings: Array<{ title: string; description: string; metric: string }>;
  citations_analyzed: number;
  top_movers: Array<{ rank: number; domain: string; citations: number; change: string }>;
}

interface BenchmarkData {
  vertical: string;
  reports: ReportSummary[];
  trend: string;
}

export default function VerticalResearchPage() {
  const params = useParams<{ vertical: string }>();
  const vertical = (params?.vertical || "").toLowerCase();
  const title = verticalTitles[vertical] || vertical.charAt(0).toUpperCase() + vertical.slice(1);

  const [data, setData] = useState<BenchmarkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [subEmail, setSubEmail] = useState("");
  const [subState, setSubState] = useState<"idle" | "done" | "error">("idle");

  useEffect(() => {
    if (!vertical) return;
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${base}/api/research/benchmarks/${vertical}`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [vertical]);

  async function subscribe(e: React.FormEvent) {
    e.preventDefault();
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const qs = new URLSearchParams({ email: subEmail, vertical });
      const res = await fetch(`${base}/email/subscribe?${qs}`, { method: "POST" });
      setSubState(res.ok ? "done" : "error");
    } catch {
      setSubState("error");
    }
  }

  const latest = data?.reports?.[0];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-16">
        <Link href="/research" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-8">
          <ArrowLeft className="w-4 h-4" /> All Research
        </Link>

        <p className="text-sm text-violet-600 font-semibold uppercase tracking-wider mb-2">
          Industry Research
        </p>
        <h1 className="text-4xl font-bold text-slate-900 mb-8">
          {title} — AI Search Report
        </h1>

        {loading ? (
          <div className="text-center py-16">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-violet-600"></div>
          </div>
        ) : latest ? (
          <div className="space-y-8">
            <p className="text-slate-600">
              <span className="font-semibold">{latest.month}</span> ·{" "}
              {latest.citations_analyzed.toLocaleString()} AI citations analyzed
            </p>

            <div className="space-y-4">
              {latest.key_findings.map((f, i) => (
                <div key={i} className="bg-white p-5 rounded-lg border border-slate-200">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-bold text-slate-900">{f.title}</h3>
                      <p className="text-sm text-slate-600 mt-1">{f.description}</p>
                    </div>
                    <span className="text-xl font-bold text-violet-600 whitespace-nowrap">{f.metric}</span>
                  </div>
                </div>
              ))}
            </div>

            {latest.top_movers?.length > 0 && (
              <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-500" />
                  <h3 className="font-semibold text-slate-900 text-sm">Top cited domains</h3>
                </div>
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-slate-100">
                    {latest.top_movers.slice(0, 10).map(m => (
                      <tr key={m.rank}>
                        <td className="px-5 py-2.5 font-semibold text-slate-900 w-12">#{m.rank}</td>
                        <td className="px-5 py-2.5 text-slate-700">{m.domain}</td>
                        <td className="px-5 py-2.5 text-right text-slate-900">{m.citations.toLocaleString()}</td>
                        <td className="px-5 py-2.5 text-right text-emerald-600 font-semibold">{m.change}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white p-10 rounded-lg border border-slate-200 text-center">
            <h2 className="text-xl font-bold text-slate-900 mb-3">
              The first {title} report is in production
            </h2>
            <p className="text-slate-600 max-w-md mx-auto">
              We&apos;re collecting AI citation data across ChatGPT, Perplexity, Gemini, and
              Google AI Overviews for the {title.toLowerCase()} industry. Subscribe below and
              you&apos;ll get it the day it publishes.
            </p>
          </div>
        )}

        {/* Subscribe */}
        <div className="mt-12 p-8 bg-slate-900 rounded-lg text-center">
          <h3 className="text-xl font-bold text-white mb-2">
            Get the {title} report by email
          </h3>
          <p className="text-slate-300 text-sm mb-6">Monthly. No spam. Unsubscribe anytime.</p>
          {subState === "done" ? (
            <p className="text-emerald-300 font-semibold">✓ Subscribed — see you in your inbox.</p>
          ) : (
            <form onSubmit={subscribe} className="flex gap-3 justify-center max-w-md mx-auto">
              <input
                type="email"
                value={subEmail}
                onChange={e => setSubEmail(e.target.value)}
                placeholder="your@email.com"
                required
                className="flex-1 px-4 py-3 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
              <button type="submit" className="bg-violet-600 text-white font-semibold px-6 py-3 rounded-lg hover:bg-violet-700 transition">
                Subscribe
              </button>
            </form>
          )}
          {subState === "error" && (
            <p className="text-rose-300 text-sm mt-3">Something went wrong — please try again.</p>
          )}
        </div>
      </div>
    </div>
  );
}
