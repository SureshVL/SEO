"use client";

import { useState, useEffect } from "react";
import { Loader2, Shield, Sparkles } from "lucide-react";
import { cn, scoreColor, scoreBg } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { technicalAudit } from "@/lib/api";
import { toast } from "sonner";

export default function AuditPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Auto-fill from business profile
  useEffect(() => {
    if (businessProfile?.websiteUrl && !url) setUrl(businessProfile.websiteUrl);
  }, [businessProfile]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await technicalAudit(url, apiKey);
      setResult(data);
      toast.success("Audit complete!");
    } catch (err: any) {
      toast.error(err.message || "Audit failed");
    } finally { setLoading(false); }
  }

  const scoreLabel = (v: number | null) => v !== null ? Math.round(v) : "—";

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-amber-400" /> Technical SEO Audit
        </h1>
        {businessProfile?.websiteUrl && (
          <div className="flex items-center gap-1.5 mt-2 text-xs text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded-lg px-3 py-1.5 w-fit">
            <Sparkles className="w-3.5 h-3.5" /> Auto-filled from your project
          </div>
        )}
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <div className="flex-1">
            <input type="url" value={url} onChange={e => setUrl(e.target.value)}
              className="input-field" placeholder="https://example.com" required />
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 px-6">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            {loading ? "Auditing..." : "Run Audit"}
          </button>
        </form>
      </div>

      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Performance", key: "performance" },
              { label: "Accessibility", key: "accessibility" },
              { label: "Best Practices", key: "best_practices" },
              { label: "SEO", key: "seo" },
            ].map(({ label, key }) => {
              const val = result.lighthouse_scores?.[key] ?? result.scores?.[key] ?? null;
              return (
                <div key={key} className={cn("card p-4 text-center border", val !== null ? scoreBg(val) : "")}>
                  <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">{label}</div>
                  <div className={cn("text-3xl font-bold font-serif", val !== null ? scoreColor(val) : "text-zinc-400")}>
                    {scoreLabel(val)}
                  </div>
                </div>
              );
            })}
          </div>

          {result.issues?.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4 text-amber-400">Issues Found</h3>
              <div className="space-y-2">
                {result.issues.slice(0, 10).map((issue: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-zinc-800/30 rounded-lg text-sm">
                    <span className={cn("text-[10px] font-bold uppercase mt-0.5 shrink-0",
                      issue.severity === "critical" ? "text-red-400" :
                      issue.severity === "high" ? "text-amber-400" : "text-blue-400")}>
                      {issue.severity}
                    </span>
                    <span className="text-zinc-300">{issue.description || issue.message || JSON.stringify(issue)}</span>
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
