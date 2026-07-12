"use client";

import Link from "next/link";
import { ArrowRight, Download, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

const verticals = [
  "saas", "ecommerce", "healthcare", "fintech", "b2b", "legal",
  "realestate", "local", "accounting", "consulting", "education",
  "insurance", "nonprofit"
];

const verticalTitles: Record<string, string> = {
  "saas": "SaaS",
  "ecommerce": "Ecommerce",
  "healthcare": "Healthcare",
  "fintech": "Fintech",
  "b2b": "B2B",
  "legal": "Legal",
  "realestate": "Real Estate",
  "local": "Local Services",
  "accounting": "Accounting",
  "consulting": "Consulting",
  "education": "Education",
  "insurance": "Insurance",
  "nonprofit": "Nonprofit",
};

interface ResearchReport {
  id: string;
  vertical: string;
  month: string;
  status: string;
  created_at: string;
  key_findings: Array<{
    title: string;
    description: string;
    metric: string;
  }>;
}

export default function ResearchPage() {
  const [reports, setReports] = useState<Record<string, ResearchReport[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const res = await fetch("/api/research/latest");
        if (res.ok) {
          const data = await res.json();
          setReports(data.reports || {});
        }
      } catch (error) {
        console.error("Error fetching reports:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            OR OMNI-RANK
          </Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-violet-50 via-blue-50 to-indigo-50 py-24">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            AI Search Research Reports
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto mb-8">
            Monthly AI visibility analysis across ChatGPT, Perplexity, Gemini, and Google AI Overviews.
            See how your industry is competing for AI citations.
          </p>
          <div className="flex gap-4 justify-center">
            <button className="bg-violet-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-violet-700 transition flex items-center gap-2">
              <Download className="w-4 h-4" /> Download Latest Report
            </button>
            <Link href="/benchmarks" className="border border-slate-300 text-slate-900 font-semibold px-8 py-3 rounded-lg hover:bg-slate-100 transition">
              View Benchmarks
            </Link>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-slate-900 mb-12">Latest Reports by Industry</h2>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-violet-600"></div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-8">
            {verticals.map((vertical) => {
              const verticalReports = reports[vertical] || [];
              const latestReport = verticalReports[0];

              return (
                <Link
                  key={vertical}
                  href={`/research/${vertical}`}
                  className="group"
                >
                  <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-violet-300 hover:shadow-lg transition h-full">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <p className="text-xs text-violet-600 font-semibold uppercase tracking-wider mb-1">
                          Industry Report
                        </p>
                        <h3 className="text-xl font-bold text-slate-900 group-hover:text-violet-600 transition">
                          {verticalTitles[vertical] || vertical.title()}
                        </h3>
                      </div>
                      <TrendingUp className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                    </div>

                    {latestReport ? (
                      <>
                        <p className="text-sm text-slate-600 mb-4">
                          <span className="font-semibold">{latestReport.month}</span> Report
                        </p>
                        <div className="space-y-3 mb-6">
                          {latestReport.key_findings.slice(0, 2).map((finding, i) => (
                            <div key={i} className="p-3 bg-slate-50 rounded border border-slate-200">
                              <p className="text-sm font-semibold text-slate-900">{finding.title}</p>
                              <p className="text-xs text-slate-600 mt-1">{finding.metric}</p>
                            </div>
                          ))}
                        </div>
                        <button className="text-sm font-semibold text-violet-600 hover:text-violet-700 flex items-center gap-1">
                          View Full Report <ArrowRight className="w-3 h-3" />
                        </button>
                      </>
                    ) : (
                      <p className="text-slate-600 text-sm">Report coming soon...</p>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      <section className="bg-slate-900 text-white py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-6">Get Research Delivered Monthly</h2>
          <p className="text-lg text-slate-300 mb-8">
            Subscribe to our research reports and get AI visibility data before your competitors.
          </p>
          <form className="flex gap-3 justify-center max-w-md mx-auto mb-6">
            <input
              type="email"
              placeholder="your@email.com"
              className="flex-1 px-4 py-3 rounded-lg text-slate-900 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
              required
            />
            <button
              type="submit"
              className="bg-violet-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-violet-700 transition"
            >
              Subscribe
            </button>
          </form>
          <p className="text-sm text-slate-400">
            No spam. Monthly research reports only. Unsubscribe anytime.
          </p>
        </div>
      </section>
    </div>
  );
}
