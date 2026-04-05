"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, BarChart3, Loader2, Minus, Plus, RefreshCw, TrendingUp, X } from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function RankTrackerPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [projectId, setProjectId] = useState("");
  const [keywords, setKeywords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newKw, setNewKw] = useState({ keyword: "", region: "IN", locale: "en-US" });
  const [history, setHistory] = useState<Record<string, any[]>>({});
  const [selectedKw, setSelectedKw] = useState<string | null>(null);

  async function loadKeywords() {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/keywords`, { headers: { "X-API-KEY": apiKey } });
      if (res.ok) setKeywords(await res.json());
    } catch {} finally { setLoading(false); }
  }

  async function addKeyword(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await fetch(`${API}/projects/${projectId}/keywords`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify(newKw),
      });
      if (!res.ok) throw new Error(await res.text());
      toast.success("Keyword added!");
      setNewKw({ keyword: "", region: "IN", locale: "en-US" });
      setShowAdd(false);
      loadKeywords();
    } catch (err: any) { toast.error(err.message); }
  }

  async function deleteKeyword(id: string) {
    await fetch(`${API}/keywords/${id}`, { method: "DELETE", headers: { "X-API-KEY": apiKey } });
    loadKeywords();
  }

  async function triggerRankCheck() {
    setChecking(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/rank-check`, { method: "POST", headers: { "X-API-KEY": apiKey } });
      if (res.ok) toast.success("Rank check started! Results will appear shortly.");
    } catch { toast.error("Failed"); }
    finally { setChecking(false); }
  }

  async function loadHistory(kwId: string) {
    setSelectedKw(kwId);
    try {
      const res = await fetch(`${API}/keywords/${kwId}/rank-history?limit=30`, { headers: { "X-API-KEY": apiKey } });
      if (res.ok) {
        const data = await res.json();
        setHistory(prev => ({ ...prev, [kwId]: data }));
      }
    } catch {}
  }

  const posChange = (curr: number | null, prev: number | null) => {
    if (!curr || !prev) return null;
    return prev - curr; // positive = improved
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><BarChart3 className="w-6 h-6 text-teal-400" /> Rank Tracker</h1>
          <p className="text-sm text-zinc-400 mt-1">Monitor keyword positions daily with SERP feature detection.</p>
        </div>
      </div>

      {/* Project Selector */}
      <div className="card p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="label">Project ID</label>
            <input type="text" value={projectId} onChange={e => setProjectId(e.target.value)} className="input-field" placeholder="Paste project ID from Projects page" />
          </div>
          <div className="flex items-end gap-2">
            <button onClick={loadKeywords} disabled={!projectId || loading} className="btn-primary flex items-center gap-2">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />} Load
            </button>
            {keywords.length > 0 && (
              <button onClick={triggerRankCheck} disabled={checking} className="btn-secondary flex items-center gap-2">
                <RefreshCw className={cn("w-4 h-4", checking && "animate-spin")} /> Check Now
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Add Keyword */}
      {projectId && (
        <div className="mb-6">
          {showAdd ? (
            <div className="card p-4 animate-fade-in">
              <form onSubmit={addKeyword} className="flex items-end gap-3">
                <div className="flex-1">
                  <label className="label">Keyword</label>
                  <input type="text" value={newKw.keyword} onChange={e => setNewKw({ ...newKw, keyword: e.target.value })} className="input-field" placeholder="e.g. best seo tools india" required />
                </div>
                <div className="w-32">
                  <label className="label">Region</label>
                  <select value={newKw.region} onChange={e => setNewKw({ ...newKw, region: e.target.value })} className="input-field">
                    <option value="IN">India</option><option value="US">US</option><option value="GB">UK</option>
                  </select>
                </div>
                <button type="submit" className="btn-primary">Add</button>
                <button type="button" onClick={() => setShowAdd(false)} className="btn-ghost p-2"><X className="w-4 h-4" /></button>
              </form>
            </div>
          ) : (
            <button onClick={() => setShowAdd(true)} className="btn-ghost text-sm flex items-center gap-1.5"><Plus className="w-3.5 h-3.5" /> Add keyword</button>
          )}
        </div>
      )}

      {/* Keywords Table */}
      {keywords.length > 0 && (
        <div className="card overflow-hidden mb-6">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/30">
                <th className="text-left px-5 py-3 text-zinc-500 text-xs uppercase">Keyword</th>
                <th className="text-center px-4 py-3 text-zinc-500 text-xs uppercase">Position</th>
                <th className="text-center px-4 py-3 text-zinc-500 text-xs uppercase">Change</th>
                <th className="text-center px-4 py-3 text-zinc-500 text-xs uppercase">Intent</th>
                <th className="text-center px-4 py-3 text-zinc-500 text-xs uppercase">Region</th>
                <th className="text-right px-5 py-3 text-zinc-500 text-xs uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keywords.map((kw) => {
                const change = posChange(kw.latest_position, kw.previous_position);
                return (
                  <tr key={kw.id} className="border-b border-zinc-800/30 hover:bg-zinc-800/20 cursor-pointer" onClick={() => loadHistory(kw.id)}>
                    <td className="px-5 py-3 font-medium text-zinc-200">{kw.keyword}</td>
                    <td className="px-4 py-3 text-center">
                      {kw.latest_position ? (
                        <span className={cn("font-bold", kw.latest_position <= 3 ? "text-emerald-400" : kw.latest_position <= 10 ? "text-amber-400" : "text-zinc-400")}>
                          #{kw.latest_position}
                        </span>
                      ) : <span className="text-zinc-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {change !== null ? (
                        <span className={cn("flex items-center justify-center gap-0.5 text-xs font-medium", change > 0 ? "text-emerald-400" : change < 0 ? "text-red-400" : "text-zinc-500")}>
                          {change > 0 ? <ArrowUp className="w-3 h-3" /> : change < 0 ? <ArrowDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                          {Math.abs(change)}
                        </span>
                      ) : <span className="text-zinc-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {kw.intent ? <span className="badge badge-info text-xs">{kw.intent}</span> : <span className="text-zinc-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center text-zinc-400 text-xs">{kw.target_region}</td>
                    <td className="px-5 py-3 text-right">
                      <button onClick={(e) => { e.stopPropagation(); deleteKeyword(kw.id); }} className="btn-ghost p-1 text-zinc-500 hover:text-red-400">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Rank History Chart (simple ASCII/visual) */}
      {selectedKw && history[selectedKw] && (
        <div className="card p-6 animate-fade-in">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-400" />
            Position History — {keywords.find(k => k.id === selectedKw)?.keyword}
          </h3>
          {history[selectedKw].length === 0 ? (
            <p className="text-sm text-zinc-500">No rank history yet. Run a rank check to start tracking.</p>
          ) : (
            <div className="space-y-1">
              {history[selectedKw].slice(0, 30).reverse().map((h: any, i: number) => {
                const pos = h.position;
                const barWidth = pos ? Math.max(5, Math.min(100, (50 - pos) * 2 + 20)) : 0;
                const date = new Date(h.checked_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" });
                return (
                  <div key={i} className="flex items-center gap-3 text-xs">
                    <span className="text-zinc-500 w-16 text-right">{date}</span>
                    <div className="flex-1 h-5 bg-zinc-800/30 rounded overflow-hidden relative">
                      {pos && (
                        <div
                          className={cn("h-full rounded transition-all", pos <= 3 ? "bg-emerald-500/30" : pos <= 10 ? "bg-brand-500/30" : "bg-amber-500/30")}
                          style={{ width: `${barWidth}%` }}
                        />
                      )}
                    </div>
                    <span className={cn("w-8 text-right font-mono font-medium", pos ? (pos <= 3 ? "text-emerald-400" : pos <= 10 ? "text-brand-400" : "text-zinc-400") : "text-zinc-600")}>
                      {pos ? `#${pos}` : "—"}
                    </span>
                    {h.serp_features?.length > 0 && (
                      <div className="flex gap-1">
                        {h.serp_features.map((f: string) => (
                          <span key={f} className="badge bg-zinc-700/50 text-zinc-400 border-0 text-[10px]">{f.replace("_", " ")}</span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
