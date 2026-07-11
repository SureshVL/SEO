"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ArrowDown, ArrowUp, BarChart3, FolderOpen, Loader2, Minus,
  Plus, RefreshCw, Search, Sparkles, TrendingUp, Trash2, X,
} from "lucide-react";
import { cn, scoreColor } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  listProjects, listProjectKeywords, addKeyword,
  deleteKeyword, getKeywordHistory, triggerRankCheck,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

// Tiny sparkline component
function Sparkline({ data }: { data: number[] }) {
  if (data.length < 2) return <span className="text-xs text-zinc-600">—</span>;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const W = 80, H = 28, pad = 2;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (W - pad * 2);
    // invert: lower rank = higher on chart
    const y = pad + ((v - min) / range) * (H - pad * 2);
    return `${x},${y}`;
  });
  const trend = data[data.length - 1] - data[0]; // positive = rank went up (worse)
  const color = trend < 0 ? "#1D9E75" : trend > 0 ? "#E24B4A" : "#888";
  return (
    <svg width={W} height={H} className="overflow-visible">
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle
        cx={pts[pts.length - 1].split(",")[0]}
        cy={pts[pts.length - 1].split(",")[1]}
        r="2.5"
        fill={color}
      />
    </svg>
  );
}

function posChange(curr: number | null, prev: number | null) {
  if (!curr || !prev) return null;
  return prev - curr; // positive = improved (rank went down)
}

