"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2, Copy, Globe, Loader2, Plus, Rocket, ShieldCheck, Trash2, XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/PageHeader";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface EdgeSite {
  id: string;
  domain: string;
  site_token: string;
  enabled: boolean;
  verified: boolean;
  last_seen_at: string | null;
}

interface EdgeRule {
  id: number;
  site_id: string;
  url_pattern: string;
  match_type: string;
  rule_type: string;
  payload: any;
  enabled: boolean;
  source: string;
}

const RULE_TYPES = [
  { id: "schema", label: "Schema (JSON-LD)", hint: "Structured data for rich results" },
  { id: "title", label: "Page Title", hint: "Overrides the <title> tag" },
  { id: "meta_description", label: "Meta Description", hint: "Sets meta[name=description]" },
  { id: "canonical", label: "Canonical URL", hint: "Sets link[rel=canonical]" },
  { id: "hreflang", label: "Hreflang Links", hint: "Language alternate links" },
  { id: "meta", label: "Custom Meta", hint: "Any meta name/content pair" },
];

export default function EdgeDeployPage() {
  const { apiKey } = useAppStore();
  const [tab, setTab] = useState<"install" | "rules">("install");
  const [sites, setSites] = useState<EdgeSite[]>([]);
  const [rules, setRules] = useState<EdgeRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [showAddSite, setShowAddSite] = useState(false);
  const [showAddRule, setShowAddRule] = useState(false);
  const [newDomain, setNewDomain] = useState("");
  const [ruleForm, setRuleForm] = useState({
    site_id: "",
    url_pattern: "*",
    match_type: "all",
    rule_type: "meta_description",
    value: "",
    jsonld: "",
    metaName: "",
  });

  const fetchSites = async () => {
    try {
      const res = await apiFetch(`/edge/sites`);
      if (res.ok) {
        const data = await res.json();
        setSites(data.sites || []);
      }
    } catch (e) { console.error(e); }
  };

  const fetchRules = async () => {
    try {
      const res = await apiFetch(`/edge/rules`);
      if (res.ok) {
        const data = await res.json();
        setRules(data.rules || []);
      }
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    fetchSites();
    fetchRules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  const snippetFor = (site: EdgeSite) =>
    `<script src="${API}/edge/v1/omnirank.js" data-site="${site.site_token}" async></script>`;

  const handleAddSite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDomain.trim()) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/edge/sites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain: newDomain.trim() }),
      });
      if (res.ok) {
        toast.success("Site added — copy the snippet into its <head>");
        setNewDomain("");
        setShowAddSite(false);
        fetchSites();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Failed to add site");
      }
    } catch { toast.error("Failed to add site"); }
    finally { setLoading(false); }
  };

  const handleVerify = async (site: EdgeSite) => {
    setVerifying(site.id);
    try {
      const res = await apiFetch(`/edge/sites/${site.id}/verify`, { method: "POST" });
      const data = await res.json();
      if (data.verified) {
        toast.success("Snippet detected — site verified!");
        fetchSites();
      } else {
        toast.error(data.error || "Snippet not found on the homepage yet");
      }
    } catch { toast.error("Verification failed"); }
    finally { setVerifying(null); }
  };

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleForm.site_id) { toast.error("Pick a site"); return; }
    let payload: any = {};
    if (ruleForm.rule_type === "schema") {
      try { payload = { jsonld: JSON.parse(ruleForm.jsonld) }; }
      catch { toast.error("Schema must be valid JSON"); return; }
    } else if (ruleForm.rule_type === "canonical") {
      payload = { href: ruleForm.value };
    } else if (ruleForm.rule_type === "hreflang") {
      try { payload = { links: JSON.parse(ruleForm.jsonld) }; }
      catch { toast.error('Hreflang must be JSON like [{"hreflang":"es","href":"https://..."}]'); return; }
    } else if (ruleForm.rule_type === "meta") {
      payload = { name: ruleForm.metaName, content: ruleForm.value };
    } else {
      payload = { value: ruleForm.value };
    }

    setLoading(true);
    try {
      const res = await apiFetch(`/edge/rules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_id: ruleForm.site_id,
          url_pattern: ruleForm.url_pattern || "*",
          match_type: ruleForm.match_type,
          rule_type: ruleForm.rule_type,
          payload,
        }),
      });
      if (res.ok) {
        toast.success("Rule deployed — live on next pageview");
        setShowAddRule(false);
        setRuleForm({ ...ruleForm, value: "", jsonld: "", metaName: "" });
        fetchRules();
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Failed to create rule");
      }
    } catch { toast.error("Failed to create rule"); }
    finally { setLoading(false); }
  };

  const toggleRule = async (rule: EdgeRule) => {
    await apiFetch(`/edge/rules/${rule.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !rule.enabled }),
    });
    fetchRules();
  };

  const deleteRule = async (rule: EdgeRule) => {
    await apiFetch(`/edge/rules/${rule.id}`, { method: "DELETE" });
    toast.success("Rule removed");
    fetchRules();
  };

  const siteDomain = (id: string) => sites.find((s) => s.id === id)?.domain || id;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edge Deploy"
        description="Push SEO fixes to ANY website — custom builds, e-commerce, legacy stacks — via one script tag"
        icon={Rocket}
        accent="#14B8A6"
      />

      <div className="flex gap-2 border-b">
        {[
          { id: "install", label: "Install & Verify" },
          { id: "rules", label: `Rules (${rules.length})` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as any)}
            className={cn(
              "px-4 py-2 font-medium text-sm border-b-2 transition-colors",
              tab === t.id ? "border-teal-500 text-teal-600" : "border-transparent text-gray-600 hover:text-gray-900",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "install" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowAddSite(true)}
              className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition"
            >
              <Plus className="w-4 h-4" /> Add Website
            </button>
          </div>

          {sites.length === 0 ? (
            <div className="bg-white rounded-lg border p-12 text-center">
              <Globe className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600 font-medium">Deploy SEO fixes to any website</p>
              <p className="text-sm text-gray-500 mt-1 max-w-md mx-auto">
                Add a website, paste one script tag into its &lt;head&gt;, and OMNI-RANK can inject
                schema, titles, meta descriptions, canonicals and hreflang — no CMS or developer needed.
              </p>
            </div>
          ) : (
            sites.map((site) => (
              <div key={site.id} className="bg-white rounded-lg border p-5 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <Globe className="w-5 h-5 text-teal-600" />
                    <span className="font-semibold text-gray-900">{site.domain}</span>
                    {site.verified ? (
                      <span className="flex items-center gap-1 text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                        <CheckCircle2 className="w-3 h-3" /> Verified
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                        <XCircle className="w-3 h-3" /> Not verified
                      </span>
                    )}
                    {site.last_seen_at && (
                      <span className="text-xs text-gray-500">
                        Active {new Date(site.last_seen_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleVerify(site)}
                    disabled={verifying === site.id}
                    className="flex items-center gap-2 text-sm px-3 py-1.5 border rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
                  >
                    {verifying === site.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                    Verify install
                  </button>
                </div>
                <div className="bg-gray-900 text-gray-100 rounded-lg p-3 font-mono text-xs overflow-x-auto flex items-center justify-between gap-3">
                  <code className="whitespace-nowrap">{snippetFor(site)}</code>
                  <button
                    onClick={() => { navigator.clipboard.writeText(snippetFor(site)); toast.success("Snippet copied"); }}
                    className="shrink-0 p-1.5 rounded hover:bg-white/10 transition"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
                <p className="text-xs text-gray-500">
                  Paste inside &lt;head&gt;. Works on any stack: custom builds, Magento, Salesforce Commerce, legacy CMS.
                </p>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "rules" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowAddRule(true)}
              disabled={sites.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition disabled:opacity-50"
            >
              <Plus className="w-4 h-4" /> Deploy Rule
            </button>
          </div>

          {rules.length === 0 ? (
            <div className="bg-white rounded-lg border p-12 text-center">
              <Rocket className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No rules deployed yet</p>
            </div>
          ) : (
            rules.map((rule) => (
              <div key={rule.id} className="bg-white rounded-lg border p-4 flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold bg-teal-100 text-teal-800 px-2 py-0.5 rounded-full">
                      {rule.rule_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-gray-500">{siteDomain(rule.site_id)}</span>
                    <span className="text-xs text-gray-400">
                      {rule.match_type === "all" ? "all pages" : `${rule.match_type}: ${rule.url_pattern}`}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mt-1 font-mono truncate">
                    {typeof rule.payload === "string" ? rule.payload : JSON.stringify(rule.payload)}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => toggleRule(rule)}
                    className={cn(
                      "text-xs px-3 py-1.5 rounded-full font-medium transition",
                      rule.enabled ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500",
                    )}
                  >
                    {rule.enabled ? "Live" : "Paused"}
                  </button>
                  <button onClick={() => deleteRule(rule)} className="p-1.5 text-gray-400 hover:text-red-500 transition">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showAddSite && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Add Website</h3>
            <form onSubmit={handleAddSite} className="space-y-4">
              <input
                type="text"
                placeholder="client-website.com"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
              <div className="flex gap-3">
                <button type="submit" disabled={loading} className="flex-1 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 transition">
                  {loading ? "Adding..." : "Add & get snippet"}
                </button>
                <button type="button" onClick={() => setShowAddSite(false)} className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAddRule && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 max-h-[85vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">Deploy Rule</h3>
            <form onSubmit={handleAddRule} className="space-y-4">
              <select
                value={ruleForm.site_id}
                onChange={(e) => setRuleForm({ ...ruleForm, site_id: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                <option value="">Select website</option>
                {sites.map((s) => <option key={s.id} value={s.id}>{s.domain}</option>)}
              </select>

              <select
                value={ruleForm.rule_type}
                onChange={(e) => setRuleForm({ ...ruleForm, rule_type: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                {RULE_TYPES.map((r) => <option key={r.id} value={r.id}>{r.label} — {r.hint}</option>)}
              </select>

              <div className="grid grid-cols-2 gap-3">
                <select
                  value={ruleForm.match_type}
                  onChange={(e) => setRuleForm({ ...ruleForm, match_type: e.target.value })}
                  className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="all">All pages</option>
                  <option value="exact">Exact path</option>
                  <option value="prefix">Path prefix</option>
                  <option value="contains">Path contains</option>
                </select>
                <input
                  type="text"
                  placeholder="/products/widget"
                  value={ruleForm.url_pattern}
                  onChange={(e) => setRuleForm({ ...ruleForm, url_pattern: e.target.value })}
                  disabled={ruleForm.match_type === "all"}
                  className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-gray-100"
                />
              </div>

              {ruleForm.rule_type === "meta" && (
                <input
                  type="text"
                  placeholder="meta name (e.g. robots)"
                  value={ruleForm.metaName}
                  onChange={(e) => setRuleForm({ ...ruleForm, metaName: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              )}

              {(ruleForm.rule_type === "schema" || ruleForm.rule_type === "hreflang") ? (
                <textarea
                  placeholder={ruleForm.rule_type === "schema"
                    ? '{"@context":"https://schema.org","@type":"Organization","name":"..."}'
                    : '[{"hreflang":"es","href":"https://example.com/es/"}]'}
                  value={ruleForm.jsonld}
                  onChange={(e) => setRuleForm({ ...ruleForm, jsonld: e.target.value })}
                  className="w-full h-32 px-3 py-2 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              ) : (
                <input
                  type="text"
                  placeholder={ruleForm.rule_type === "canonical" ? "https://example.com/page" : "Value"}
                  value={ruleForm.value}
                  onChange={(e) => setRuleForm({ ...ruleForm, value: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              )}

              <div className="flex gap-3">
                <button type="submit" disabled={loading} className="flex-1 px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 transition">
                  {loading ? "Deploying..." : "Deploy live"}
                </button>
                <button type="button" onClick={() => setShowAddRule(false)} className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
