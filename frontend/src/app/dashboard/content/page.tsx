"use client";

import { useState } from "react";
import { FileText, Loader2, Plus, RefreshCw, Wand2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ContentPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [projectId, setProjectId] = useState("");
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [editBody, setEditBody] = useState("");
  const [rewriting, setRewriting] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newDraft, setNewDraft] = useState({ title: "", target_keyword: "", body_markdown: "" });
  const [creating, setCreating] = useState(false);

  async function loadContent() {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/content`, { headers: { "X-API-KEY": apiKey } });
      if (res.ok) setDrafts(await res.json());
    } catch {} finally { setLoading(false); }
  }

  function openDraft(draft: any) {
    setSelected(draft);
    setEditBody(draft.body_markdown || "");
  }

  async function saveDraft() {
    if (!selected) return;
    try {
      await fetch(`${API}/content/${selected.id}`, {
        method: "PATCH",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({ body_markdown: editBody }),
      });
      toast.success("Draft saved!");
      loadContent();
    } catch { toast.error("Failed to save"); }
  }

  async function aiRewrite() {
    if (!selected) return;
    setRewriting(true);
    try {
      const res = await fetch(`${API}/content/${selected.id}/ai-rewrite?instruction=Improve SEO optimization, readability, and add more entity coverage`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (!res.ok) throw new Error(await res.text());
      toast.success("Content rewritten by AI!");
      loadContent();
      // Reload the draft
      const updated = await fetch(`${API}/projects/${projectId}/content`, { headers: { "X-API-KEY": apiKey } });
      if (updated.ok) {
        const all = await updated.json();
        const refreshed = all.find((d: any) => d.id === selected.id);
        if (refreshed) { setSelected(refreshed); setEditBody(refreshed.body_markdown); }
      }
    } catch (err: any) { toast.error(err.message); }
    finally { setRewriting(false); }
  }

  async function updateStatus(id: string, status: string) {
    try {
      await fetch(`${API}/content/${id}`, {
        method: "PATCH",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({ queue_status: status }),
      });
      toast.success(`Status updated to ${status}`);
      loadContent();
    } catch { toast.error("Failed"); }
  }

  async function createDraft(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const res = await fetch(`${API}/projects/${projectId}/content`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify(newDraft),
      });
      if (!res.ok) throw new Error(await res.text());
      toast.success("Draft created!");
      setShowCreate(false);
      setNewDraft({ title: "", target_keyword: "", body_markdown: "" });
      loadContent();
    } catch (err: any) { toast.error(err.message); }
    finally { setCreating(false); }
  }

  const statusColors: Record<string, string> = {
    draft: "badge-info", review: "badge-warning", approved: "badge-success", published: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><FileText className="w-6 h-6 text-emerald-400" /> Content Manager</h1>
          <p className="text-sm text-zinc-400 mt-1">Write, edit, and manage SEO content with AI assistance.</p>
        </div>
      </div>

      {/* Project selector */}
      <div className="card p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <input type="text" value={projectId} onChange={e => setProjectId(e.target.value)} className="input-field" placeholder="Project ID" />
          </div>
          <button onClick={loadContent} disabled={!projectId} className="btn-primary">Load Content</button>
          {projectId && <button onClick={() => setShowCreate(true)} className="btn-secondary flex items-center gap-1.5"><Plus className="w-3.5 h-3.5" /> New Draft</button>}
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="card p-6 mb-6 animate-fade-in">
          <form onSubmit={createDraft} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div><label className="label">Title</label><input type="text" className="input-field" value={newDraft.title} onChange={e => setNewDraft({ ...newDraft, title: e.target.value })} required /></div>
              <div><label className="label">Target Keyword</label><input type="text" className="input-field" value={newDraft.target_keyword} onChange={e => setNewDraft({ ...newDraft, target_keyword: e.target.value })} required /></div>
            </div>
            <div><label className="label">Content (Markdown)</label><textarea className="input-field h-40 font-mono text-sm" value={newDraft.body_markdown} onChange={e => setNewDraft({ ...newDraft, body_markdown: e.target.value })} /></div>
            <div className="flex gap-3"><button type="submit" disabled={creating} className="btn-primary">{creating ? "Creating..." : "Create Draft"}</button><button type="button" onClick={() => setShowCreate(false)} className="btn-ghost">Cancel</button></div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Draft List */}
        <div className="lg:col-span-1 space-y-2">
          {drafts.map(d => (
            <div key={d.id} onClick={() => openDraft(d)} className={cn("card-hover p-4 cursor-pointer", selected?.id === d.id && "border-brand-500/50 bg-brand-500/5")}>
              <div className="flex items-center justify-between mb-1">
                <h4 className="text-sm font-medium truncate flex-1">{d.title}</h4>
                <span className={cn("badge text-[10px] ml-2", statusColors[d.queue_status] || "badge-info")}>{d.queue_status}</span>
              </div>
              <p className="text-xs text-zinc-500">{d.target_keyword || "No keyword"}</p>
              <p className="text-xs text-zinc-600 mt-1">{new Date(d.created_at).toLocaleDateString()}</p>
            </div>
          ))}
          {drafts.length === 0 && !loading && projectId && (
            <p className="text-sm text-zinc-500 text-center py-8">No content drafts yet. Run an AI Research job or create one manually.</p>
          )}
        </div>

        {/* Editor */}
        <div className="lg:col-span-2">
          {selected ? (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">{selected.title}</h3>
                <div className="flex items-center gap-2">
                  <button onClick={aiRewrite} disabled={rewriting} className="btn-ghost text-xs flex items-center gap-1.5 text-brand-400">
                    {rewriting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                    AI Rewrite
                  </button>
                  <button onClick={saveDraft} className="btn-primary text-xs">Save</button>
                </div>
              </div>
              <div className="flex gap-2 mb-4">
                {["draft", "review", "approved", "published"].map(s => (
                  <button key={s} onClick={() => updateStatus(selected.id, s)} className={cn("text-xs px-2.5 py-1 rounded-md", selected.queue_status === s ? "bg-brand-500/20 text-brand-300" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800")}>
                    {s}
                  </button>
                ))}
              </div>
              <textarea
                value={editBody}
                onChange={e => setEditBody(e.target.value)}
                className="input-field h-[500px] font-mono text-sm leading-relaxed resize-none"
                placeholder="Write your content in Markdown..."
              />
              <div className="flex items-center justify-between mt-3 text-xs text-zinc-500">
                <span>{editBody.split(/\s+/).filter(Boolean).length} words</span>
                <span>Keyword: {selected.target_keyword || "—"}</span>
              </div>
            </div>
          ) : (
            <div className="card p-12 text-center">
              <FileText className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
              <p className="text-sm text-zinc-400">Select a draft to edit, or create a new one.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
