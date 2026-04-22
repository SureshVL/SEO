"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, ArrowUpRight, Eye, ExternalLink, FolderOpen,
  Loader2, RefreshCw, Sparkles, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { listProjects, listCompetitors, triggerCompetitorScan } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

export default function CompetitorsPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [competitors, setCompetitors] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => { listProjects(apiKey).then(setProjects).catch(() => {}); }, [apiKey]);
  useEffect(() => { if (businessProfile?.projectId && !projectId) setProjectId(businessProfile.projectId); }, [businessProfile]);

  const loadCompetitors = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await listCompetitors(projectId, apiKey);
      setCompetitors(data);
    } catch { /* no intel yet */ }
    finally { setLoading(false); }
  }, [projectId, apiKey]);

  useEffect(() => { loadCompetitors(); }, [loadCompetitors]);

  async function handleScan() {
    if (!projectId) { toast.error("Select a project first"); return; }
    setScanning(true);
    try {
      await triggerCompetitorScan(projectId, apiKey);
      toast.success("Competitor scan queued — changes logged in ~2 min");
      setTimeout(loadCompetitors, 30000);
    } catch (err: any) { toast.error(err.message || "Scan failed"); }
    finally { setScanning(false); }
  }

  // Parse entities from stored intel
  function getEntities(c: any): string[] {
    try {
      return c.entity_maps?.top_entities || [];
    } catch { return []; }
  }

  function getDomain(url: string) {
    try { return new URL(url).hostname.replace("www.", ""); } catch { return url; }
  }

  const uniqueDomains = [...new Set(competitors.map(c => getDomain(c.source_url)))];

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Competitor Monitor"
        subtitle="Track competitor content, entities, and backlink changes — know before they outrank you."
        icon={Eye}
        accent="#22D3EE"
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              icon={FolderOpen}
              accent="#22D3EE"
              placeholder="Select a project…"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              options={projects.map((p) => ({ value: p.id, label: p.name }))}
              widthClass="min-w-[220px]"
            />
            {projectId && (
              <>
                <button onClick={loadCompetitors} disabled={loading} className="btn-ghost flex items-center gap-1.5 text-sm px-3 py-2.5">
                  <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
                </button>
                <button onClick={handleScan} disabled={scanning} className="btn-primary flex items-center gap-2 text-sm">
                  {scanning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                  {scanning ? "Scanning…" : "Scan Competitors"}
                </button>
              </>
            )}
          </div>
        }
      />

      {/* KPI strip */}
      {competitors.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: "Competitors tracked", value: uniqueDomains.length, icon: Eye, color: "text-purple-400" },
            { label: "Pages indexed", value: competitors.length, icon: TrendingUp, color: "text-teal-400" },
            { label: "Entities mapped", value: competitors.reduce((n, c) => n + getEntities(c).length, 0), icon: Sparkles, color: "text-brand-400" },
          ].map(m => (
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

      {loading ? (
        <div className="card p-12 text-center">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-500 mx-auto mb-2" />
          <p className="text-sm text-zinc-500">Loading competitor intelligence…</p>
        </div>
      ) : competitors.length === 0 ? (
        <div className="card p-10 text-center">
          <Eye className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
          <h3 className="font-semibold text-lg mb-2">No competitor data yet</h3>
          <p className="text-sm text-zinc-400 max-w-md mx-auto mb-2">
            Competitors are auto-discovered when you run an <strong>AI Research</strong> job. Their pages are scraped and entity-mapped.
          </p>
          <p className="text-sm text-zinc-500 max-w-md mx-auto">
            Once discovered, use <em>Scan Competitors</em> to detect content changes and get AI strategy recommendations.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {competitors.map(c => {
            const entities = getEntities(c);
            const domain = getDomain(c.source_url);
            const isExpanded = expanded === c.id;
            const capturedAt = new Date(c.captured_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

            return (
              <div key={c.id} className="card overflow-hidden">
                <button
                  onClick={() => setExpanded(isExpanded ? null : c.id)}
                  className="w-full p-5 flex items-center justify-between hover:bg-zinc-800/20 transition-colors text-left"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center shrink-0">
                      <Eye className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <div className="font-medium text-sm flex items-center gap-2">
                        {domain}
                        <a
                          href={c.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="text-zinc-600 hover:text-brand-400"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                      <p className="text-xs text-zinc-500 mt-0.5 max-w-xs truncate">{c.source_url}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 shrink-0">
                    <div className="text-right hidden md:block">
                      <div className="text-xs text-zinc-500">Entities</div>
                      <div className="text-sm font-semibold text-teal-400">{entities.length}</div>
                    </div>
                    <div className="text-right hidden md:block">
                      <div className="text-xs text-zinc-500">Captured</div>
                      <div className="text-xs text-zinc-400">{capturedAt}</div>
                    </div>
                    <ArrowUpRight className={cn("w-4 h-4 text-zinc-600 transition-transform", isExpanded && "rotate-90")} />
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-zinc-800/50 pt-4 space-y-4 animate-fade-in">
                    {entities.length > 0 && (
                      <div>
                        <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mb-2">Top Entities</p>
                        <div className="flex flex-wrap gap-1.5">
                          {entities.slice(0, 20).map((e: string) => (
                            <span key={e} className="text-xs bg-purple-500/10 border border-purple-500/20 text-purple-300 rounded-full px-2.5 py-1">
                              {e}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {c.scraped_content && (
                      <div>
                        <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mb-2">Content Snapshot</p>
                        <p className="text-xs text-zinc-400 leading-relaxed line-clamp-4 bg-zinc-900/60 p-3 rounded-lg">
                          {c.scraped_content.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 600)}…
                        </p>
                      </div>
                    )}

                    {Object.keys(c.backlink_profiles || {}).length > 0 && (
                      <div>
                        <p className="text-xs text-zinc-500 uppercase tracking-wider font-medium mb-2">Backlink Profile</p>
                        <div className="flex gap-6 text-sm">
                          {Object.entries(c.backlink_profiles).slice(0, 4).map(([k, v]) => (
                            <div key={k}>
                              <span className="text-zinc-500 text-xs">{k.replace(/_/g, " ")}: </span>
                              <span className="text-zinc-300 font-medium">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
