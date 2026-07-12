"use client";

import { useState } from "react";
import { Coins, Loader2, Target, MousePointerClick, Sparkles } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { optimisedKeywords, type BudgetKeywordsResult } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const MODES = [
  { id: "aggressive", label: "Aggressive", hint: "Maximize reach — bid on high-volume head terms" },
  { id: "balanced", label: "Balanced", hint: "Best mix of reach and cost-efficiency" },
  { id: "conservative", label: "Conservative", hint: "Maximize clicks per rupee — cheap long-tail" },
];

const compColor = (c: string) =>
  c === "high" ? "text-rose-300 bg-rose-500/10"
  : c === "low" ? "text-emerald-300 bg-emerald-500/10"
  : "text-amber-300 bg-amber-500/10";

export default function BudgetKeywordsPage() {
  const { apiKey } = useAppStore();
  const [budget, setBudget] = useState(500);
  const [seed, setSeed] = useState("");
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState("balanced");
  const [region, setRegion] = useState("IN");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BudgetKeywordsResult | null>(null);

  async function run() {
    if (!seed.trim()) { toast.error("Enter a seed keyword."); return; }
    if (budget <= 0) { toast.error("Enter a monthly budget."); return; }
    setLoading(true);
    setResult(null);
    try {
      const data = await optimisedKeywords(
        { budget_inr: budget, seed_keyword: seed.trim(), url: url.trim(), mode, region },
        apiKey,
      );
      setResult(data);
      toast.success(`${data.keywords_selected} keywords · ~${data.total_estimated_clicks} clicks/mo`);
    } catch (err: any) {
      toast.error(err?.message || "Could not generate the budget plan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Budget Keywords"
        subtitle="Tell us your monthly budget and a seed — we return the best keyword mix that spend can actually buy, with estimated CPC, clicks, and allocation."
        icon={Coins}
        accent="#FACC15"
      />

      <div className="card p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Monthly budget (₹)</label>
            <input type="number" min={1} value={budget}
              onChange={e => setBudget(Number(e.target.value))}
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-500/50" />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Seed keyword</label>
            <input value={seed} onChange={e => setSeed(e.target.value)} placeholder="e.g. software company"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-500/50" />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Your site (optional)</label>
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="surrvik.com"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-500/50" />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Region</label>
            <input value={region} onChange={e => setRegion(e.target.value.toUpperCase())} placeholder="IN"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-500/50" />
          </div>
        </div>

        <div className="mt-4">
          <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Strategy</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-1">
            {MODES.map(m => (
              <button key={m.id} onClick={() => setMode(m.id)}
                className={cn("text-left p-3 rounded-lg border transition",
                  mode === m.id ? "bg-amber-500/10 border-amber-500/50" : "border-zinc-700 hover:border-zinc-600")}>
                <div className={cn("text-sm font-semibold", mode === m.id ? "text-amber-200" : "text-zinc-300")}>{m.label}</div>
                <div className="text-[11px] text-zinc-500 mt-0.5">{m.hint}</div>
              </button>
            ))}
          </div>
        </div>

        <button onClick={run} disabled={loading}
          className="btn-primary mt-5 flex items-center gap-2 px-6 h-[42px]">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {loading ? "Planning your spend…" : "Build budget plan"}
        </button>
        {loading && <p className="text-xs text-zinc-500 mt-2">Analyzing the market and allocating your budget — ~15–30s.</p>}
      </div>

      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat icon={<Coins className="w-4 h-4" />} label="Monthly budget" value={`₹${result.budget_inr.toLocaleString()}`} />
            <Stat icon={<MousePointerClick className="w-4 h-4" />} label="Est. clicks / mo" value={result.total_estimated_clicks.toLocaleString()} accent />
            <Stat icon={<Target className="w-4 h-4" />} label="Keywords in mix" value={String(result.keywords_selected)} />
            <Stat icon={<Sparkles className="w-4 h-4" />} label="Strategy" value={result.mode} />
          </div>

          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200">Recommended budget mix</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-zinc-500 border-b border-zinc-800">
                    <th className="py-2">Keyword</th>
                    <th className="py-2 text-right">CPC</th>
                    <th className="py-2 text-right">Volume</th>
                    <th className="py-2">Comp.</th>
                    <th className="py-2">Intent</th>
                    <th className="py-2 text-right">Budget</th>
                    <th className="py-2 text-right">Est. clicks</th>
                    <th className="py-2 text-right">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recommended_mix.map((k, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-2 max-w-[280px] truncate text-amber-200 font-medium">{k.keyword}</td>
                      <td className="py-2 text-right text-zinc-300 tabular-nums">₹{k.cpc_inr}</td>
                      <td className="py-2 text-right text-zinc-400 tabular-nums">{k.monthly_searches.toLocaleString()}</td>
                      <td className="py-2"><span className={cn("px-2 py-0.5 rounded-full text-[10px] font-semibold", compColor(k.competition))}>{k.competition}</span></td>
                      <td className="py-2 text-zinc-400">{k.intent}</td>
                      <td className="py-2 text-right text-zinc-300 tabular-nums">₹{k.allocated_budget_inr}</td>
                      <td className="py-2 text-right text-emerald-300 font-semibold tabular-nums">{k.estimated_clicks}</td>
                      <td className="py-2 text-right text-zinc-400 tabular-nums">{k.priority}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-zinc-500 mt-3">{result.notes}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value, accent }: { icon: React.ReactNode; label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-zinc-800/30 rounded-lg p-4 border border-zinc-800">
      <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-wider mb-2">
        <span className="text-zinc-400">{icon}</span>{label}
      </div>
      <div className={cn("text-2xl font-semibold font-serif capitalize", accent ? "text-emerald-400" : "text-zinc-100")}>{value}</div>
    </div>
  );
}
