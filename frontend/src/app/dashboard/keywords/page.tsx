"use client";

import { useState, useEffect } from "react";
import { Globe2, Loader2, MapPin, Search, Sparkles, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { keywordResearch } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

export default function KeywordsPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [seed, setSeed] = useState("");
  const [domain, setDomain] = useState("");
  const [region, setRegion] = useState("IN");
  const [industry, setIndustry] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Auto-fill from business profile
  useEffect(() => {
    if (businessProfile) {
      if (!domain && businessProfile.websiteUrl) {
        try { setDomain(new URL(businessProfile.websiteUrl).hostname); } catch {}
      }
      if (!seed && businessProfile.keywords.length > 0) setSeed(businessProfile.keywords[0]);
      if (!industry && businessProfile.businessType) setIndustry(businessProfile.businessTypeLabel);
    }
  }, [businessProfile]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await keywordResearch({
        seed_keyword: seed,
        domain,
        region,
        industry: industry || businessProfile?.businessTypeLabel || "",
        city: businessProfile?.cityCode || "",
      }, apiKey);
      setResult(data);
      toast.success(`Found ${(data as any).opportunities?.length || 0} keyword opportunities`);
    } catch (err: any) {
      toast.error(err.message || "Failed");
    } finally { setLoading(false); }
  }

  const intentColors: Record<string, string> = {
    informational: "badge-info",
    transactional: "badge-success",
    commercial: "badge-warning",
    navigational: "bg-zinc-700/50 text-zinc-300 border border-zinc-600/30",
  };

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="AI Keyword Research"
        subtitle="Discover high-intent keyword opportunities with volume, difficulty, and priority scoring."
        icon={Search}
        accent="#22D3EE"
        chips={businessProfile && (
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium rounded-full px-3 py-1"
            style={{ background: "rgba(34,211,238,0.12)", color: "#67E8F9", border: "1px solid rgba(34,211,238,0.3)" }}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {businessProfile.city ? `${businessProfile.city} · ` : ""}{businessProfile.businessTypeLabel}
          </span>
        )}
      />

      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Seed Keyword</label>
              <input type="text" value={seed} onChange={e => setSeed(e.target.value)}
                className="input-field" placeholder="e.g. seo tools" required />
            </div>
            <div>
              <label className="label">Your Domain</label>
              <input type="text" value={domain} onChange={e => setDomain(e.target.value)}
                className="input-field" placeholder="e.g. yoursite.com" required />
            </div>
            <div>
              <label className="label">Industry / Niche</label>
              <input type="text" value={industry} onChange={e => setIndustry(e.target.value)}
                className="input-field" placeholder="e.g. SaaS, restaurant" />
            </div>
            <div>
              <label className="label">Region</label>
              <Select
                icon={Globe2}
                accent="#22D3EE"
                widthClass="w-full"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                options={[
                  { value: "IN", label: "India" },
                  { value: "US", label: "United States" },
                  { value: "GB", label: "United Kingdom" },
                ]}
              />
            </div>
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 px-6">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Researching…" : "Find Keywords"}
          </button>
        </form>
      </div>

      {/* Saved keywords quick-fill */}
      {businessProfile && businessProfile.keywords.length > 0 && !result && (
        <div className="card p-4 mb-6">
          <p className="text-xs text-zinc-500 mb-2 font-medium uppercase tracking-wider">Your project keywords</p>
          <div className="flex flex-wrap gap-2">
            {businessProfile.keywords.map(kw => (
              <button key={kw} onClick={() => setSeed(kw)}
                className="text-xs bg-zinc-800/60 border border-zinc-700/40 text-zinc-300 rounded-full px-3 py-1.5 hover:bg-teal-600/20 hover:border-teal-500/30 hover:text-teal-300 transition-all">
                {kw}
              </button>
            ))}
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-teal-400" />
              {result.opportunities?.length || 0} Keyword Opportunities
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-zinc-800">
                    <th className="pb-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Keyword</th>
                    <th className="pb-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Volume</th>
                    <th className="pb-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Difficulty</th>
                    <th className="pb-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Intent</th>
                    <th className="pb-3 text-xs text-zinc-500 font-medium uppercase tracking-wider">Priority</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                  {(result.opportunities || []).map((opp: any, i: number) => (
                    <tr key={i} className="hover:bg-zinc-800/20 transition-colors">
                      <td className="py-3 font-medium">{opp.keyword}</td>
                      <td className="py-3 text-zinc-400">{opp.search_volume_est}</td>
                      <td className="py-3 text-zinc-400">{opp.difficulty_est}</td>
                      <td className="py-3">
                        <span className={cn("badge", intentColors[opp.intent] || "bg-zinc-700/50 text-zinc-300 border border-zinc-600/30")}>
                          {opp.intent}
                        </span>
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                            <div className="h-full rounded-full bg-teal-500 transition-all" style={{ width: `${opp.priority_score}%` }} />
                          </div>
                          <span className="text-zinc-400 text-xs">{Math.round(opp.priority_score)}</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
