"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight, BarChart3, Bot, Globe, LayoutDashboard, Loader2,
  MapPin, Plus, Star, Trash2, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { listProjects, listProjectKeywords } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Card accent colors, cycled through the project list
const ACCENTS = ["#8B5CF6", "#EC4899", "#22D3EE", "#A3E635", "#F97316", "#FACC15", "#2DD4BF", "#818CF8"];

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
      <PageHeader
        title="Projects"
        subtitle="Manage your SEO projects. The active project auto-fills all tools."
        icon={LayoutDashboard}
        accent="#EC4899"
        actions={
          <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Project
          </button>
        }
      />

      {/* Create form */}
      {showCreate && (
        <div className="card p-6 mb-6 animate-fade-in" style={{ borderColor: "rgba(139,92,246,0.35)" }}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-base">Create new project</h3>
            <button onClick={() => setShowCreate(false)} className="btn-ghost p-1.5">
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
          <Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: "var(--violet)" }} />
        </div>
      ) : projects.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
               style={{ background: "rgba(139,92,246,0.12)" }}>
            <Globe className="w-7 h-7" style={{ color: "var(--violet)" }} />
          </div>
          <h3 className="font-semibold text-lg mb-2">No projects yet</h3>
          <p className="text-sm max-w-sm mx-auto mb-6" style={{ color: "var(--text-muted)" }}>
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
          {projects.map((p, idx) => {
            const accent = ACCENTS[idx % ACCENTS.length];
            const domain = p.domain || (() => { try { return new URL(p.client_url).hostname; } catch { return p.client_url; } })();
            const isActive = businessProfile?.projectId === p.id;
            const kwCount = kwCounts[p.id] ?? null;
            const city = p.settings?.city;

            return (
              <div
                key={p.id}
                className={cn(
                  "relative group rounded-2xl p-5 flex flex-col overflow-hidden transition-all duration-200",
                  "hover:-translate-y-0.5"
                )}
                style={{
                  background: isActive
                    ? `linear-gradient(180deg, ${accent}1a, ${accent}05)`
                    : "var(--bg-card)",
                  border: `1px solid ${isActive ? accent + "66" : "var(--border)"}`,
                  boxShadow: isActive ? `0 10px 30px ${accent}22` : "none",
                }}
              >
                {/* Accent top strip */}
                <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ background: accent, opacity: isActive ? 1 : 0.7 }} />

                {isActive && (
                  <div
                    className="absolute -top-2.5 left-4 text-[10px] font-bold uppercase tracking-[0.12em] px-2.5 py-1 rounded-full flex items-center gap-1 text-white shadow-lg"
                    style={{ background: accent, boxShadow: `0 4px 14px ${accent}66` }}
                  >
                    <Star className="w-2.5 h-2.5" fill="currentColor" /> Active
                  </div>
                )}

                <div className="flex items-start justify-between mb-3 mt-1">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                      style={{ background: `${accent}1f`, color: accent }}
                    >
                      <Globe className="w-5 h-5" strokeWidth={2.2} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-bold text-[15px] truncate" style={{ color: "var(--text-primary)" }}>{p.name}</h3>
                      <p className="text-xs truncate" style={{ color: "var(--text-muted)" }}>{domain}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="btn-ghost p-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: "var(--text-muted)" }}
                    title="Delete project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Meta */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {city && (
                    <span className="chip">
                      <MapPin className="w-3 h-3" /> {city}
                    </span>
                  )}
                  {p.target_niche && (
                    <span className="chip">{p.target_niche}</span>
                  )}
                </div>

                {/* Keywords */}
                {p.goal_keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {p.goal_keywords.slice(0, 3).map((kw: string) => (
                      <span
                        key={kw}
                        className="text-[10px] px-2 py-0.5 rounded font-medium"
                        style={{ background: `${accent}15`, color: accent }}
                      >
                        {kw}
                      </span>
                    ))}
                    {p.goal_keywords.length > 3 && (
                      <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        +{p.goal_keywords.length - 3}
                      </span>
                    )}
                  </div>
                )}

                <div className="flex-1" />

                {/* Footer */}
                <div className="flex items-center justify-between mt-3 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                  <div className="flex items-center gap-3">
                    <span className={cn("text-[10px]", p.status === "active" ? "badge-success" : "badge-warning")}>
                      {p.status}
                    </span>
                    {kwCount !== null && (
                      <span className="flex items-center gap-1 text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
                        <BarChart3 className="w-3 h-3" /> {kwCount} kw
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    {!isActive && businessProfile && (
                      <button
                        onClick={() => handleSetActive(p)}
                        className="text-[11px] font-semibold hover:opacity-80 transition-opacity"
                        style={{ color: accent }}
                      >
                        Set active
                      </button>
                    )}
                    <Link
                      href={`/dashboard/research?project=${p.id}`}
                      className="text-[11px] font-semibold flex items-center gap-1 transition-opacity hover:opacity-80"
                      style={{ color: accent }}
                    >
                      <Bot className="w-3 h-3" /> Research
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
