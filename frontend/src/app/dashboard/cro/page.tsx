"use client";

import { useState } from "react";
import { MousePointerClick, Loader2, Sparkles, Zap } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { createCroJob, getJob, type CroAuditResult } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";
import { cn, scoreColor } from "@/lib/utils";

const sevColor = (s: string) =>
  s === "high" ? "text-rose-300 bg-rose-500/10"
  : s === "low" ? "text-emerald-300 bg-emerald-500/10"
  : "text-amber-300 bg-amber-500/10";

export default function CroPage() {
  const { apiKey } = useAppStore();
  const [url, setUrl] = useState("");
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusNote, setStatusNote] = useState("");
  const [result, setResult] = useState<CroAuditResult | null>(null);

  async function run() {
    if (!url.trim()) { toast.error("Enter a landing-page URL."); return; }
    setLoading(true);
    setResult(null);
    setStatusNote("Queuing audit…");
    try {
      const { job_id } = await createCroJob({ url: url.trim(), goal: goal.trim() }, apiKey);
      setStatusNote("Analyzing the page — first run takes about a minute. Re-audits of the same page are instant.");
      const started = Date.now();
      while (Date.now() - started < 240_000) {
        await new Promise((r) => setTimeout(r, 3000));
        const job = await getJob(job_id, apiKey);
        if (job.status === "completed") {
          const data = job.result as CroAuditResult;
          setResult(data);
          toast.success(`CRO score ${data.score ?? "—"} · ${data.issues?.length ?? 0} findings`);
          return;
        }
        if (job.status === "failed") {
          toast.error(job.error || "CRO audit failed");
          return;
        }
      }
      toast.error("The audit is taking unusually long — check the Jobs list or try again.");
    } catch (err: any) {
      toast.error(err?.message || "CRO audit failed");
    } finally {
      setLoading(false);
      setStatusNote("");
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="CRO Audit"
        subtitle="Audit any landing page for conversion issues — CTA clarity, trust signals, copy, forms and social proof — with concrete fixes."
        icon={MousePointerClick}
        accent="#F43F5E"
      />

      <div className="card p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Landing-page URL</span>
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://surrvik.com/"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-rose-500/50" />
          </label>
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Conversion goal (optional)</span>
            <input value={goal} onChange={e => setGoal(e.target.value)} placeholder="book a demo"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-rose-500/50" />
          </label>
        </div>
        <button onClick={run} disabled={loading} className="btn-primary mt-5 flex items-center gap-2 px-6 h-[42px]">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {loading ? "Auditing page…" : "Run CRO audit"}
        </button>
        {statusNote && <p className="text-xs text-zinc-500 mt-3">{statusNote}</p>}
      </div>

      {result && (
        <div className="space-y-6">
          <div className="card p-6 flex items-center gap-6">
            <div className="text-center">
              <div className={cn("text-5xl font-bold font-serif", scoreColor(result.score ?? 0))}>{result.score ?? "—"}</div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-1">CRO score</div>
            </div>
            <p className="text-sm text-zinc-300 flex-1">{result.summary}</p>
          </div>

          {result.quick_wins?.length > 0 && (
            <div className="card p-6 border border-rose-500/20 bg-rose-500/5">
              <h3 className="font-semibold mb-3 text-rose-200 flex items-center gap-2"><Zap className="w-4 h-4" /> Quick wins</h3>
              <ul className="space-y-2">
                {result.quick_wins.map((w, i) => (
                  <li key={i} className="text-sm text-zinc-300 flex gap-2"><span className="text-rose-400">→</span>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="card p-6">
            <h3 className="font-semibold mb-4 text-zinc-200">Findings ({result.issues.length})</h3>
            <div className="space-y-3">
              {result.issues.map((iss, i) => (
                <div key={i} className="border border-zinc-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-semibold", sevColor(iss.severity))}>{iss.severity}</span>
                    <span className="text-xs font-semibold text-zinc-400">{iss.category}</span>
                  </div>
                  <p className="text-sm text-zinc-200">{iss.finding}</p>
                  <p className="text-xs text-zinc-400 mt-1"><span className="text-emerald-400 font-semibold">Fix:</span> {iss.fix}</p>
                </div>
              ))}
            </div>
          </div>

          {result.ctas_detected?.length > 0 && (
            <div className="card p-6">
              <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold mb-2">CTAs detected on page</div>
              <div className="flex flex-wrap gap-2">
                {result.ctas_detected.map((c, i) => (
                  <span key={i} className="text-xs bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1 text-zinc-300">{c}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
