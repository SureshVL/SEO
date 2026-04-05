"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Globe, Loader2, Plus, Trash2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ProjectsPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", client_url: "", target_niche: "", goal_keywords: "" });

  async function fetchProjects() {
    try {
      const res = await fetch(`${API}/projects`, { headers: { "X-API-KEY": apiKey } });
      if (res.ok) setProjects(await res.json());
    } catch {} finally { setLoading(false); }
  }

  useEffect(() => { fetchProjects(); }, [apiKey]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await fetch(`${API}/projects`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          client_url: form.client_url,
          target_niche: form.target_niche || null,
          goal_keywords: form.goal_keywords ? form.goal_keywords.split(",").map(k => k.trim()) : [],
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      toast.success("Project created!");
      setShowCreate(false);
      setForm({ name: "", client_url: "", target_niche: "", goal_keywords: "" });
      fetchProjects();
    } catch (err: any) {
      toast.error(err.message || "Failed to create project");
    } finally { setCreating(false); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this project and all its data?")) return;
    try {
      await fetch(`${API}/projects/${id}`, { method: "DELETE", headers: { "X-API-KEY": apiKey } });
      toast.success("Project deleted");
      fetchProjects();
    } catch { toast.error("Failed to delete"); }
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-sm text-zinc-400 mt-1">Manage your SEO projects and tracked domains.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      {/* Create Dialog */}
      {showCreate && (
        <div className="card p-6 mb-6 border-brand-500/30 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Create new project</h3>
            <button onClick={() => setShowCreate(false)} className="btn-ghost p-1"><X className="w-4 h-4" /></button>
          </div>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Project Name</label>
                <input type="text" className="input-field" placeholder="My Website SEO" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div>
                <label className="label">Website URL</label>
                <input type="url" className="input-field" placeholder="https://example.com" value={form.client_url} onChange={e => setForm({ ...form, client_url: e.target.value })} required />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Niche / Industry (optional)</label>
                <input type="text" className="input-field" placeholder="e.g. SaaS, ecommerce, fintech" value={form.target_niche} onChange={e => setForm({ ...form, target_niche: e.target.value })} />
              </div>
              <div>
                <label className="label">Goal Keywords (comma-separated)</label>
                <input type="text" className="input-field" placeholder="seo tools, rank tracker, keyword research" value={form.goal_keywords} onChange={e => setForm({ ...form, goal_keywords: e.target.value })} />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={creating} className="btn-primary flex items-center gap-2">
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {creating ? "Creating..." : "Create Project"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Project List */}
      {loading ? (
        <div className="card p-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-zinc-500" /></div>
      ) : projects.length === 0 ? (
        <div className="card p-12 text-center">
          <Globe className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <h3 className="font-semibold text-lg mb-2">No projects yet</h3>
          <p className="text-sm text-zinc-400 max-w-sm mx-auto mb-6">Create your first project to start tracking keywords, running audits, and generating AI reports.</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary inline-flex items-center gap-2"><Plus className="w-4 h-4" /> Create first project</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => {
            const domain = p.domain || new URL(p.client_url).hostname;
            return (
              <div key={p.id} className="card-hover p-5 group relative">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center">
                      <Globe className="w-5 h-5 text-brand-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">{p.name}</h3>
                      <p className="text-xs text-zinc-500">{domain}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => handleDelete(p.id)} className="btn-ghost p-1.5 text-zinc-500 hover:text-red-400">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                {p.target_niche && <p className="text-xs text-zinc-500 mb-2">Niche: {p.target_niche}</p>}
                {p.goal_keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {p.goal_keywords.slice(0, 3).map((kw: string) => (
                      <span key={kw} className="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded">{kw}</span>
                    ))}
                    {p.goal_keywords.length > 3 && <span className="text-xs text-zinc-500">+{p.goal_keywords.length - 3}</span>}
                  </div>
                )}
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-800/50">
                  <span className={cn("badge text-xs", p.status === "active" ? "badge-success" : "badge-warning")}>{p.status}</span>
                  <Link href={`/dashboard/research?project=${p.id}`} className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
                    Open <ArrowUpRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
