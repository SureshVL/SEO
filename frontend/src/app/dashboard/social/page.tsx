"use client";

import { useCallback, useEffect, useState } from "react";
import { Share2, Loader2, Sparkles, Copy, CalendarPlus, Check, RotateCcw, Trash2, Send, Pencil } from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  generateSocialPosts, listSocialPosts, createSocialPost, updateSocialPost,
  approveSocialPost, requestSocialRevision, deleteSocialPost,
  type SocialGenerateResult, type SocialPlatform, type SocialPost,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const PLATFORMS: { id: SocialPlatform; label: string }[] = [
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "youtube", label: "YouTube" },
  { id: "linkedin", label: "LinkedIn" },
];

const GOALS = ["educational", "promotional", "engagement", "brand_awareness"];
const TONES = ["friendly", "professional", "playful", "bold", "inspirational"];

const statusStyle: Record<string, string> = {
  draft: "text-zinc-300 bg-zinc-500/10",
  pending_approval: "text-amber-300 bg-amber-500/10",
  revision_requested: "text-rose-300 bg-rose-500/10",
  approved: "text-emerald-300 bg-emerald-500/10",
  scheduled: "text-sky-300 bg-sky-500/10",
  published: "text-violet-300 bg-violet-500/10",
};

export default function SocialStudioPage() {
  const { apiKey, currentProject } = useAppStore();
  const projectId = currentProject?.id as string | undefined;

  // Generator state
  const [topic, setTopic] = useState("");
  const [context, setContext] = useState("");
  const [tone, setTone] = useState("friendly");
  const [goal, setGoal] = useState("engagement");
  const [selected, setSelected] = useState<SocialPlatform[]>(["instagram", "facebook", "linkedin"]);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<SocialGenerateResult | null>(null);

  // Calendar state
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCaption, setEditCaption] = useState("");

  const loadPosts = useCallback(async () => {
    if (!projectId) return;
    setLoadingPosts(true);
    try {
      setPosts(await listSocialPosts(projectId, apiKey));
    } catch {
      /* table may not exist yet in dev — keep the page usable */
    } finally {
      setLoadingPosts(false);
    }
  }, [projectId, apiKey]);

  useEffect(() => { loadPosts(); }, [loadPosts]);

  function togglePlatform(p: SocialPlatform) {
    setSelected(s => (s.includes(p) ? s.filter(x => x !== p) : [...s, p]));
  }

  async function generate() {
    if (!topic.trim()) { toast.error("Enter a topic first."); return; }
    if (selected.length === 0) { toast.error("Pick at least one platform."); return; }
    setGenerating(true);
    setResult(null);
    try {
      const data = await generateSocialPosts(
        { topic: topic.trim(), platforms: selected, tone, business_context: context.trim(), content_goal: goal },
        apiKey,
      );
      setResult(data);
      toast.success("Content generated — review below.");
    } catch (err: any) {
      toast.error(err?.message || "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function addToCalendar(platform: string) {
    const block = result?.platforms[platform];
    if (!block || block.error || !projectId) {
      if (!projectId) toast.error("Select a project first (top of sidebar).");
      return;
    }
    try {
      await createSocialPost(projectId, {
        platform: platform as SocialPlatform,
        topic: result!.topic,
        caption: block.caption,
        hashtags: block.hashtags,
        content_goal: result!.content_goal,
      }, apiKey);
      toast.success(`${platform} post added to calendar as draft`);
      loadPosts();
    } catch (err: any) {
      toast.error(err?.message || "Could not save post — did you run the social_posts migration?");
    }
  }

  async function act(fn: () => Promise<unknown>, okMsg: string) {
    try { await fn(); toast.success(okMsg); loadPosts(); }
    catch (err: any) { toast.error(err?.message || "Action failed"); }
  }

  function onRequestRevision(post: SocialPost) {
    const note = window.prompt(`Revision note (round ${post.revision_count + 1} of 2):`);
    if (!note) return;
    act(() => requestSocialRevision(post.id, note, apiKey), "Revision requested");
  }

  async function saveEdit(post: SocialPost) {
    await act(
      () => updateSocialPost(post.id, { caption: editCaption, status: "pending_approval" }, apiKey),
      "Caption updated — sent back for approval",
    );
    setEditingId(null);
  }

  function copyText(block: { caption: string; hashtags: string[] }) {
    navigator.clipboard.writeText(`${block.caption}\n\n${block.hashtags.join(" ")}`);
    toast.success("Copied caption + hashtags");
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Social Studio"
        subtitle="AI captions and hashtags per platform, a social content calendar, and a client approval flow with two revision rounds."
        icon={Share2}
        accent="#E1306C"
      />

      {/* ── Generator ── */}
      <div className="card p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Topic / announcement</span>
            <input value={topic} onChange={e => setTopic(e.target.value)}
              placeholder="Diwali offer: 20% off teeth whitening this week"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-pink-500/50" />
          </label>
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Business context (optional)</span>
            <input value={context} onChange={e => setContext(e.target.value)}
              placeholder="Dental clinic in Chennai, family-focused, WhatsApp bookings"
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-pink-500/50" />
          </label>
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Tone</span>
            <select value={tone} onChange={e => setTone(e.target.value)}
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none">
              {TONES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Content goal</span>
            <select value={goal} onChange={e => setGoal(e.target.value)}
              className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none">
              {GOALS.map(g => <option key={g} value={g}>{g.replace("_", " ")}</option>)}
            </select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {PLATFORMS.map(p => (
            <button key={p.id} onClick={() => togglePlatform(p.id)}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-semibold border transition",
                selected.includes(p.id)
                  ? "bg-pink-500/20 border-pink-500/50 text-pink-200"
                  : "bg-zinc-800/50 border-zinc-700 text-zinc-400 hover:border-zinc-500",
              )}>
              {p.label}
            </button>
          ))}
        </div>

        <button onClick={generate} disabled={generating} className="btn-primary mt-5 flex items-center gap-2 px-6 h-[42px]">
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {generating ? "Writing platform-native copy…" : "Generate captions & hashtags"}
        </button>
      </div>

      {/* ── Generated results ── */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          {Object.entries(result.platforms).map(([platform, block]) => (
            <div key={platform} className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-bold uppercase tracking-wider text-pink-300">{platform}</span>
                {!block.error && (
                  <div className="flex gap-2">
                    <button onClick={() => copyText(block)} title="Copy caption + hashtags"
                      className="p-1.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-700 text-zinc-300"><Copy className="w-3.5 h-3.5" /></button>
                    <button onClick={() => addToCalendar(platform)} title="Add to calendar as draft"
                      className="p-1.5 rounded-lg bg-pink-500/20 hover:bg-pink-500/30 text-pink-200"><CalendarPlus className="w-3.5 h-3.5" /></button>
                  </div>
                )}
              </div>
              {block.error ? (
                <p className="text-sm text-rose-300">{block.error}</p>
              ) : (
                <>
                  <p className="text-sm text-zinc-200 whitespace-pre-wrap">{block.caption}</p>
                  <p className="text-xs text-sky-300 mt-3">{block.hashtags.join(" ")}</p>
                  {block.best_time_hint && (
                    <p className="text-[11px] text-zinc-500 mt-2">Best time: {block.best_time_hint}</p>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Calendar / approval queue ── */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-zinc-100">Content calendar &amp; approvals</h3>
          {loadingPosts && <Loader2 className="w-4 h-4 animate-spin text-zinc-500" />}
        </div>

        {!projectId ? (
          <p className="text-sm text-zinc-500">Select a project to see its social calendar.</p>
        ) : posts.length === 0 && !loadingPosts ? (
          <p className="text-sm text-zinc-500">No posts yet — generate content above and add it to the calendar.</p>
        ) : (
          <div className="space-y-3">
            {posts.map(post => (
              <div key={post.id} className="border border-zinc-800 rounded-lg p-4">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-pink-300">{post.platform}</span>
                  <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase", statusStyle[post.status])}>
                    {post.status.replace("_", " ")}
                  </span>
                  <span className="text-[11px] text-zinc-500">
                    revisions {post.revision_count}/2
                    {post.scheduled_date ? ` · scheduled ${new Date(post.scheduled_date).toLocaleDateString()}` : ""}
                  </span>
                  <div className="ml-auto flex gap-1.5">
                    {post.status === "draft" && (
                      <button onClick={() => act(() => updateSocialPost(post.id, { status: "pending_approval" }, apiKey), "Sent for client approval")}
                        title="Send for approval" className="p-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-200"><Send className="w-3.5 h-3.5" /></button>
                    )}
                    {post.status === "pending_approval" && (
                      <>
                        <button onClick={() => act(() => approveSocialPost(post.id, apiKey), "Approved")}
                          title="Approve" className="p-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-200"><Check className="w-3.5 h-3.5" /></button>
                        <button onClick={() => onRequestRevision(post)}
                          title="Request revision" className="p-1.5 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-200"><RotateCcw className="w-3.5 h-3.5" /></button>
                      </>
                    )}
                    {post.status === "revision_requested" && (
                      <button onClick={() => { setEditingId(post.id); setEditCaption(post.caption); }}
                        title="Edit caption" className="p-1.5 rounded-lg bg-sky-500/15 hover:bg-sky-500/25 text-sky-200"><Pencil className="w-3.5 h-3.5" /></button>
                    )}
                    {post.status === "approved" && (
                      <button onClick={() => act(() => updateSocialPost(post.id, { status: "published" }, apiKey), "Marked as published")}
                        title="Mark published" className="p-1.5 rounded-lg bg-violet-500/15 hover:bg-violet-500/25 text-violet-200"><Check className="w-3.5 h-3.5" /></button>
                    )}
                    <button onClick={() => act(() => deleteSocialPost(post.id, apiKey), "Deleted")}
                      title="Delete" className="p-1.5 rounded-lg bg-zinc-800/60 hover:bg-zinc-700 text-zinc-400"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>

                {editingId === post.id ? (
                  <div>
                    <textarea value={editCaption} onChange={e => setEditCaption(e.target.value)} rows={4}
                      className="w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-sky-500/50" />
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => saveEdit(post)} className="btn-primary px-4 h-8 text-xs">Save &amp; resubmit</button>
                      <button onClick={() => setEditingId(null)} className="px-4 h-8 text-xs text-zinc-400 hover:text-zinc-200">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="text-sm text-zinc-300 whitespace-pre-wrap line-clamp-3">{post.caption}</p>
                    {post.hashtags?.length > 0 && (
                      <p className="text-xs text-sky-300 mt-1.5">{post.hashtags.join(" ")}</p>
                    )}
                    {post.revision_notes?.length > 0 && (
                      <div className="mt-2 text-[11px] text-rose-300/80">
                        {post.revision_notes.map(n => <div key={n.round}>Round {n.round}: {n.note}</div>)}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
