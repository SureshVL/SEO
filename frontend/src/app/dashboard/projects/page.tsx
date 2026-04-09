"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight, BarChart3, Bot, Globe, Loader2,
  MapPin, Plus, Star, Trash2, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { listProjects, listProjectKeywords } from "@/lib/api";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ProjectsPage() {
  const { apiKey, businessProfile, setBusinessProfile } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [kwCounts, setKwCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "", client_url: "", target_niche: "", goal_keywords: "",
  });

  async function fetchProjects() {
    setLoading(true);
    try {
      const ps = await listProjects(apiKey);
      setProjects(ps);
      // Fetch keyword counts in parallel
      const counts: Record<string, number> = {};
      await Promise.allSettled(
        ps.map(async (p) => {
          const kws = await listProjectKeywords(p.id, apiKey);
          counts[p.id] = kws.length;
        })
      );
      setKwCounts(counts);
    } catch { /* supabase not configured */ }
    finally { setLoading(false); }
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
          goal_keywords: form.goal_keywords
            ? form.goal_keywords.split(",").map((k) => k.trim()).filter(Boolean)
            : [],
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
      await fetch(`${API}/projects/${id}`, {
        method: "DELETE",
        headers: { "X-API-KEY": apiKey },
      });
      if (businessProfile?.projectId === id) {
        setBusinessProfile({ ...businessProfile, projectId: "" });
      }
      toast.success("Project deleted");
      fetchProjects();
    } catch { toast.error("Failed to delete"); }
  }

  function handleSetActive(p: any) {
    if (!businessProfile) return;
    const domain = p.domain || (() => { try { return new URL(p.client_url).hostname; } catch { return p.client_url; } })();
    setBusinessProfile({
      ...businessProfile,
      projectId: p.id,
      projectName: p.name,
      websiteUrl: p.client_url,
      keywords: p.goal_keywords || businessProfile.keywords,
    });
    toast.success(`Active project set to "${p.name}"`);
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-sm text-zinc-400 mt-1">Manage your SEO projects. The active project auto-fills all tools.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> New Project
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="card p-6 mb-6 border-brand-500/30 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Create new project</h3>
            <button onClick={() => setShowCreate(false)} className="btn-ghost p-1">
              <X className="w-4 h-4" />
            </button>
          </div>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">Project Name</label>
                <input
                  type="text" className="input-field"
                  placeholder="My Website SEO"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required autoFocus
                />
              </div>
              <div>
                <label className="label">Website URL</label>
                <input
                  type="url" className="input-field"
                  placeholder="https://example.com"
                  value={form.client_url}
                  onChange={(e) => setForm({ ...form, client_url: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="label">Niche / Industry</label>
                <input
                  type="text" className="input-field"
                  placeholder="e.g. SaaS, restaurant, healthcare"
                  value={form.target_niche}
                  onChange={(e) => setForm({ ...form, target_niche: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Goal Keywords (comma-separated)</label>
                <input
                  type="text" className="input-field"
                  placeholder="seo tools india, rank tracker"
                  value={form.goal_keywords}
                  onChange={(e) => setForm({ ...form, goal_keywords: e.target.value })}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" disabled={creating} className="btn-primary flex items-center gap-2">
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {creating ? "Creating…" : "Create Project"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="card p-12 text-center">
          <Loader2 className="w-6 h-6 animate-spin mx-auto text-zinc-500" />
        </div>
      ) : projects.length === 0 ? (
        <div className="card p-12 text-center">
          <Globe className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <h3 className="font-semibold text-lg mb-2">No projects yet</h3>
          <p className="text-sm text-zinc-400 max-w-sm mx-auto mb-6">
            Create your first project or complete onboarding to get started.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button onClick={() => setShowCreate(true)} className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-4 h-4" /> Create project
            </button>
            <Link href="/onboarding" className="btn-secondary inline-flex items-center gap-2">
              Run onboarding
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => {
            const domain = p.domain || (() => { try { return new URL(p.client_url).hostname; } catch { return p.client_url; } })();
            const isActive = businessProfile?.projectId === p.id;
            const kwCount = kwCounts[p.id] ?? null;
            const city = p.settings?.city;

            return (
              <div
                key={p.id}
                className={cn(
                  "card-hover p-5 group relative flex flex-col",
                  isActive && "border-brand-500/40 bg-brand-500/5"
                )}
              >
                {isActive && (
                  <div className="absolute -top-2.5 left-4 bg-brand-600 text-white text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <Star className="w-2.5 h-2.5" /> Active
                  </div>
                )}

                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0">
                      <Globe className="w-5 h-5 text-brand-400" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm">{p.name}</h3>
                      <p className="text-xs text-zinc-500 truncate max-w-[140px]">{domain}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="btn-ghost p-1.5 text-zinc-500 hover:text-red-400"
                      title="Delete project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Meta */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {city && (
                    <span className="flex items-center gap-1 text-[10px] bg-zinc-800/60 border border-zinc-700/40 text-zinc-400 rounded-full px-2 py-0.5">
                      <MapPin className="w-2.5 h-2.5" /> {city}
                    </span>
                  )}
                  {p.target_niche && (
                    <span className="text-[10px] bg-zinc-800/60 border border-zinc-700/40 text-zinc-400 rounded-full px-2 py-0.5">
                      {p.target_niche}
                    </span>
                  )}
                </div>

                {/* Keywords */}
                {p.goal_keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {p.goal_keywords.slice(0, 2).map((kw: string) => (
                      <span key={kw} className="text-[10px] bg-zinc-800/60 text-zinc-400 px-2 py-0.5 rounded">
                        {kw}
                      </span>
                    ))}
                    {p.goal_keywords.length > 2 && (
                      <span className="text-[10px] text-zinc-600">+{p.goal_keywords.length - 2}</span>
                    )}
                  </div>
                )}

                <div className="flex-1" />

                {/* Footer */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-800/50">
                  <div className="flex items-center gap-3">
                    <span className={cn("badge text-[10px]", p.status === "active" ? "badge-success" : "badge-warning")}>
                      {p.status}
                    </span>
                    {kwCount !== null && (
                      <span className="flex items-center gap-1 text-[10px] text-zinc-500">
                        <BarChart3 className="w-3 h-3" /> {kwCount} kw
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {!isActive && businessProfile && (
                      <button
                        onClick={() => handleSetActive(p)}
                        className="text-[10px] text-brand-400 hover:text-brand-300 font-medium"
                      >
                        Set active
                      </button>
                    )}
                    <Link
                      href={`/dashboard/research?project=${p.id}`}
                      className="text-xs text-zinc-400 hover:text-brand-400 flex items-center gap-1"
                    >
                      <Bot className="w-3 h-3" /> Research
                    </Link>
                    <Link
                      href={`/dashboard/rank-tracker`}
                      className="text-xs text-zinc-400 hover:text-teal-400 flex items-center gap-1"
                    >
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
