"use client";

import { useState, useEffect } from "react";
import {
  Play, Loader2, AlertTriangle, CheckCircle, Clock, Zap, Target, Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AuditIssue {
  id: number;
  issue_type: string;
  severity: string;
  affected_url: string;
  description: string;
  recommendation: string;
  status: string;
}

interface AuditRun {
  id: number;
  audit_type: string;
  status: string;
  total_pages_checked: number;
  issues_found: number;
  critical_count: number;
  warning_count: number;
  completed_at: string;
}

interface AuditSummary {
  total_open_issues: number;
  critical_count: number;
  warning_count: number;
  recent_audits: number;
  health_score: number;
  last_audit: string | null;
  issues_by_type: Record<string, number>;
}

export default function AuditPage() {
  const { apiKey } = useAppStore();
  const [tab, setTab] = useState<"summary" | "issues" | "runs" | "schedules">("summary");
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [issues, setIssues] = useState<AuditIssue[]>([]);
  const [runs, setRuns] = useState<AuditRun[]>([]);

  const auditTypes = [
    { id: "crawl_errors", name: "Crawl Errors", icon: AlertTriangle, description: "Check for crawl/indexing errors" },
    { id: "broken_links", name: "Broken Links", icon: Target, description: "Find 404s and dead links" },
    { id: "schema_validation", name: "Schema Validation", icon: Shield, description: "Validate structured data" },
    { id: "performance", name: "Page Performance", icon: Zap, description: "Analyze Core Web Vitals" },
    { id: "orphan_pages", name: "Orphan Pages", icon: Clock, description: "Identify unlinked pages" },
  ];

  const fetchSummary = async () => {
    if (!apiKey) return;
    try {
      const res = await apiFetch(`/audits/summary`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) setSummary(await res.json());
    } catch (err) {
      console.error("Failed:", err);
    }
  };

  const fetchIssues = async () => {
    if (!apiKey) return;
    try {
      const res = await apiFetch(`/audits/issues`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setIssues(data.issues || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    }
  };

  const fetchRuns = async () => {
    if (!apiKey) return;
    try {
      const res = await apiFetch(`/audits/runs`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setRuns(data.runs || []);
      }
    } catch (err) {
      console.error("Failed:", err);
    }
  };

  useEffect(() => {
    if (tab === "summary") fetchSummary();
    else if (tab === "issues") fetchIssues();
    else if (tab === "runs") fetchRuns();
  }, [tab, apiKey]);

  const handleRunAudit = async (auditType: string) => {
    if (!apiKey) return;
    setRunning(auditType);
    try {
      const res = await apiFetch(`/audits/run`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({ audit_type: auditType, audit_data: [] }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Audit completed: ${data.issues_found} issues found`);
        fetchRuns();
        fetchSummary();
      }
    } catch (err) {
      toast.error("Error running audit");
    } finally {
      setRunning(null);
    }
  };

  const handleUpdateIssueStatus = async (issueId: number, status: string) => {
    if (!apiKey) return;
    try {
      const res = await apiFetch(`/audits/issues/${issueId}`, {
        method: "PATCH",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        toast.success(`Issue marked as ${status}`);
        fetchIssues();
      }
    } catch (err) {
      toast.error("Error updating issue");
    }
  };

  const getSeverityColor = (severity: string) => {
    if (severity === "critical") return "bg-red-100 text-red-800";
    if (severity === "warning") return "bg-orange-100 text-orange-800";
    return "bg-blue-100 text-blue-800";
  };

  const tabs = [
    { id: "summary", label: "Summary", icon: Shield },
    { id: "issues", label: "Issues", icon: AlertTriangle },
    { id: "runs", label: "Runs", icon: Clock },
    { id: "schedules", label: "Schedules", icon: Zap },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Technical Audits"
        description="Continuous monitoring for SEO issues"
      />

      <div className="flex gap-2 border-b overflow-x-auto">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={cn(
                "px-4 py-2 font-medium text-sm border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap",
                tab === t.id ? "border-lime-500 text-lime-600" : "border-transparent text-gray-600 hover:text-gray-900",
              )}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="bg-white rounded-lg border p-6">
        {tab === "summary" && summary && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-gradient-to-br from-lime-50 to-green-50 rounded-lg p-4 border border-lime-200">
                <div className="text-3xl font-bold text-lime-600">{summary.health_score}</div>
                <p className="text-sm text-gray-600 mt-1">Health Score</p>
              </div>
              <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-lg p-4 border border-red-200">
                <div className="text-3xl font-bold text-red-600">{summary.critical_count}</div>
                <p className="text-sm text-gray-600 mt-1">Critical Issues</p>
              </div>
              <div className="bg-gradient-to-br from-orange-50 to-yellow-50 rounded-lg p-4 border border-orange-200">
                <div className="text-3xl font-bold text-orange-600">{summary.warning_count}</div>
                <p className="text-sm text-gray-600 mt-1">Warnings</p>
              </div>
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg p-4 border border-blue-200">
                <div className="text-3xl font-bold text-blue-600">{summary.recent_audits}</div>
                <p className="text-sm text-gray-600 mt-1">Recent Audits</p>
              </div>
            </div>
          </div>
        )}

        {tab === "issues" && (
          <div className="space-y-4">
            {issues.length === 0 ? (
              <div className="text-center py-12">
                <CheckCircle className="w-12 h-12 text-green-300 mx-auto mb-4" />
                <p className="text-gray-500">No open issues!</p>
              </div>
            ) : (
              issues.slice(0, 20).map((issue) => (
                <div key={issue.id} className="border rounded-lg p-4 hover:bg-gray-50 transition">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn("px-2 py-1 rounded-full text-xs font-medium", getSeverityColor(issue.severity))}>
                          {issue.severity.toUpperCase()}
                        </span>
                        <h4 className="font-semibold text-gray-900">{issue.issue_type.replace(/_/g, " ")}</h4>
                      </div>
                      <p className="text-sm text-gray-600">{issue.affected_url}</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{issue.description}</p>
                  <p className="text-xs text-gray-600 mb-3">Fix: {issue.recommendation}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdateIssueStatus(issue.id, "in_progress")}
                      className="text-xs px-3 py-1 border rounded hover:bg-gray-50"
                    >
                      In Progress
                    </button>
                    <button
                      onClick={() => handleUpdateIssueStatus(issue.id, "resolved")}
                      className="text-xs px-3 py-1 border rounded hover:bg-gray-50"
                    >
                      Resolve
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "runs" && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              {auditTypes.map((audit) => {
                const Icon = audit.icon;
                return (
                  <button
                    key={audit.id}
                    onClick={() => handleRunAudit(audit.id)}
                    disabled={running === audit.id}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition text-left disabled:opacity-50"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <Icon className="w-5 h-5 text-lime-600" />
                      {running === audit.id && <Loader2 className="w-4 h-4 animate-spin" />}
                    </div>
                    <h4 className="font-semibold text-gray-900">{audit.name}</h4>
                    <p className="text-sm text-gray-600">{audit.description}</p>
                  </button>
                );
              })}
            </div>
            <div className="border-t pt-6">
              <h3 className="font-semibold text-gray-900 mb-4">Recent Runs</h3>
              {runs.slice(0, 10).map((run) => (
                <div key={run.id} className="border rounded-lg p-4 mb-3">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="font-semibold text-gray-900">{run.audit_type.replace(/_/g, " ")}</h4>
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">{run.status}</span>
                  </div>
                  <div className="text-sm text-gray-600 flex gap-4">
                    <span>Pages: {run.total_pages_checked}</span>
                    <span className="text-red-600">Critical: {run.critical_count}</span>
                    <span className="text-orange-600">Warnings: {run.warning_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "schedules" && (
          <div className="text-center py-12">
            <Clock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Audit schedules will be displayed here</p>
          </div>
        )}
      </div>
    </div>
  );
}
