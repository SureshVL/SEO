"use client";

import { useEffect, useState } from "react";
import {
  ExternalLink, GitBranch, GitPullRequest, Loader2, Plus, Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

interface GitConnection {
  id: string;
  repo_owner: string;
  repo_name: string;
  base_branch: string;
  verified: boolean;
  enabled: boolean;
}

interface FixPR {
  id: number;
  pr_number: number;
  pr_url: string;
  title: string;
  fix_type: string;
  status: string;
  created_at: string;
}

const FIX_TYPES = ["content", "schema", "meta", "redirects", "hreflang", "other"];

export default function GitWritebackPage() {
  const { apiKey } = useAppStore();
  const [tab, setTab] = useState<"repos" | "prs">("repos");
  const [connections, setConnections] = useState<GitConnection[]>([]);
  const [prs, setPrs] = useState<FixPR[]>([]);
  const [loading, setLoading] = useState(false);
  const [showConnect, setShowConnect] = useState(false);
  const [showPR, setShowPR] = useState(false);

  const [connectForm, setConnectForm] = useState({
    repo_owner: "", repo_name: "", base_branch: "", access_token: "",
  });
  const [prForm, setPrForm] = useState({
    connection_id: "", title: "", description: "", fix_type: "content",
    path: "", content: "",
  });

  const fetchConnections = async () => {
    try {
      const res = await apiFetch(`/git/connections`);
      if (res.ok) setConnections((await res.json()).connections || []);
    } catch (e) { console.error(e); }
  };

  const fetchPrs = async () => {
    try {
      const res = await apiFetch(`/git/prs`);
      if (res.ok) setPrs((await res.json()).pull_requests || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchConnections();
    fetchPrs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await apiFetch(`/git/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(connectForm),
      });
      if (res.ok) {
        toast.success("Repository connected and verified");
        setConnectForm({ repo_owner: "", repo_name: "", base_branch: "", access_token: "" });
        setShowConnect(false);
        fetchConnections();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Failed to connect repository");
      }
    } catch { toast.error("Failed to connect repository"); }
    finally { setLoading(false); }
  };

  const handleOpenPR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prForm.connection_id || !prForm.title || !prForm.path) {
      toast.error("Repo, title, and file path are required");
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch(`/git/pr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          connection_id: prForm.connection_id,
          title: prForm.title,
          description: prForm.description,
          fix_type: prForm.fix_type,
          files: [{ path: prForm.path, content: prForm.content }],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(`Pull request #${data.pr_number} opened`);
        setShowPR(false);
        setPrForm({ ...prForm, title: "", description: "", path: "", content: "" });
        fetchPrs();
        setTab("prs");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Failed to open PR");
      }
    } catch { toast.error("Failed to open PR"); }
    finally { setLoading(false); }
  };

  const deleteConnection = async (id: string) => {
    await apiFetch(`/git/connections/${id}`, { method: "DELETE" });
    toast.success("Repository disconnected");
    fetchConnections();
  };

  const statusColor = (s: string) =>
    s === "merged" ? "bg-purple-100 text-purple-800"
    : s === "closed" ? "bg-gray-100 text-gray-600"
    : "bg-green-100 text-green-800";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Git Write-back"
        description="Ship SEO fixes as pull requests — for headless, JAMstack and static sites"
        icon={GitPullRequest}
        accent="#6366F1"
      />

      <div className="flex gap-2 border-b">
        {[
          { id: "repos", label: `Repositories (${connections.length})` },
          { id: "prs", label: `Pull Requests (${prs.length})` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as any)}
            className={cn(
              "px-4 py-2 font-medium text-sm border-b-2 transition-colors",
              tab === t.id ? "border-indigo-500 text-indigo-600" : "border-transparent text-gray-600 hover:text-gray-900",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "repos" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowConnect(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
            >
              <Plus className="w-4 h-4" /> Connect Repository
            </button>
          </div>

          {connections.length === 0 ? (
            <div className="bg-white rounded-lg border p-12 text-center">
              <GitBranch className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600 font-medium">No repositories connected</p>
              <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
                Connect a GitHub repo with a fine-grained token (Contents + Pull requests, read/write)
                and OMNI-RANK will ship fixes as reviewable pull requests.
              </p>
            </div>
          ) : (
            connections.map((c) => (
              <div key={c.id} className="bg-white rounded-lg border p-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <GitBranch className="w-5 h-5 text-indigo-600" />
                  <div>
                    <p className="font-semibold text-gray-900">{c.repo_owner}/{c.repo_name}</p>
                    <p className="text-xs text-gray-500">base: {c.base_branch}</p>
                  </div>
                  {c.verified && (
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">Verified</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { setPrForm({ ...prForm, connection_id: c.id }); setShowPR(true); }}
                    className="text-sm px-3 py-1.5 border rounded-lg hover:bg-gray-50 transition flex items-center gap-1.5"
                  >
                    <GitPullRequest className="w-4 h-4" /> Open fix PR
                  </button>
                  <button onClick={() => deleteConnection(c.id)} className="p-1.5 text-gray-400 hover:text-red-500 transition">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "prs" && (
        <div className="space-y-3">
          {prs.length === 0 ? (
            <div className="bg-white rounded-lg border p-12 text-center">
              <GitPullRequest className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No fix pull requests yet</p>
            </div>
          ) : (
            prs.map((pr) => (
              <div key={pr.id} className="bg-white rounded-lg border p-4 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", statusColor(pr.status))}>
                      {pr.status}
                    </span>
                    <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full">{pr.fix_type}</span>
                    <span className="font-semibold text-gray-900 truncate">#{pr.pr_number} {pr.title}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{new Date(pr.created_at).toLocaleString()}</p>
                </div>
                {pr.pr_url && (
                  <a
                    href={pr.pr_url} target="_blank" rel="noreferrer"
                    className="shrink-0 flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-700"
                  >
                    View <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {showConnect && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-1">Connect GitHub Repository</h3>
            <p className="text-xs text-gray-500 mb-4">
              Use a fine-grained personal access token with Contents and Pull requests read/write on this repo.
            </p>
            <form onSubmit={handleConnect} className="space-y-3">
              <input type="text" placeholder="Owner (user or org)" value={connectForm.repo_owner}
                onChange={(e) => setConnectForm({ ...connectForm, repo_owner: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <input type="text" placeholder="Repository name" value={connectForm.repo_name}
                onChange={(e) => setConnectForm({ ...connectForm, repo_name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <input type="text" placeholder="Base branch (default: repo default)" value={connectForm.base_branch}
                onChange={(e) => setConnectForm({ ...connectForm, base_branch: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <input type="password" placeholder="GitHub access token" value={connectForm.access_token}
                onChange={(e) => setConnectForm({ ...connectForm, access_token: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <div className="flex gap-3">
                <button type="submit" disabled={loading}
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Connect & verify"}
                </button>
                <button type="button" onClick={() => setShowConnect(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showPR && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[85vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">Open Fix Pull Request</h3>
            <form onSubmit={handleOpenPR} className="space-y-3">
              <select value={prForm.connection_id}
                onChange={(e) => setPrForm({ ...prForm, connection_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="">Select repository</option>
                {connections.map((c) => (
                  <option key={c.id} value={c.id}>{c.repo_owner}/{c.repo_name}</option>
                ))}
              </select>
              <input type="text" placeholder="PR title (e.g. Add Organization schema)" value={prForm.title}
                onChange={(e) => setPrForm({ ...prForm, title: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <textarea placeholder="What this fix does and why" value={prForm.description}
                onChange={(e) => setPrForm({ ...prForm, description: e.target.value })}
                className="w-full h-20 px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <select value={prForm.fix_type}
                onChange={(e) => setPrForm({ ...prForm, fix_type: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {FIX_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <input type="text" placeholder="File path (e.g. content/blog/new-post.md)" value={prForm.path}
                onChange={(e) => setPrForm({ ...prForm, path: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <textarea placeholder="File content" value={prForm.content}
                onChange={(e) => setPrForm({ ...prForm, content: e.target.value })}
                className="w-full h-40 px-3 py-2 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              <div className="flex gap-3">
                <button type="submit" disabled={loading}
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition">
                  {loading ? "Opening PR..." : "Open pull request"}
                </button>
                <button type="button" onClick={() => setShowPR(false)}
                  className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