export default function RankTrackerPage() {
  const { apiKey, businessProfile } = useAppStore();

  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [keywords, setKeywords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newKw, setNewKw] = useState({ keyword: "", region: "IN", locale: "en-US", is_primary: false });
  const [histories, setHistories] = useState<Record<string, number[]>>({});
  const [expandedKw, setExpandedKw] = useState<string | null>(null);

  useEffect(() => {
    listProjects(apiKey).then(setProjects).catch(() => {});
  }, [apiKey]);

  useEffect(() => {
    if (businessProfile?.projectId && !projectId) setProjectId(businessProfile.projectId);
  }, [businessProfile]);

  const loadKeywords = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const kws = await listProjectKeywords(projectId, apiKey);
      setKeywords(kws);
      // Fetch sparkline data for keywords that have positions
      for (const kw of kws.slice(0, 20)) {
        getKeywordHistory(kw.id, apiKey, 12)
          .then((hist) => {
            const positions = hist
              .filter((h) => h.position !== null)
              .map((h) => h.position as number)
              .reverse();
            if (positions.length > 0) {
              setHistories((prev) => ({ ...prev, [kw.id]: positions }));
            }
          })
          .catch(() => {});
      }
    } catch { toast.error("Failed to load keywords"); }
    finally { setLoading(false); }
  }, [projectId, apiKey]);

  useEffect(() => { loadKeywords(); }, [loadKeywords]);

  async function handleAddKeyword(e: React.FormEvent) {
    e.preventDefault();
    try {
      await addKeyword(projectId, newKw, apiKey);
      toast.success("Keyword added");
      setNewKw({ keyword: "", region: "IN", locale: "en-US", is_primary: false });
      setShowAdd(false);
      loadKeywords();
    } catch (err: any) { toast.error(err.message); }
  }

  async function handleDelete(id: string) {
    await deleteKeyword(id, apiKey);
    setKeywords((kws) => kws.filter((k) => k.id !== id));
    toast.success("Keyword removed");
  }

  async function handleRankCheck() {
    setChecking(true);
    try {
      await triggerRankCheck(projectId, apiKey);
      toast.success("Rank check started — results in ~2 min");
      setTimeout(loadKeywords, 30000);
    } catch { toast.error("Rank check failed"); }
    finally { setChecking(false); }
  }

  const topMover = keywords.reduce<any>((best, kw) => {
    const delta = posChange(kw.latest_position, kw.previous_position);
    if (delta !== null && (best === null || delta > best.delta)) return { kw, delta };
    return best;
  }, null);

  const avgPosition = keywords.length
    ? Math.round(keywords.filter((k) => k.latest_position).reduce((s, k) => s + k.latest_position, 0) /
        keywords.filter((k) => k.latest_position).length)
    : null;

  const top10Count = keywords.filter((k) => k.latest_position && k.latest_position <= 10).length;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Rank Tracker"
        subtitle="Live keyword positions from DataForSEO with sparklines, week-over-week deltas, and top-10 share."
        icon={BarChart3}
        accent="#EC4899"
        chips={businessProfile?.city && (
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium rounded-full px-3 py-1"
            style={{ background: "rgba(236,72,153,0.12)", color: "#F9A8D4", border: "1px solid rgba(236,72,153,0.3)" }}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {businessProfile.city} · {businessProfile.businessTypeLabel}
          </span>
        )}
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            {projects.length > 0 ? (
              <Select
                icon={FolderOpen}
                accent="#EC4899"
                placeholder="Select a project…"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                options={projects.map((p) => ({ value: p.id, label: p.name }))}
                widthClass="min-w-[240px]"
              />
            ) : (
              <input
                type="text"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="input-field max-w-[240px]"
                placeholder="Project ID"
              />
            )}
            {projectId && (
              <>
                <button onClick={loadKeywords} disabled={loading} className="btn-ghost flex items-center gap-1.5 text-sm px-3 py-2.5">
                  <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
                </button>
                <button
                  onClick={handleRankCheck}
                  disabled={checking || !projectId}
                  className="btn-secondary flex items-center gap-2 text-sm"
                >
                  {checking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  {checking ? "Checking…" : "Check Rankings"}
                </button>
                <button
                  onClick={() => setShowAdd(!showAdd)}
                  className="btn-primary flex items-center gap-2 text-sm"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Keyword
                </button>
              </>
            )}
          </div>
        }
      />

      {/* Add keyword panel */}
      {showAdd && (
        <form onSubmit={handleAddKeyword} className="card p-5 mb-6 animate-fade-in space-y-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold">Add keyword</h3>
            <button type="button" onClick={() => setShowAdd(false)} className="btn-ghost p-1">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="label">Keyword</label>
              <input
                type="text"
                value={newKw.keyword}
                onChange={(e) => setNewKw({ ...newKw, keyword: e.target.value })}
                className="input-field"
                placeholder={businessProfile?.city ? `e.g. best ${businessProfile.businessType} in ${businessProfile.city}` : "e.g. seo tools india"}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="label">Region</label>
              <select
                value={newKw.region}
                onChange={(e) => setNewKw({ ...newKw, region: e.target.value })}
                className="input-field"
              >
                <option value="IN">India</option>
                <option value="US">US</option>
                <option value="GB">UK</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer">
              <input
                type="checkbox"
                checked={newKw.is_primary}
                onChange={(e) => setNewKw({ ...newKw, is_primary: e.target.checked })}
                className="rounded"
              />
              Mark as primary keyword
            </label>
            <div className="flex-1" />
            <button type="button" onClick={() => setShowAdd(false)} className="btn-ghost text-sm">Cancel</button>
            <button type="submit" className="btn-primary text-sm">Add Keyword</button>
          </div>
        </form>
      )}

      {/* Summary KPIs */}
      {keywords.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: "Avg Position", value: avgPosition ?? "—", icon: TrendingUp, color: "text-teal-400" },
            { label: "Top 10", value: top10Count, icon: ArrowUp, color: "text-emerald-400" },
            { label: "Best Mover", value: topMover ? `+${topMover.delta}` : "—", icon: Sparkles, color: "text-brand-400" },
          ].map((m) => (
            <div key={m.label} className="metric-card">
              <div className="flex items-center justify-between mb-2">
                <span className="metric-label">{m.label}</span>
                <m.icon className={cn("w-4 h-4", m.color)} />
              </div>
              <div className={cn("metric-value", m.color)}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Keywords table */}
      {loading ? (
        <div className="card p-12 text-center">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-500 mx-auto mb-2" />
          <p className="text-sm text-zinc-500">Loading keywords…</p>
        </div>
      ) : keywords.length === 0 ? (
        <div className="card p-12 text-center">
          <Search className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
          <p className="text-sm text-zinc-400 mb-5">
            {projectId ? "No keywords tracked yet." : "Select a project to view keywords."}
          </p>
          {projectId && (
            <button onClick={() => setShowAdd(true)} className="btn-primary text-sm inline-flex items-center gap-2">
              <Plus className="w-4 h-4" /> Add first keyword
            </button>
          )}
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800">
                {["Keyword", "Position", "Change", "Trend", "Volume", "Intent", ""].map((h) => (
                  <th
                    key={h}
                    className={cn(
                      "px-5 py-3 text-zinc-500 font-medium text-xs uppercase tracking-wider",
                      h === "" ? "text-right" : "text-left"
                    )}
                  >{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keywords.map((kw) => {
                const delta = posChange(kw.latest_position, kw.previous_position);
                const sparkData = histories[kw.id] || [];
                return (
                  <tr key={kw.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/20 transition-colors">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {kw.is_primary && (
                          <span className="text-[9px] font-bold bg-brand-500/20 text-brand-400 border border-brand-500/30 rounded px-1.5 py-0.5 uppercase">
                            Primary
                          </span>
                        )}
                        <span className="font-medium text-zinc-200">{kw.keyword}</span>
                      </div>
                      <span className="text-[10px] text-zinc-600">{kw.target_region}</span>
                    </td>
                    <td className="px-5 py-3">
                      {kw.latest_position != null ? (
                        <span className={cn(
                          "text-lg font-bold font-serif",
                          kw.latest_position <= 3 ? "text-emerald-400" :
                          kw.latest_position <= 10 ? "text-teal-400" :
                          kw.latest_position <= 30 ? "text-amber-400" : "text-zinc-400"
                        )}>
                          #{kw.latest_position}
                        </span>
                      ) : (
                        <span className="text-zinc-600 text-xs">Not ranked</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      {delta !== null ? (
                        <span className={cn(
                          "flex items-center gap-1 text-sm font-medium",
                          delta > 0 ? "text-emerald-400" : delta < 0 ? "text-red-400" : "text-zinc-500"
                        )}>
                          {delta > 0 ? <ArrowUp className="w-3.5 h-3.5" /> : delta < 0 ? <ArrowDown className="w-3.5 h-3.5" /> : <Minus className="w-3.5 h-3.5" />}
                          {Math.abs(delta)}
                        </span>
                      ) : (
                        <span className="text-zinc-600 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <Sparkline data={sparkData} />
                    </td>
                    <td className="px-5 py-3 text-zinc-400 text-xs">
                      {kw.search_volume != null ? kw.search_volume.toLocaleString("en-IN") : "—"}
                    </td>
                    <td className="px-5 py-3">
                      {kw.intent ? (
                        <span className={cn("badge text-[10px]", {
                          "badge-info": kw.intent === "informational",
                          "badge-success": kw.intent === "transactional",
                          "badge-warning": kw.intent === "commercial",
                        })}>
                          {kw.intent}
                        </span>
                      ) : (
                        <span className="text-zinc-600 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => handleDelete(kw.id)}
                        className="btn-ghost p-1 text-zinc-600 hover:text-red-400 transition-colors"
                        title="Remove keyword"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
