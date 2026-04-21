"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Briefcase,
  Copy,
  ExternalLink,
  FolderOpen,
  Link2,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import {
  listProjects,
  listLinkProspects,
  createLinkProspect,
  updateLinkProspect,
  deleteLinkProspect,
  draftProspectEmail,
  fetchBacklinkProfile,
  type BacklinkProfile,
  type LinkProspect,
  type LinkProspectStatus,
  type OutreachEmailDraft,
} from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const STATUSES: LinkProspectStatus[] = [
  "new", "researching", "contacted", "replied", "agreed", "placed", "declined",
];

const STATUS_COLORS: Record<LinkProspectStatus, string> = {
  new: "bg-zinc-500/10 text-zinc-300 border-zinc-500/30",
  researching: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  contacted: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  replied: "bg-indigo-500/10 text-indigo-300 border-indigo-500/30",
  agreed: "bg-violet-500/10 text-violet-300 border-violet-500/30",
  placed: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  declined: "bg-rose-500/10 text-rose-300 border-rose-500/30",
};

export default function LinksPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState(businessProfile?.projectId || "");
  const [tab, setTab] = useState<"pipeline" | "backlinks">("pipeline");

  const [prospects, setProspects] = useState<LinkProspect[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<LinkProspectStatus | "">("");

  // New prospect form
  const [newDomain, setNewDomain] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [newContactName, setNewContactName] = useState("");
  const [newContactEmail, setNewContactEmail] = useState("");
  const [newDr, setNewDr] = useState("");
  const [creating, setCreating] = useState(false);

  // Draft-email state
  const [drafting, setDrafting] = useState<string | null>(null);
  const [draft, setDraft] = useState<OutreachEmailDraft | null>(null);
  const [draftProspect, setDraftProspect] = useState<LinkProspect | null>(null);
  const [draftTemplate, setDraftTemplate] = useState<
    "intro" | "broken_link" | "guest_post" | "resource_page"
  >("intro");
  const [senderName, setSenderName] = useState(businessProfile?.projectName || "");
  const [senderSite, setSenderSite] = useState(businessProfile?.websiteUrl || "");
  const [valueProp, setValueProp] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [brokenUrl, setBrokenUrl] = useState("");

  // Backlink profile state
  const [backlinkDomain, setBacklinkDomain] = useState(
    businessProfile?.websiteUrl?.replace(/^https?:\/\//, "") || "",
  );
  const [backlinkReport, setBacklinkReport] = useState<BacklinkProfile | null>(null);
  const [backlinkLoading, setBacklinkLoading] = useState(false);

  useEffect(() => {
    listProjects(apiKey).then(setProjects).catch(() => {});
  }, [apiKey]);
  useEffect(() => {
    if (businessProfile?.projectId && !projectId) setProjectId(businessProfile.projectId);
  }, [businessProfile]);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await listLinkProspects(projectId, apiKey, filter || undefined);
      setProspects(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load prospects");
    } finally {
      setLoading(false);
    }
  }, [projectId, apiKey, filter]);
  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    if (!projectId) {
      toast.error("Select a project first");
      return;
    }
    if (!newDomain.trim()) {
      toast.error("Domain is required");
      return;
    }
    setCreating(true);
    try {
      await createLinkProspect(
        projectId,
        {
          domain: newDomain.trim(),
          url: newUrl.trim(),
          contact_name: newContactName.trim(),
          contact_email: newContactEmail.trim(),
          domain_rating: newDr ? Number(newDr) : undefined,
        },
        apiKey,
      );
      toast.success(`Added ${newDomain}`);
      setNewDomain("");
      setNewUrl("");
      setNewContactName("");
      setNewContactEmail("");
      setNewDr("");
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to add prospect");
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(p: LinkProspect, status: LinkProspectStatus) {
    const updates: Partial<LinkProspect> = { status };
    const now = new Date().toISOString();
    if (status === "contacted" && !p.outreach_sent_at) updates.outreach_sent_at = now;
    if (status === "replied" && !p.response_at) updates.response_at = now;
    if (status === "placed" && !p.placed_at) updates.placed_at = now;
    try {
      await updateLinkProspect(p.id, updates, apiKey);
      await load();
    } catch (err: any) {
      toast.error(err.message || "Status update failed");
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this prospect?")) return;
    try {
      await deleteLinkProspect(id, apiKey);
      await load();
    } catch (err: any) {
      toast.error(err.message || "Delete failed");
    }
  }

  async function handleDraft(p: LinkProspect) {
    setDrafting(p.id);
    setDraftProspect(p);
    setDraft(null);
    try {
      const email = await draftProspectEmail(
        p.id,
        {
          campaign: {
            sender_name: senderName,
            sender_site: senderSite,
            value_prop: valueProp,
            target_url: targetUrl,
            broken_url: brokenUrl,
          },
          template: draftTemplate,
        },
        apiKey,
      );
      setDraft(email);
      await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to draft email");
    } finally {
      setDrafting(null);
    }
  }

  async function handleBacklinkProfile() {
    if (!backlinkDomain.trim()) {
      toast.error("Domain is required");
      return;
    }
    setBacklinkLoading(true);
    setBacklinkReport(null);
    try {
      const report = await fetchBacklinkProfile({ domain: backlinkDomain }, apiKey);
      setBacklinkReport(report);
      if (report.warnings.length) {
        report.warnings.forEach(w => toast.warning(w));
      }
    } catch (err: any) {
      toast.error(err.message || "Backlink lookup failed");
    } finally {
      setBacklinkLoading(false);
    }
  }

  function copyEmail() {
    if (!draft) return;
    const text = `Subject: ${draft.subject}\n\n${draft.body}`;
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  }

  async function addReferrerAsProspect(domain: string, rank: number) {
    if (!projectId) {
      toast.error("Select a project first");
      return;
    }
    try {
      await createLinkProspect(
        projectId,
        { domain, domain_rating: rank, already_linking: true, status: "researching" },
        apiKey,
      );
      toast.success(`Added ${domain}`);
      if (tab === "pipeline") await load();
    } catch (err: any) {
      toast.error(err.message || "Failed to add referrer");
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Link Building"
        subtitle="Track backlink prospects, draft personalised outreach, and monitor your live backlink profile via DataForSEO."
        icon={Link2}
        accent="#2DD4BF"
        actions={
          <Select
            icon={FolderOpen}
            accent="#2DD4BF"
            placeholder="Select a project…"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            options={projects.map((p) => ({ value: p.id, label: p.name }))}
            widthClass="min-w-[240px]"
          />
        }
      />

      {/* Tabs */}
      <div className="flex gap-2 mb-6" style={{ borderBottom: "1px solid var(--border)" }}>
        <TabButton active={tab === "pipeline"} onClick={() => setTab("pipeline")}>
          <Briefcase className="w-4 h-4" /> Outreach pipeline
        </TabButton>
        <TabButton active={tab === "backlinks"} onClick={() => setTab("backlinks")}>
          <Search className="w-4 h-4" /> Live backlinks
        </TabButton>
      </div>

      {tab === "pipeline" && (
        <div className="space-y-6">
          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200 flex items-center gap-2">
              <Plus className="w-4 h-4" /> Add prospect
            </h3>
            <div className="grid md:grid-cols-5 gap-2">
              <input
                placeholder="example.com"
                value={newDomain}
                onChange={e => setNewDomain(e.target.value)}
                className="input-field md:col-span-1"
              />
              <input
                placeholder="Target URL"
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
                className="input-field md:col-span-2"
              />
              <input
                placeholder="Contact name"
                value={newContactName}
                onChange={e => setNewContactName(e.target.value)}
                className="input-field"
              />
              <input
                placeholder="Email"
                value={newContactEmail}
                onChange={e => setNewContactEmail(e.target.value)}
                className="input-field"
              />
            </div>
            <div className="flex items-end gap-2 mt-2">
              <input
                placeholder="DR / domain rating"
                value={newDr}
                onChange={e => setNewDr(e.target.value)}
                className="input-field max-w-[200px]"
              />
              <button
                onClick={handleCreate}
                disabled={creating || !projectId}
                className="btn-primary flex items-center gap-2"
              >
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Add prospect
              </button>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-zinc-200">Prospects</h3>
              <div className="flex items-center gap-2">
                <select
                  value={filter}
                  onChange={e => setFilter(e.target.value as LinkProspectStatus)}
                  className="input-field py-1.5 text-sm"
                >
                  <option value="">All statuses</option>
                  {STATUSES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <button onClick={load} className="btn-ghost flex items-center gap-1.5 text-sm">
                  <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
                </button>
              </div>
            </div>

            {prospects.length === 0 ? (
              <div className="text-sm text-zinc-500">No prospects yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-zinc-500 border-b border-zinc-800">
                      <th className="py-2">Domain</th>
                      <th className="py-2">Contact</th>
                      <th className="py-2 text-right">DR</th>
                      <th className="py-2 text-right">Score</th>
                      <th className="py-2">Status</th>
                      <th className="py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prospects.map(p => (
                      <tr key={p.id} className="border-b border-zinc-800/50 align-top">
                        <td className="py-2 text-violet-300">
                          <div className="font-medium">{p.domain}</div>
                          {p.url && (
                            <a href={p.url} target="_blank" rel="noreferrer" className="text-zinc-500 underline inline-flex items-center gap-1">
                              {p.url.length > 40 ? p.url.slice(0, 40) + "…" : p.url}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </td>
                        <td className="py-2 text-zinc-300">
                          {p.contact_name || "—"}
                          {p.contact_email && (
                            <div className="text-zinc-500">{p.contact_email}</div>
                          )}
                        </td>
                        <td className="py-2 text-right text-zinc-300">
                          {p.domain_rating ?? "—"}
                        </td>
                        <td className="py-2 text-right text-emerald-300">
                          {p.opportunity_score?.toFixed(0) ?? "—"}
                        </td>
                        <td className="py-2">
                          <select
                            value={p.status}
                            onChange={e => handleStatusChange(p, e.target.value as LinkProspectStatus)}
                            className={cn(
                              "text-xs rounded px-2 py-1 border",
                              STATUS_COLORS[p.status],
                            )}
                          >
                            {STATUSES.map(s => (
                              <option key={s} value={s}>{s}</option>
                            ))}
                          </select>
                        </td>
                        <td className="py-2">
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDraft(p)}
                              disabled={drafting === p.id}
                              className="btn-ghost flex items-center gap-1 text-xs"
                              title="Draft outreach email"
                            >
                              {drafting === p.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Mail className="w-3.5 h-3.5" />
                              )}
                              Draft
                            </button>
                            <button
                              onClick={() => handleDelete(p.id)}
                              className="btn-ghost text-rose-400"
                              title="Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" /> Email campaign defaults
            </h3>
            <p className="text-xs text-zinc-500 mb-3">
              Applied to every new draft. Pick a template then hit <em>Draft</em> on any
              prospect to generate a personalised email.
            </p>
            <div className="grid md:grid-cols-4 gap-2">
              <input
                placeholder="Sender name"
                value={senderName}
                onChange={e => setSenderName(e.target.value)}
                className="input-field"
              />
              <input
                placeholder="Sender site"
                value={senderSite}
                onChange={e => setSenderSite(e.target.value)}
                className="input-field"
              />
              <input
                placeholder="Target URL to pitch"
                value={targetUrl}
                onChange={e => setTargetUrl(e.target.value)}
                className="input-field"
              />
              <select
                value={draftTemplate}
                onChange={e => setDraftTemplate(e.target.value as any)}
                className="input-field"
              >
                <option value="intro">Intro</option>
                <option value="broken_link">Broken link</option>
                <option value="guest_post">Guest post</option>
                <option value="resource_page">Resource page</option>
              </select>
            </div>
            <input
              placeholder="Value proposition (what's unique / why link)"
              value={valueProp}
              onChange={e => setValueProp(e.target.value)}
              className="input-field mt-2"
            />
            {draftTemplate === "broken_link" && (
              <input
                placeholder="Broken URL on their site"
                value={brokenUrl}
                onChange={e => setBrokenUrl(e.target.value)}
                className="input-field mt-2"
              />
            )}
          </div>

          {draft && draftProspect && (
            <div className="card p-6 border border-violet-500/30 bg-violet-500/5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-zinc-100">
                    Draft for {draftProspect.domain}
                  </h3>
                  <div className="text-xs text-zinc-500 mt-0.5">
                    Template: {draft.template}
                    {draft.fallback && " · (fallback, AI unavailable)"}
                    {draft.model_used && ` · ${draft.model_used}`}
                  </div>
                </div>
                <button onClick={copyEmail} className="btn-ghost flex items-center gap-1 text-xs">
                  <Copy className="w-3.5 h-3.5" /> Copy
                </button>
              </div>
              <div className="text-sm font-medium text-amber-200 mb-2">
                Subject: {draft.subject}
              </div>
              <pre className="text-sm text-zinc-200 whitespace-pre-wrap font-sans bg-zinc-900/50 border border-zinc-800 rounded p-3">
{draft.body}
              </pre>
            </div>
          )}
        </div>
      )}

      {tab === "backlinks" && (
        <div className="space-y-6">
          <div className="card p-6">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-1">
                  Domain
                </label>
                <input
                  placeholder="example.com"
                  value={backlinkDomain}
                  onChange={e => setBacklinkDomain(e.target.value)}
                  className="input-field"
                />
              </div>
              <button
                onClick={handleBacklinkProfile}
                disabled={backlinkLoading || !backlinkDomain}
                className="btn-primary flex items-center gap-2"
              >
                {backlinkLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Fetch profile
              </button>
            </div>
          </div>

          {backlinkReport && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Stat label="Total backlinks" value={backlinkReport.total_backlinks.toLocaleString()} />
                <Stat label="Referring domains" value={backlinkReport.referring_domains.toLocaleString()} />
                <Stat label="Domain rank" value={backlinkReport.domain_rank.toFixed(0)} />
                <Stat label="Dofollow %" value={`${backlinkReport.dofollow_ratio.toFixed(1)}%`} />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="card p-6">
                  <h3 className="font-semibold mb-3 text-zinc-200">Top anchors</h3>
                  {backlinkReport.top_anchors.length === 0 ? (
                    <div className="text-sm text-zinc-500">No anchor data.</div>
                  ) : (
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-zinc-500 border-b border-zinc-800">
                          <th className="py-2">Anchor</th>
                          <th className="py-2 text-right">Links</th>
                          <th className="py-2 text-right">Domains</th>
                        </tr>
                      </thead>
                      <tbody>
                        {backlinkReport.top_anchors.slice(0, 15).map((a, i) => (
                          <tr key={i} className="border-b border-zinc-800/50">
                            <td className="py-2 text-zinc-300 truncate max-w-[240px]">{a.anchor || "(empty)"}</td>
                            <td className="py-2 text-right text-zinc-300">{a.backlinks.toLocaleString()}</td>
                            <td className="py-2 text-right text-zinc-400">{a.referring_domains.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                <div className="card p-6">
                  <h3 className="font-semibold mb-3 text-zinc-200">Top referring domains</h3>
                  {backlinkReport.top_referring.length === 0 ? (
                    <div className="text-sm text-zinc-500">No referrer data.</div>
                  ) : (
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-zinc-500 border-b border-zinc-800">
                          <th className="py-2">Domain</th>
                          <th className="py-2 text-right">Rank</th>
                          <th className="py-2 text-right">Links</th>
                          <th className="py-2"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {backlinkReport.top_referring.slice(0, 15).map((r, i) => (
                          <tr key={i} className="border-b border-zinc-800/50">
                            <td className="py-2 text-violet-300">{r.domain}</td>
                            <td className="py-2 text-right text-zinc-300">{r.rank.toFixed(0)}</td>
                            <td className="py-2 text-right text-zinc-400">{r.backlinks.toLocaleString()}</td>
                            <td className="py-2 text-right">
                              <button
                                onClick={() => addReferrerAsProspect(r.domain, r.rank)}
                                className="text-xs text-emerald-400 hover:text-emerald-300"
                              >
                                + track
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "px-4 py-2 text-sm flex items-center gap-2 border-b-2 transition",
        active
          ? "border-violet-500 text-zinc-100"
          : "border-transparent text-zinc-500 hover:text-zinc-300",
      )}
    >
      {children}
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-zinc-800/30 rounded-lg p-4 border border-zinc-800">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1">{label}</div>
      <div className="text-2xl font-semibold font-serif text-zinc-100">{value}</div>
    </div>
  );
}
