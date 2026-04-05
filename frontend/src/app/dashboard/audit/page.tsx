"use client";

import { useState } from "react";
import { Loader2, Shield } from "lucide-react";
import { cn, scoreColor, scoreBg } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { technicalAudit } from "@/lib/api";
import { toast } from "sonner";

export default function AuditPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await technicalAudit(url, apiKey);
      setResult(data);
      toast.success("Audit complete!");
    } catch (err: any) {
      toast.error(err.message || "Audit failed");
    } finally {
      setLoading(false);
    }
  }

  const scoreLabel = (v: number | null) => v !== null ? Math.round(v) : "—";

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Shield className="w-6 h-6 text-amber-400" /> Technical SEO Audit
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Real PageSpeed Insights + AI-powered analysis for any URL.
        </p>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <div className="flex-1">
            <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} className="input-field" placeholder="https://example.com" required />
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 px-6">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            {loading ? "Auditing..." : "Run Audit"}
          </button>
        </form>
      </div>

      {result && (
        <div className="space-y-6">
          {/* Scores */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Performance", key: "performance" },
              { label: "SEO", key: "seo" },
              { label: "Accessibility", key: "accessibility" },
              { label: "Best Practices", key: "best_practices" },
            ].map((s) => {
              const val = result.scores?.[s.key];
              return (
                <div key={s.key} className={cn("card p-5 border", val !== null ? scoreBg(val) : "")}>
                  <div className="metric-label">{s.label}</div>
                  <div className={cn("text-3xl font-bold mt-1", val !== null ? scoreColor(val) : "text-zinc-500")}>
                    {scoreLabel(val)}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Core Web Vitals */}
          {result.core_web_vitals && Object.keys(result.core_web_vitals).length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Core Web Vitals</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(result.core_web_vitals).map(([key, val]: [string, any]) => (
                  <div key={key} className="bg-zinc-800/30 rounded-lg p-4">
                    <div className="text-xs text-zinc-500 uppercase">{key}</div>
                    <div className="text-xl font-bold mt-1 text-zinc-200">
                      {key === "CLS" ? val?.toFixed(3) : `${Math.round(val)}ms`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          {result.actions?.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Issues & Recommendations ({result.issues_count})</h3>
              <div className="space-y-2">
                {result.actions.map((a: any, i: number) => (
                  <div key={i} className={cn(
                    "p-3 rounded-lg border text-sm flex items-start gap-3",
                    a.impact === "critical" ? "bg-red-500/5 border-red-500/20" :
                    a.impact === "high" ? "bg-amber-500/5 border-amber-500/20" :
                    "bg-zinc-800/30 border-zinc-700/50"
                  )}>
                    <span className={cn(
                      "badge text-xs flex-shrink-0 mt-0.5",
                      a.impact === "critical" ? "badge-error" : a.impact === "high" ? "badge-warning" : "badge-info"
                    )}>{a.impact}</span>
                    <div>
                      <div className="text-zinc-200">{a.action}</div>
                      {a.details && <div className="text-xs text-zinc-500 mt-1">{a.details}</div>}
                      <div className="text-xs text-zinc-600 mt-1">{a.category} · {a.auto_fixable === "true" ? "Auto-fixable" : "Manual"}</div>
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
