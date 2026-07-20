"use client";

import { useState, useEffect } from "react";
import {
  Plus, Trash2, Loader2, Target, TrendingUp,
  ChevronDown, ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Competitor {
  id: number;
  domain: string;
  name: string;
  last_analyzed?: string;
}

interface Strategy {
  id: number;
  target_keyword: string;
  competitor_position: number;
  action: string;
  priority: number;
  status: "pending" | "in_progress" | "completed";
}

interface Analysis {
  domain: string;
  analysis: string;
  data_snapshot: {
    keyword_count: number;
    backlink_count: number;
    referring_domains: number;
  };
}

export default function CompetitorsPage() {
  const { apiKey } = useAppStore();

  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedCompetitor, setSelectedCompetitor] = useState<Competitor | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingStrategies, setGeneratingStrategies] = useState(false);

  const [newCompetitor, setNewCompetitor] = useState({
    domain: "",
    name: "",
  });

  const fetchCompetitors = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/competitors`);
      if (res.ok) {
        const data = await res.json();
        setCompetitors(data.competitors || []);
      }
    } catch (err) {
      console.error("Failed to fetch competitors:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalysis = async (competitorId: number) => {
    try {
      const res = await apiFetch(`/competitors/${competitorId}/analysis`);
      if (res.ok) {
        const data = await res.json();
        setAnalysis(data);
      }
    } catch (err) {
      console.error("Failed to fetch analysis:", err);
    }
  };

  const fetchStrategies = async (competitorId: number) => {
    try {
      const res = await apiFetch(`/competitors/strategies?competitor_id=${competitorId}`);
      if (res.ok) {
        const data = await res.json();
        setStrategies(data.strategies || []);
      }
    } catch (err) {
      console.error("Failed to fetch strategies:", err);
    }
  };

  useEffect(() => {
    fetchCompetitors();
  }, [apiKey]);

  useEffect(() => {
    if (selectedCompetitor) {
      fetchAnalysis(selectedCompetitor.id);
      fetchStrategies(selectedCompetitor.id);
    }
  }, [selectedCompetitor, apiKey]);

  const handleAddCompetitor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !newCompetitor.domain) {
      toast.error("Domain required");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch(`/competitors/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newCompetitor),
      });

      if (!res.ok) throw new Error("Failed");
      toast.success("Competitor added!");
      setShowAddModal(false);
      setNewCompetitor({ domain: "", name: "" });
      fetchCompetitors();
    } catch (err: any) {
      toast.error(err.message || "Failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!apiKey || !selectedCompetitor) return;

    setAnalyzing(true);
    try {
      const res = await apiFetch(`/competitors/${selectedCompetitor.id}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          competitor_id: selectedCompetitor.id,
          keywords: [],
          backlinks: 5000,
          referring_domains: 300,
          top_pages: [],
          content_pages: 1500,
          avg_content_length: 2000,
        }),
      });

      if (!res.ok) throw new Error("Failed");
      toast.success("Analysis complete!");
      fetchAnalysis(selectedCompetitor.id);
    } catch (err: any) {
      toast.error(err.message || "Failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerateStrategies = async () => {
    if (!apiKey || !selectedCompetitor) return;

    setGeneratingStrategies(true);
    try {
      const res = await apiFetch(`/competitors/${selectedCompetitor.id}/strategies`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          competitor_id: selectedCompetitor.id,
          your_keywords: ["seo", "content", "marketing"],
          your_rankings: {},
        }),
      });

      if (!res.ok) throw new Error("Failed");
      toast.success("Strategies generated!");
      fetchStrategies(selectedCompetitor.id);
    } catch (err: any) {
      toast.error(err.message || "Failed");
    } finally {
      setGeneratingStrategies(false);
    }
  };

  const priorityColor = (priority: number) => {
    if (priority >= 8) return "text-red-400";
    if (priority >= 6) return "text-orange-400";
    return "text-cyan-400";
  };

  return (
    <div className="min-h-screen bg-zinc-950">
      <PageHeader
        title="Competitor Analysis"
        subtitle="Analyze competitors and generate strategies to outrank them"
      />

      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-4">
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Competitor
            </button>

            <div className="space-y-2">
              {competitors.map((comp) => (
                <button
                  key={comp.id}
                  onClick={() => setSelectedCompetitor(comp)}
                  className={cn(
                    "w-full text-left p-3 rounded-lg border transition-all",
                    selectedCompetitor?.id === comp.id
                      ? "bg-cyan-500/10 border-cyan-500/50"
                      : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"
                  )}
                >
                  <div className="font-medium text-zinc-100 truncate">{comp.name || comp.domain}</div>
                  <div className="text-xs text-zinc-500 truncate">{comp.domain}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {selectedCompetitor ? (
              <>
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-zinc-100">{selectedCompetitor.name}</h2>
                    <a
                      href={`https://${selectedCompetitor.domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 text-sm flex items-center gap-1 mt-1"
                    >
                      {selectedCompetitor.domain}
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-zinc-100">Analysis</h3>
                    <button
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      className="btn-primary text-sm flex items-center gap-2"
                    >
                      {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
                      Analyze
                    </button>
                  </div>

                  {analysis ? (
                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4 space-y-3">
                      <div className="grid grid-cols-3 gap-2">
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-xs text-zinc-500">Keywords</div>
                          <div className="font-bold text-cyan-400">{analysis.data_snapshot?.keyword_count}</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-xs text-zinc-500">Backlinks</div>
                          <div className="font-bold text-violet-400">{(analysis.data_snapshot?.backlink_count / 1000).toFixed(1)}K</div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2">
                          <div className="text-xs text-zinc-500">Domains</div>
                          <div className="font-bold text-emerald-400">{analysis.data_snapshot?.referring_domains}</div>
                        </div>
                      </div>
                      <div className="border-t border-zinc-700 pt-2">
                        <div className="text-xs font-semibold text-zinc-300 mb-1">Insights</div>
                        <div className="text-sm text-zinc-300 line-clamp-6">{analysis.analysis}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6 text-center text-zinc-400 text-sm">
                      Run analysis
                    </div>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-zinc-100">Strategies</h3>
                    <button
                      onClick={handleGenerateStrategies}
                      disabled={generatingStrategies || !analysis}
                      className="btn-primary text-sm flex items-center gap-2"
                    >
                      {generatingStrategies ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
                      Generate
                    </button>
                  </div>

                  {strategies.length > 0 ? (
                    <div className="space-y-2">
                      {strategies.slice(0, 10).map((strategy) => (
                        <div key={strategy.id} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="font-medium text-zinc-100 text-sm">{strategy.target_keyword}</div>
                              <div className="flex gap-2 mt-1">
                                <span className={cn("text-xs font-bold", priorityColor(strategy.priority))}>P{strategy.priority}</span>
                                <span className="text-xs text-zinc-500">#{strategy.competitor_position}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6 text-center text-zinc-400 text-sm">
                      {analysis ? "Generate strategies" : "Run analysis first"}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-16 text-center">
                <Target className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                <div className="text-zinc-400">Select a competitor</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full">
            <div className="border-b border-zinc-800 p-4">
              <h2 className="text-lg font-semibold text-zinc-100">Add Competitor</h2>
            </div>

            <form onSubmit={handleAddCompetitor} className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">Domain</label>
                <input
                  type="text"
                  value={newCompetitor.domain}
                  onChange={(e) => setNewCompetitor({ ...newCompetitor, domain: e.target.value })}
                  placeholder="example.com"
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">Name</label>
                <input
                  type="text"
                  value={newCompetitor.name}
                  onChange={(e) => setNewCompetitor({ ...newCompetitor, name: e.target.value })}
                  placeholder="Company"
                  className="input-field w-full"
                />
              </div>

              <div className="flex gap-2 pt-4">
                <button type="button" onClick={() => setShowAddModal(false)} className="flex-1 btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="flex-1 btn-primary">
                  Add
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
