"use client";

import Link from "next/link";
import { ArrowRight, TrendingUp, ArrowUpRight, ArrowDownLeft } from "lucide-react";
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

interface TopMover {
  rank: number;
  domain: string;
  citations: number;
  change: string;
}

interface BenchmarkData {
  vertical: string;
  reports: Array<{
    citations_analyzed: number;
    top_movers: TopMover[];
  }>;
  trend: string;
  last_updated: string;
}

export default function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<Record<string, BenchmarkData>>({});
  const [loading, setLoading] = useState(true);
  const [selectedVertical, setSelectedVertical] = useState<string | null>(null);

  useEffect(() => {
    const fetchBenchmarks = async () => {
      try {
        const results: Record<string, BenchmarkData> = {};
        for (const vertical of verticals) {
          const res = await fetch(`/api/research/benchmarks/${vertical}`);
          if (res.ok) {
            const data = await res.json();
            results[vertical] = data;
          }
        }
        setBenchmarks(results);
        setSelectedVertical(verticals[0]);
      } catch (error) {
        console.error("Error fetching benchmarks:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchBenchmarks();
  }, []);

  const selected = selectedVertical ? benchmarks[selectedVertical] : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            OR OMNI-RANK
          </Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-indigo-50 via-purple-50 to-violet-50 py-24">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            AI Search Benchmarks
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            Real-time AI citation rankings for every industry. See who's winning in ChatGPT, Perplexity, Gemini, and Google AI Overviews.
          </p>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Vertical selector */}
          <div>
            <h3 className="font-semibold text-slate-900 mb-4">Industries</h3>
            <div className="space-y-2">
              {verticals.map((vertical) => (
                <button
                  key={vertical}
                  onClick={() => setSelectedVertical(vertical)}
                  className={`w-full text-left px-4 py-3 rounded-lg font-medium transition ${
                    selectedVertical === vertical
                      ? "bg-violet-600 text-white"
                      : "bg-white text-slate-900 border border-slate-200 hover:border-violet-300"
                  }`}
                >
                  {verticalTitles[vertical]}
                </button>
              ))}
            </div>
          </div>

          {/* Benchmark data */}
          <div className="lg:col-span-3">
            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-violet-600"></div>
              </div>
            ) : selected && selected.reports.length > 0 ? (
              <div className="space-y-6">
                {/* Summary */}
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-white p-6 rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-600 mb-2">Citations Analyzed</p>
                    <p className="text-3xl font-bold text-slate-900">
                      {(selected.reports[0].citations_analyzed / 1000).toFixed(1)}K
                    </p>
                  </div>
                  <div className="bg-white p-6 rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-600 mb-2">Trend</p>
                    <div className="flex items-center gap-2">
                      {selected.trend === "up" ? (
                        <ArrowUpRight className="w-6 h-6 text-emerald-500" />
                      ) : selected.trend === "down" ? (
                        <ArrowDownLeft className="w-6 h-6 text-red-500" />
                      ) : (
                        <TrendingUp className="w-6 h-6 text-slate-400" />
                      )}
                      <span className="text-lg font-semibold text-slate-900">
                        {selected.trend === "up" ? "Rising" : selected.trend === "down" ? "Declining" : "Stable"}
                      </span>
                    </div>
                  </div>
                  <div className="bg-white p-6 rounded-lg border border-slate-200">
                    <p className="text-sm text-slate-600 mb-2">Updated</p>
                    <p className="text-sm text-slate-900">
                      {selected.last_updated ? new Date(selected.last_updated).toLocaleDateString() : "Recently"}
                    </p>
                  </div>
                </div>

                {/* Top movers table */}
                <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
                    <h3 className="font-semibold text-slate-900">Top Ranking Domains</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Rank</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Domain</th>
                          <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Citations</th>
                          <th className="px-6 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Change</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {selected.reports[0].top_movers.slice(0, 10).map((mover) => (
                          <tr key={mover.rank} className="hover:bg-slate-50">
                            <td className="px-6 py-4 text-sm font-semibold text-slate-900">#{mover.rank}</td>
                            <td className="px-6 py-4 text-sm text-slate-900">{mover.domain}</td>
                            <td className="px-6 py-4 text-sm text-right text-slate-900 font-semibold">{mover.citations.toLocaleString()}</td>
                            <td className="px-6 py-4 text-sm text-right">
                              <span className={mover.change.startsWith("+") ? "text-emerald-600 font-semibold" : "text-slate-600"}>
                                {mover.change}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="text-center pt-6">
                  <p className="text-slate-600 mb-4">Want to see your domain in this benchmark?</p>
                  <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-violet-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-violet-700 transition">
                    Start Tracking AI Visibility <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="bg-white p-12 rounded-lg border border-slate-200 text-center">
                <p className="text-slate-600">No benchmark data available yet. Check back soon!</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
