"use client";

import { useState } from "react";
import { Loader2, Search, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { keywordResearch } from "@/lib/api";
import { toast } from "sonner";

export default function KeywordsPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [seed, setSeed] = useState("");
  const [domain, setDomain] = useState("");
  const [region, setRegion] = useState("IN");
  const [industry, setIndustry] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await keywordResearch({ seed_keyword: seed, domain, region, industry }, apiKey);
      setResult(data);
      toast.success(`Found ${(data as any).opportunities?.length || 0} keyword opportunities`);
    } catch (err: any) {
      toast.error(err.message || "Failed");
    } finally {
      setLoading(false);
    }
  }

  const intentColors: Record<string, string> = {
    informational: "badge-info",
    transactional: "badge-success",
    commercial: "badge-warning",
    navigational: "bg-zinc-700/50 text-zinc-300 border border-zinc-600/30",
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Search className="w-6 h-6 text-teal-400" /> AI Keyword Research
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Enter a seed keyword and Claude will generate opportunities, clusters, and a content plan.
        </p>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Seed Keyword</label>
              <input type="text" value={seed} onChange={(e) => setSeed(e.target.value)} className="input-field" placeholder="e.g. seo tools" required />
            </div>
            <div>
              <label className="label">Your Domain</label>
              <input type="text" value={domain} onChange={(e) => setDomain(e.target.value)} className="input-field" placeholder="e.g. yoursite.com" required />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Region</label>
              <select value={region} onChange={(e) => setRegion(e.target.value)} className="input-field">
                <option value="IN">India</option>
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
              </select>
            </div>
            <div>
              <label className="label">Industry (optional)</label>
              <input type="text" value={industry} onChange={(e) => setIndustry(e.target.value)} className="input-field" placeholder="e.g. SaaS, ecommerce" />
            </div>
            <div className="flex items-end">
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {loading ? "Researching..." : "Find Keywords"}
              </button>
            </div>
          </div>
        </form>
      </div>

      {result && (
        <div className="space-y-6">
          {/* Opportunities Table */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-zinc-800">
              <h3 className="font-semibold">Keyword Opportunities ({result.opportunities?.length || 0})</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-900/30">
                    <th className="text-left px-5 py-2.5 text-zinc-500 text-xs uppercase">Keyword</th>
                    <th className="text-center px-4 py-2.5 text-zinc-500 text-xs uppercase">Volume</th>
                    <th className="text-center px-4 py-2.5 text-zinc-500 text-xs uppercase">Difficulty</th>
                    <th className="text-center px-4 py-2.5 text-zinc-500 text-xs uppercase">Intent</th>
                    <th className="text-center px-4 py-2.5 text-zinc-500 text-xs uppercase">Type</th>
                    <th className="text-right px-5 py-2.5 text-zinc-500 text-xs uppercase">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {result.opportunities?.map((opp: any, i: number) => (
                    <tr key={i} className="border-b border-zinc-800/30 hover:bg-zinc-800/20">
                      <td className="px-5 py-2.5 font-medium text-zinc-200">{opp.keyword}</td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={cn("badge text-xs", opp.volume === "high" ? "badge-success" : opp.volume === "medium" ? "badge-warning" : "badge-info")}>{opp.volume}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={cn("badge text-xs", opp.difficulty === "easy" ? "badge-success" : opp.difficulty === "hard" ? "badge-error" : "badge-warning")}>{opp.difficulty}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={cn("badge text-xs", intentColors[opp.intent] || "badge-info")}>{opp.intent}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center text-zinc-400 text-xs">{opp.content_type}</td>
                      <td className="px-5 py-2.5 text-right font-mono text-xs text-zinc-300">{Math.round(opp.priority)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Clusters */}
          {result.clusters && Object.keys(result.clusters).length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Topic Clusters</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(result.clusters).map(([name, keywords]: [string, any]) => (
                  <div key={name} className="bg-zinc-800/30 rounded-lg p-4 border border-zinc-700/30">
                    <h4 className="text-sm font-medium text-brand-400 mb-2">{name}</h4>
                    <div className="flex flex-wrap gap-1">
                      {keywords.map((kw: string) => (
                        <span key={kw} className="text-xs bg-zinc-700/50 text-zinc-300 px-2 py-0.5 rounded">{kw}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Content Plan */}
          {result.content_plan?.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-emerald-400" /> Content Plan</h3>
              <div className="space-y-3">
                {result.content_plan.map((item: any, i: number) => (
                  <div key={i} className="flex items-start gap-4 p-3 bg-zinc-800/20 rounded-lg">
                    <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center text-brand-400 font-bold text-sm flex-shrink-0">
                      {item.order || i + 1}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-zinc-200">{item.title}</div>
                      <div className="text-xs text-zinc-500 mt-0.5">{item.content_type} · {item.keyword}</div>
                      {item.rationale && <div className="text-xs text-zinc-400 mt-1">{item.rationale}</div>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
