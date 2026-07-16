"use client";

import { useState, useEffect } from "react";
import {
  Plus, Loader2, LinkIcon, AlertCircle, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Opportunity {
  id: number;
  target_url: string;
  anchor_text: string;
  relevance_score: number;
  priority: number;
  status: string;
}

interface SiteAnalysis {
  total_pages: number;
  topic_clusters: number;
  analysis: string;
}

export default function InternalLinkingPage() {
  const { apiKey } = useAppStore();

  const [tab, setTab] = useState<"analysis" | "opportunities">("analysis");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<SiteAnalysis | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [showAddPageModal, setShowAddPageModal] = useState(false);

  const [newPage, setNewPage] = useState({
    url: "",
    title: "",
    content: "",
    topics: "",
  });

  const fetchAnalysis = async () => {
    setAnalyzing(true);
    try {
      const res = await apiFetch(`/linking/analyze`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setAnalysis(data);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setAnalyzing(false);
    }
  };

  const fetchOpportunities = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/linking/opportunities`);
      if (res.ok) {
        const data = await res.json();
        setOpportunities(data.opportunities || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "analysis") {
      fetchAnalysis();
    } else {
      fetchOpportunities();
    }
  }, [tab, apiKey]);

  const handleAddPage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !newPage.url || !newPage.title) {
      toast.error("Required fields");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch(`/linking/pages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: newPage.url,
          title: newPage.title,
          content: newPage.content,
          topics: newPage.topics.split(",").map(t => t.trim()),
        }),
      });
      if (!res.ok) throw new Error("Failed");
      toast.success("Page added!");
      setShowAddPageModal(false);
      setNewPage({ url: "", title: "", content: "", topics: "" });
      fetchAnalysis();
    } catch (err: any) {
      toast.error(err.message || "Failed");
    } finally {
      setLoading(false);
    }
  };

  const handleApproveOpportunity = async (opportunityId: number) => {
    try {
      const res = await apiFetch(`/linking/opportunities/${opportunityId}?status=approved`, {
        method: "PATCH",
      });
      if (!res.ok) throw new Error("Failed");
      toast.success("Approved!");
      fetchOpportunities();
    } catch (err: any) {
      toast.error(err.message || "Failed");
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
        title="Internal Linking"
        subtitle="Discover and implement strategic internal links"
      />

      <div className="max-w-7xl mx-auto p-6">
        <div className="flex gap-2 border-b border-zinc-800 mb-6">
          <button
            onClick={() => setTab("analysis")}
            className={cn(
              "px-4 py-3 text-sm font-medium transition-colors",
              tab === "analysis"
                ? "border-b-2 border-cyan-500 text-cyan-400"
                : "text-zinc-400 hover:text-zinc-300"
            )}
          >
            Site Structure
          </button>
          <button
            onClick={() => setTab("opportunities")}
            className={cn(
              "px-4 py-3 text-sm font-medium transition-colors",
              tab === "opportunities"
                ? "border-b-2 border-cyan-500 text-cyan-400"
                : "text-zinc-400 hover:text-zinc-300"
            )}
          >
            Opportunities
          </button>
        </div>

        {tab === "analysis" ? (
          <div className="space-y-6">
            <button
              onClick={() => setShowAddPageModal(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Page
            </button>

            <button
              onClick={fetchAnalysis}
              disabled={analyzing}
              className="btn-secondary flex items-center gap-2"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4" />
                  Analyze Site
                </>
              )}
            </button>

            {analysis ? (
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-zinc-800/50 rounded p-4">
                    <div className="text-xs text-zinc-500 mb-1">Pages</div>
                    <div className="text-3xl font-bold text-cyan-400">
                      {analysis.total_pages}
                    </div>
                  </div>
                  <div className="bg-zinc-800/50 rounded p-4">
                    <div className="text-xs text-zinc-500 mb-1">Topics</div>
                    <div className="text-3xl font-bold text-violet-400">
                      {analysis.topic_clusters}
                    </div>
                  </div>
                </div>

                <div className="border-t border-zinc-700 pt-4">
                  <div className="text-sm font-semibold text-zinc-300 mb-2">Insights</div>
                  <div className="text-sm text-zinc-300 line-clamp-10">
                    {analysis.analysis}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-12 text-center text-zinc-400">
                <LinkIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">Add pages and analyze site structure</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {opportunities.length > 0 ? (
              opportunities.map((opp) => (
                <div key={opp.id} className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-zinc-100 text-sm">{opp.anchor_text}</div>
                      <div className="text-xs text-zinc-500 truncate mt-1">{opp.target_url}</div>
                      <div className="flex gap-3 mt-2">
                        <span className="text-xs text-zinc-600">
                          Score: {(opp.relevance_score * 100).toFixed(0)}%
                        </span>
                        <span className={cn("text-xs font-bold", priorityColor(opp.priority))}>
                          P{opp.priority}
                        </span>
                      </div>
                    </div>
                    {opp.status === "pending" && (
                      <button
                        onClick={() => handleApproveOpportunity(opp.id)}
                        className="btn-primary text-xs py-1 px-2 flex-shrink-0"
                      >
                        Approve
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-12 text-center text-zinc-400">
                <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">{loading ? "Loading..." : "No opportunities"}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {showAddPageModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full">
            <div className="border-b border-zinc-800 p-4">
              <h2 className="text-lg font-semibold text-zinc-100">Add Page</h2>
            </div>

            <form onSubmit={handleAddPage} className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 uppercase mb-1">URL</label>
                <input
                  type="url"
                  value={newPage.url}
                  onChange={(e) => setNewPage({ ...newPage, url: e.target.value })}
                  placeholder="https://example.com/page"
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase mb-1">Title</label>
                <input
                  type="text"
                  value={newPage.title}
                  onChange={(e) => setNewPage({ ...newPage, title: e.target.value })}
                  placeholder="Page Title"
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label className="block text-xs text-zinc-500 uppercase mb-1">Topics</label>
                <input
                  type="text"
                  value={newPage.topics}
                  onChange={(e) => setNewPage({ ...newPage, topics: e.target.value })}
                  placeholder="seo, content, marketing"
                  className="input-field w-full"
                />
              </div>

              <div className="flex gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddPageModal(false)}
                  className="flex-1 btn-secondary"
                >
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
