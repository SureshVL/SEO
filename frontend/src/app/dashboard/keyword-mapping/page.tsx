"use client";

import { useState, useEffect } from "react";
import {
  Plus, Loader2, Tag, AlertCircle, TrendingUp, Upload, Target,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Keyword {
  keyword: string;
  search_volume: number;
  difficulty: number;
  intent: string;
}

interface KeywordCluster {
  cluster_name: string;
  seed_keyword: string;
  keywords: string[];
  intent: string;
  volume: number;
  difficulty: number;
}

interface URLAssignment {
  url: string;
  primary_keyword: string;
  secondary_keywords: string[];
  target_volume: number;
  priority: number;
}

interface KeywordGap {
  keyword: string;
  volume: number;
  gap_type: string;
  recommendation: string;
  impact: number;
  priority: number;
}

export default function KeywordMappingPage() {
  const { apiKey } = useAppStore();

  const [tab, setTab] = useState<"keywords" | "clusters" | "mappings" | "gaps">("keywords");
  const [loading, setLoading] = useState(false);
  const [clustering, setClustering] = useState(false);
  const [assigning, setAssigning] = useState(false);

  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [clusters, setClusters] = useState<KeywordCluster[]>([]);
  const [assignments, setAssignments] = useState<URLAssignment[]>([]);
  const [gaps, setGaps] = useState<KeywordGap[]>([]);

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadText, setUploadText] = useState("");

  const fetchClusters = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/keywords/clusters`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setClusters(data.clusters || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchMappings = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/keywords/mappings`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setAssignments(data.mappings || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchGaps = async () => {
    setLoading(true);
    try {
      // run the AI analysis (stores results), then read them back
      const res = await apiFetch(`/keywords/gaps/identify`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setGaps(data.opportunities || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "clusters") {
      fetchClusters();
    } else if (tab === "mappings") {
      fetchMappings();
    } else if (tab === "gaps") {
      fetchGaps();
    }
  }, [tab, apiKey]);

  const handleImportKeywords = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !uploadText.trim()) {
      toast.error("Add at least one keyword");
      return;
    }

    setLoading(true);
    try {
      const lines = uploadText.trim().split("\n");
      const keywordsList = lines.map((line) => {
        const [keyword, volume, difficulty] = line.split(",").map((s) => s.trim());
        return {
          keyword: keyword || "",
          search_volume: parseInt(volume) || 0,
          difficulty: parseInt(difficulty) || 0,
          intent: "informational",
        };
      }).filter((kw) => kw.keyword);

      const res = await apiFetch(`/keywords/import`, {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ keywords: keywordsList }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(`Imported ${data.imported_count} keywords`);
        setUploadText("");
        setShowUploadModal(false);
      } else {
        toast.error("Import failed");
      }
    } catch (err) {
      console.error("Failed:", err);
      toast.error("Error importing keywords");
    } finally {
      setLoading(false);
    }
  };

  const handleClusterKeywords = async () => {
    setClustering(true);
    try {
      const res = await apiFetch(`/keywords/cluster`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setClusters(data.clusters || []);
        toast.success(`Created ${data.count} clusters`);
      } else {
        toast.error("Clustering failed");
      }
    } catch (err) {
      console.error("Failed:", err);
      toast.error("Error clustering keywords");
    } finally {
      setClustering(false);
    }
  };

  const handleAssignKeywords = async () => {
    setAssigning(true);
    try {
      const res = await apiFetch(`/keywords/assign`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setAssignments(data.assignments || []);
        toast.success(`Assigned ${data.count} clusters to URLs`);
      } else {
        toast.error("Assignment failed");
      }
    } catch (err) {
      console.error("Failed:", err);
      toast.error("Error assigning keywords");
    } finally {
      setAssigning(false);
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return "bg-red-100 text-red-800";
    if (priority >= 5) return "bg-orange-100 text-orange-800";
    return "bg-yellow-100 text-yellow-800";
  };

  const getIntentColor = (intent: string) => {
    const colors: Record<string, string> = {
      informational: "bg-blue-100 text-blue-800",
      commercial: "bg-green-100 text-green-800",
      transactional: "bg-purple-100 text-purple-800",
      navigational: "bg-gray-100 text-gray-800",
    };
    return colors[intent] || "bg-gray-100 text-gray-800";
  };

  const tabs = [
    { id: "keywords", label: "Keywords", icon: Tag },
    { id: "clusters", label: "Clusters", icon: TrendingUp },
    { id: "mappings", label: "Mappings", icon: Target },
    { id: "gaps", label: "Gaps", icon: AlertCircle },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Keyword Mapping"
        description="Organize keywords by intent, cluster them by topic, and assign to URLs"
      />

      <div className="flex gap-2 border-b">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={cn(
                "px-4 py-2 font-medium text-sm border-b-2 transition-colors flex items-center gap-2",
                tab === t.id
                  ? "border-violet-500 text-violet-600"
                  : "border-transparent text-gray-600 hover:text-gray-900",
              )}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border">
        {tab === "keywords" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Keywords</h3>
                <p className="text-sm text-gray-600">Import and manage your target keywords</p>
              </div>
              <button
                onClick={() => setShowUploadModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition"
              >
                <Upload className="w-4 h-4" />
                Import Keywords
              </button>
            </div>

            {keywords.length === 0 ? (
              <div className="text-center py-12">
                <Tag className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No keywords imported yet</p>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="mt-4 text-violet-600 hover:text-violet-700 font-medium"
                >
                  Import keywords to get started
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {keywords.slice(0, 10).map((kw) => (
                  <div
                    key={kw.keyword}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{kw.keyword}</p>
                      <p className="text-sm text-gray-600">
                        Vol: {kw.search_volume.toLocaleString()} | Difficulty: {kw.difficulty}%
                      </p>
                    </div>
                    <span className={cn("px-3 py-1 rounded-full text-xs font-medium", getIntentColor(kw.intent))}>
                      {kw.intent}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "clusters" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Keyword Clusters</h3>
                <p className="text-sm text-gray-600">Keywords organized by semantic similarity</p>
              </div>
              <button
                onClick={handleClusterKeywords}
                disabled={clustering}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition disabled:opacity-50"
              >
                {clustering && <Loader2 className="w-4 h-4 animate-spin" />}
                {clustering ? "Clustering..." : "Create Clusters"}
              </button>
            </div>

            {clusters.length === 0 ? (
              <div className="text-center py-12">
                <TrendingUp className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No clusters created yet</p>
                <button
                  onClick={handleClusterKeywords}
                  disabled={clustering}
                  className="mt-4 text-violet-600 hover:text-violet-700 font-medium disabled:opacity-50"
                >
                  {clustering ? "Clustering..." : "Cluster keywords to get started"}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {clusters.map((cluster) => (
                  <div
                    key={cluster.cluster_name}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{cluster.cluster_name}</h4>
                        <p className="text-sm text-gray-600">Seed: {cluster.seed_keyword}</p>
                      </div>
                      <span className={cn("px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap", getIntentColor(cluster.intent))}>
                        {cluster.intent}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      Keywords: {cluster.keywords.join(", ")}
                    </div>
                    <div className="flex gap-4 text-xs text-gray-600">
                      <span>Volume: {cluster.volume.toLocaleString()}</span>
                      <span>Avg Difficulty: {cluster.difficulty}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "mappings" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">URL Assignments</h3>
                <p className="text-sm text-gray-600">Clusters assigned to target URLs</p>
              </div>
              <button
                onClick={handleAssignKeywords}
                disabled={assigning}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition disabled:opacity-50"
              >
                {assigning && <Loader2 className="w-4 h-4 animate-spin" />}
                {assigning ? "Assigning..." : "Assign to URLs"}
              </button>
            </div>

            {assignments.length === 0 ? (
              <div className="text-center py-12">
                <Target className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No assignments created yet</p>
                <button
                  onClick={handleAssignKeywords}
                  disabled={assigning}
                  className="mt-4 text-violet-600 hover:text-violet-700 font-medium disabled:opacity-50"
                >
                  {assigning ? "Assigning..." : "Assign clusters to URLs"}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {assignments.map((assignment) => (
                  <div
                    key={assignment.url}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{assignment.url}</h4>
                        <p className="text-sm text-gray-600">Primary: {assignment.primary_keyword}</p>
                      </div>
                      <span className={cn("px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap", getPriorityColor(assignment.priority))}>
                        P{assignment.priority}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      Secondary: {assignment.secondary_keywords.join(", ") || "None"}
                    </div>
                    <div className="text-xs text-gray-600">
                      Target Volume: {assignment.target_volume.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "gaps" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">Content Gaps</h3>
                <p className="text-sm text-gray-600">Unmapped keywords with opportunities</p>
              </div>
            </div>

            {gaps.length === 0 ? (
              <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No gaps identified</p>
                <button
                  onClick={fetchGaps}
                  className="mt-4 text-violet-600 hover:text-violet-700 font-medium"
                >
                  Analyze gaps
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {gaps.map((gap) => (
                  <div
                    key={gap.keyword}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900">{gap.keyword}</h4>
                        <p className="text-sm text-gray-600">{gap.gap_type.replace(/_/g, " ")}</p>
                      </div>
                      <span className={cn("px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap", getPriorityColor(gap.priority))}>
                        P{gap.priority}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      Recommendation: {gap.recommendation}
                    </div>
                    <div className="flex gap-4 text-xs text-gray-600">
                      <span>Volume: {gap.volume.toLocaleString()}</span>
                      <span>Impact: {gap.impact}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Import Keywords</h3>
            <p className="text-sm text-gray-600 mb-4">
              Paste keywords as CSV (keyword, volume, difficulty). One per line.
            </p>
            <form onSubmit={handleImportKeywords} className="space-y-4">
              <textarea
                value={uploadText}
                onChange={(e) => setUploadText(e.target.value)}
                placeholder="seo basics, 5000, 25&#10;how to do seo, 3000, 30&#10;seo guide, 2000, 28"
                className="w-full h-32 p-3 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 transition"
                >
                  {loading ? "Importing..." : "Import"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
