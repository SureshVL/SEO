"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft, Check, FileText, FolderOpen, Loader2, Plus,
  RefreshCw, Sparkles, Wand2, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  listProjects, listContent, createContentDraft,
  updateContent, aiRewriteContent,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { toast } from "sonner";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-zinc-700/50 text-zinc-300 border-zinc-600/30",
  review: "badge-warning",
  approved: "badge-success",
  published: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
};

export default function ContentPage() {
  const { apiKey, businessProfile } = useAppStore();

  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [editBody, setEditBody] = useState("");
  const [rewriting, setRewriting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newDraft, setNewDraft] = useState({
    title: "",
    target_keyword: "",
    body_markdown: "",
  });

  useEffect(() => { listProjects(apiKey).then(setProjects).catch(() => {}); }, [apiKey]);
  useEffect(() => { if (businessProfile?.projectId && !projectId) setProjectId(businessProfile.projectId); }, [businessProfile]);

  const loadDrafts = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try { setDrafts(await listContent(projectId, apiKey)); }
    catch { /* empty */ }
    finally { setLoading(false); }
  }, [projectId, apiKey]);

  useEffect(() => { loadDrafts(); }, [loadDrafts]);

  function openDraft(draft: any) {
    setSelected(draft);
    setEditBody(draft.body_markdown || "");
    setShowCreate(false);
  }

  async function handleSave() {
    if (!selected) return;
    setSaving(true);
    try {
      await updateContent(selected.id, { body_markdown: editBody }, apiKey);
      toast.success("Draft saved");
      loadDrafts();
    } catch { toast.error("Save failed"); }
    finally { setSaving(false); }
  }

  async function handleAiRewrite() {
    if (!selected) return;
    setRewriting(true);
    try {
      const instruction = `Improve SEO optimization for keyword "${selected.target_keyword || "seo"}". Add entity coverage, improve headings structure, and enhance readability for ${businessProfile?.city || "India"} audience.`;
      await aiRewriteContent(selected.id, instruction, apiKey);
      toast.success("Content rewritten by Claude!");
      // Reload the draft to get updated content
      const all = await listContent(projectId, apiKey);
      setDrafts(all);
      const refreshed = all.find((d: any) => d.id === selected.id);
      if (refreshed) { setSelected(refreshed); setEditBody(refreshed.body_markdown); }
    } catch (err: any) { toast.error(err.message || "Rewrite failed"); }
    finally { setRewriting(false); }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId) { toast.error("Select a project first"); return; }
    setCreating(true);
    try {
      await createContentDraft(projectId, {
        title: newDraft.title,
        body_markdown: newDraft.body_markdown || `# ${newDraft.title}\n\nStart writing your SEO-optimised content here...\n`,
        target_keyword: newDraft.target_keyword,
        publish_target: "wordpress",
      }, apiKey);
      toast.success("Draft created!");
      setShowCreate(false);
      setNewDraft({ title: "", target_keyword: "", body_markdown: "" });
      loadDrafts();
    } catch (err: any) { toast.error(err.message || "Failed to create"); }
    finally { setCreating(false); }
  }

  async function handleStatusChange(id: string, status: string) {
    try {
      await updateContent(id, { queue_status: status }, apiKey);
      toast.success(`Status → ${status}`);
      loadDrafts();
      if (selected?.id === id) setSelected({ ...selected, queue_status: status });
    } catch { toast.error("Status update failed"); }
  }

  // ── Editor view ──────────────────────────────────────────────────────────
  if (selected) {
    const wordCount = editBody.trim().split(/\s+/).filter(Boolean).length;
    return (
      <div className="animate-fade-in">
        {/* Editor toolbar */}
        <div className="flex items-center justify-between mb-5">
          <button onClick={() => setSelected(null)} className="btn-ghost flex items-center gap-1.5 text-sm">
            <ArrowLeft className="w-3.5 h-3.5" /> All drafts
          </button>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">{wordCount.toLocaleString("en-IN")} words</span>
            <select
              value={selected.queue_status}
              onChange={e => handleStatusChange(selected.id, e.target.value)}
              className="input-field text-xs py-1.5 w-28"
            >
              {["draft", "review", "approved", "published"].map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <button
              onClick={handleAiRewrite}
              disabled={rewriting}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              {rewriting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
              {rewriting ? "Rewriting…" : "AI Rewrite"}
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>

        {/* Meta */}
        <div className="card p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Title</label>
              <input
                type="text"
                value={selected.title}
                onChange={e => setSelected({ ...selected, title: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="label">Target Keyword</label>
              <input
                type="text"
                value={selected.target_keyword || ""}
                onChange={e => setSelected({ ...selected, target_keyword: e.target.value })}
                className="input-field"
                placeholder="e.g. seo tools india"
              />
            </div>
          </div>
        </div>

        {/* Markdown editor */}
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900/40">
            <span className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Markdown Editor</span>
            {selected.target_keyword && (
              <span className="text-xs text-zinc-600">
                Keyword density: {editBody.toLowerCase().split(selected.target_keyword.toLowerCase()).length - 1} occurrences
              </span>
            )}
          </div>
          <textarea
            value={editBody}
            onChange={e => setEditBody(e.target.value)}
            className="w-full bg-transparent p-4 font-mono text-sm text-zinc-200 resize-none outline-none leading-relaxed"
            style={{ minHeight: "60vh" }}
            placeholder="Start writing Markdown content here…"
          />
        </div>
      </div>
    );
  }

  // ── List view ──────────────────────────────────────────────────────────────
  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Content Studio"
        subtitle="AI-written SEO drafts with Claude Sonnet, Markdown editor, and a publish queue."
        icon={FileText}
        accent="#818CF8"
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <Select
              icon={FolderOpen}
              accent="#818CF8"
              placeholder="Select a project…"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              options={projects.map((p) => ({ value: p.id, label: p.name }))}
              widthClass="min-w-[220px]"
            />
            {projectId && (
              <>
                <button onClick={loadDrafts} disabled={loading} className="btn-ghost flex items-center gap-1.5 text-sm px-3 py-2.5">
                  <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
                </button>
                <button onClick={() => setShowCreate(!showCreate)} className="btn-primary flex items-center gap-2 text-sm">
                  <Plus className="w-3.5 h-3.5" /> New Draft
                </button>
              </>
            )}
          </div>
        }
      />

      {/* Create form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="card p-5 mb-6 border-brand-500/20 animate-fade-in space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">New content draft</h3>
            <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost p-1">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Title</label>
              <input
                type="text"
                className="input-field"
                placeholder="Best SEO Tools in India 2025"
                value={newDraft.title}
                onChange={e => setNewDraft({ ...newDraft, title: e.target.value })}
                required
                autoFocus
              />
            </div>
            <div>
              <label className="label">Target Keyword</label>
              <input
                type="text"
                className="input-field"
                placeholder={businessProfile?.keywords[0] || "seo tools india"}
                value={newDraft.target_keyword}
                onChange={e => setNewDraft({ ...newDraft, target_keyword: e.target.value })}
                required
              />
            </div>
          </div>
          {/* Profile keyword chips */}
          {businessProfile && businessProfile.keywords.length > 0 && (
            <div>
              <p className="text-xs text-zinc-500 mb-1.5">Quick fill from your keywords:</p>
              <div className="flex flex-wrap gap-1.5">
                {businessProfile.keywords.map(kw => (
                  <button
                    key={kw}
                    type="button"
                    onClick={() => setNewDraft({ ...newDraft, target_keyword: kw, title: newDraft.title || `Best ${kw} Guide` })}
                    className="text-xs bg-zinc-800/60 border border-zinc-700/40 text-zinc-400 rounded-full px-2.5 py-1 hover:bg-brand-600/20 hover:border-brand-500/30 hover:text-brand-300 transition-all"
                  >
                    {kw}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary text-sm">Cancel</button>
            <button type="submit" disabled={creating} className="btn-primary text-sm flex items-center gap-2">
              {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              {creating ? "Creating…" : "Create Draft"}
            </button>
          </div>
        </form>
      )}

      {/* Drafts list */}
      {loading ? (
        <div className="card p-12 text-center">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-500 mx-auto mb-2" />
          <p className="text-sm text-zinc-500">Loading drafts…</p>
        </div>
      ) : drafts.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
          <p className="text-sm text-zinc-400 mb-5">
            {projectId ? "No content drafts yet." : "Select a project to view drafts."}
          </p>
          {projectId && (
            <button onClick={() => setShowCreate(true)} className="btn-primary text-sm inline-flex items-center gap-2">
              <Plus className="w-4 h-4" /> Create first draft
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {drafts.map(d => {
            const words = (d.body_markdown || "").trim().split(/\s+/).filter(Boolean).length;
            return (
              <button
                key={d.id}
                onClick={() => openDraft(d)}
                className="card-hover p-5 flex items-center gap-4 w-full text-left group"
              >
                <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm truncate">{d.title}</h3>
                  <div className="flex items-center gap-3 mt-0.5">
                    {d.target_keyword && (
                      <span className="text-xs text-zinc-500">🔑 {d.target_keyword}</span>
                    )}
                    <span className="text-xs text-zinc-600">{words.toLocaleString("en-IN")} words</span>
                    <span className="text-xs text-zinc-600">
                      {new Date(d.updated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className={cn("badge text-[10px]", STATUS_COLORS[d.queue_status] || STATUS_COLORS.draft)}>
                    {d.queue_status}
                  </span>
                  {d.publish_target && (
                    <span className="text-xs text-zinc-600 hidden md:block">{d.publish_target}</span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
