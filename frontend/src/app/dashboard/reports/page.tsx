"use client";

import { useState, useEffect } from "react";
import { ClipboardList, Download, FileText, FolderOpen, Loader2, Plus, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  listProjects, listReports, generateReport, getReportHtml,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

export default function ReportsPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [projects, setProjects] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [viewHtml, setViewHtml] = useState<string | null>(null);
  const [viewTitle, setViewTitle] = useState("");

  // Load projects for selector
  useEffect(() => {
    listProjects(apiKey).then(setProjects).catch(() => {});
  }, [apiKey]);

  // Auto-load if profile project is set
  useEffect(() => {
    if (businessProfile?.projectId) {
      setProjectId(businessProfile.projectId);
    }
  }, [businessProfile]);

  useEffect(() => {
    if (projectId) loadReports();
  }, [projectId]);

  async function loadReports() {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await listReports(projectId, apiKey);
      setReports(data);
    } catch { /* project may have no reports yet */ }
    finally { setLoading(false); }
  }

  async function handleGenerate(type = "seo_audit") {
    if (!projectId) { toast.error("Select a project first"); return; }
    setGenerating(true);
    try {
      await generateReport(projectId, type, apiKey);
      toast.success("Report generated!");
      await loadReports();
    } catch (err: any) {
      toast.error(err.message || "Failed to generate report");
    } finally { setGenerating(false); }
  }

  async function handleView(report: any) {
    try {
      const html = await getReportHtml(projectId, report.id, apiKey);
      setViewHtml(html);
      setViewTitle(report.title);
    } catch { toast.error("Failed to load report"); }
  }

  function handlePrint() {
    if (!viewHtml) return;
    const win = window.open("", "_blank");
    if (win) {
      win.document.write(viewHtml);
      win.document.close();
      setTimeout(() => win.print(), 500);
    }
  }

  const selectedProject = projects.find((p) => p.id === projectId);

  return (
    <div className="animate-fade-in">
      {!viewHtml && (
        <PageHeader
          title="Reports"
          subtitle="AI-powered SEO reports with monthly rank trends, audit summaries, and exportable PDFs."
          icon={ClipboardList}
          accent="#EC4899"
          actions={
            <div className="flex items-center gap-2 flex-wrap">
              {projects.length > 0 ? (
                <Select
                  icon={FolderOpen}
                  accent="#EC4899"
                  placeholder="Select a project…"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  options={projects.map((p) => ({
                    value: p.id,
                    label: `${p.name} (${p.domain || (() => { try { return new URL(p.client_url).hostname; } catch { return p.client_url; } })()})`,
                  }))}
                  widthClass="min-w-[280px]"
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
                  <button
                    onClick={loadReports}
                    disabled={loading}
                    className="btn-ghost flex items-center gap-1.5 text-sm px-3 py-2.5"
                  >
                    <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
                  </button>
                  <button
                    onClick={() => handleGenerate("seo_audit")}
                    disabled={generating}
                    className="btn-primary flex items-center gap-2 text-sm"
                  >
                    {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                    {generating ? "Generating…" : "Generate Report"}
                  </button>
                </>
              )}
            </div>
          }
        />
      )}

      {/* Report viewer */}
      {viewHtml ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <button onClick={() => setViewHtml(null)} className="btn-ghost text-sm">
                ← Back to reports
              </button>
              <span className="text-xs text-zinc-500 ml-3">{viewTitle}</span>
            </div>
            <button
              onClick={handlePrint}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <Download className="w-4 h-4" /> Download PDF
            </button>
          </div>
          <div className="card overflow-hidden rounded-xl">
            <iframe
              srcDoc={viewHtml}
              className="w-full border-0"
              style={{ height: "82vh" }}
              title="SEO Report"
            />
          </div>
        </div>
      ) : (
        <>
          {loading ? (
            <div className="card p-12 text-center">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-500 mx-auto mb-3" />
              <p className="text-sm text-zinc-500">Loading reports…</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="card p-12 text-center">
              <FileText className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
              <p className="text-sm text-zinc-400 mb-5">
                {projectId ? "No reports yet for this project." : "Select a project to view reports."}
              </p>
              {projectId && (
                <button
                  onClick={() => handleGenerate("seo_audit")}
                  disabled={generating}
                  className="btn-primary text-sm inline-flex items-center gap-2"
                >
                  {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  Generate your first report
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {reports.map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleView(r)}
                  className="card-hover p-5 flex items-center justify-between w-full text-left"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5 text-brand-400" />
                    </div>
                    <div>
                      <h3 className="font-medium text-sm">{r.title}</h3>
                      <p className="text-xs text-zinc-500 mt-0.5">
                        {r.report_type} ·{" "}
                        {new Date(r.created_at).toLocaleDateString("en-IN", {
                          day: "numeric", month: "short", year: "numeric",
                        })}
                      </p>
                    </div>
                  </div>
                  {r.summary && (
                    <p className="text-xs text-zinc-400 max-w-xs truncate hidden md:block">{r.summary}</p>
                  )}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
