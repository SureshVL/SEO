"use client";

import { useState } from "react";
import { FileText, Loader2, Plus, Printer } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReportsPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [projectId, setProjectId] = useState("");
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [viewHtml, setViewHtml] = useState<string | null>(null);

  async function loadReports() {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/reports`, { headers: { "X-API-KEY": apiKey } });
      if (res.ok) setReports(await res.json());
    } catch {} finally { setLoading(false); }
  }

  async function generateReport() {
    setGenerating(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/reports/generate?report_type=seo_audit`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (!res.ok) throw new Error(await res.text());
      toast.success("Report generated!");
      loadReports();
    } catch (err: any) {
      toast.error(err.message);
    } finally { setGenerating(false); }
  }

  async function viewReport(reportId: string) {
    try {
      const res = await fetch(`${API}/projects/${projectId}/reports/${reportId}/html`, {
        headers: { "X-API-KEY": apiKey },
      });
      if (res.ok) {
        const html = await res.text();
        setViewHtml(html);
      }
    } catch { toast.error("Failed to load report"); }
  }

  function printReport() {
    if (!viewHtml) return;
    const win = window.open("", "_blank");
    if (win) {
      win.document.write(viewHtml);
      win.document.close();
      setTimeout(() => win.print(), 500);
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><FileText className="w-6 h-6 text-brand-400" /> Reports</h1>
          <p className="text-sm text-zinc-400 mt-1">Generate AI-powered SEO reports with white-label options.</p>
        </div>
      </div>

      <div className="card p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <input type="text" value={projectId} onChange={e => setProjectId(e.target.value)} className="input-field" placeholder="Project ID" />
          </div>
          <button onClick={loadReports} disabled={!projectId} className="btn-secondary">Load Reports</button>
          <button onClick={generateReport} disabled={!projectId || generating} className="btn-primary flex items-center gap-2">
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Generate Report
          </button>
        </div>
      </div>

      {viewHtml ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <button onClick={() => setViewHtml(null)} className="btn-ghost text-sm">Back to list</button>
            <button onClick={printReport} className="btn-secondary flex items-center gap-2 text-sm"><Printer className="w-4 h-4" /> Print / Save PDF</button>
          </div>
          <div className="card overflow-hidden">
            <iframe srcDoc={viewHtml} className="w-full border-0" style={{ height: "80vh" }} title="SEO Report" />
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.length === 0 && !loading && (
            <div className="card p-12 text-center">
              <FileText className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
              <p className="text-sm text-zinc-400">No reports yet. Generate your first AI report above.</p>
            </div>
          )}
          {reports.map((r) => (
            <div key={r.id} className="card-hover p-5 flex items-center justify-between cursor-pointer" onClick={() => viewReport(r.id)}>
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-brand-400" />
                </div>
                <div>
                  <h3 className="font-medium text-sm">{r.title}</h3>
                  <p className="text-xs text-zinc-500">{r.report_type} · {new Date(r.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              {r.summary && <p className="text-xs text-zinc-400 max-w-xs truncate hidden md:block">{r.summary}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
