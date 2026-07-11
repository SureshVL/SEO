"use client";

import { useEffect, useState } from "react";
import { Braces, Check, Copy, Loader2, Settings2, X, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { detectSchema, type SchemaDetectionResult } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { CMSCredentialsModal } from "@/components/ui/CMSCredentialsModal";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const BUSINESS_TYPE_OPTIONS = [
  { value: "default", label: "Default (any business)" },
  { value: "local_business", label: "Local Business" },
  { value: "restaurant", label: "Restaurant" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "saas", label: "SaaS" },
  { value: "publisher", label: "Publisher / Blog" },
  { value: "agency", label: "Agency / Services" },
];

const SCHEMA_TYPES = [
  "Organization", "LocalBusiness", "Restaurant", "WebSite", "BreadcrumbList",
  "Article", "BlogPosting", "FAQPage", "Product", "Service",
  "SoftwareApplication", "Menu",
];

export default function SchemaPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [tab, setTab] = useState<"detect" | "inject">("detect");

  // Detect tab state
  const [url, setUrl] = useState("");
  const [businessType, setBusinessType] = useState("default");
  const [businessName, setBusinessName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SchemaDetectionResult | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  // Inject tab state
  const [batchUrls, setBatchUrls] = useState("");
  const [selectedSchemas, setSelectedSchemas] = useState<string[]>(["FAQPage", "Organization"]);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResult, setBatchResult] = useState<any>(null);
  const [wordpressModal, setWordpressModal] = useState(false);
  const [wordpressStatus, setWordpressStatus] = useState<{ saved: boolean; endpoint: string }>({ saved: false, endpoint: "" });

  useEffect(() => {
    if (!businessProfile) return;
    if (!url && businessProfile.websiteUrl) setUrl(businessProfile.websiteUrl);
    if (!businessName && businessProfile.projectName)
      setBusinessName(businessProfile.projectName);
  }, [businessProfile]);

  useEffect(() => {
    // Fetch WordPress connection status
    async function checkWordPress() {
      try {
        const res = await fetch(`${API}/cms/credentials/wordpress`, {
          headers: { "X-API-KEY": apiKey },
        });
        const data = await res.json();
        setWordpressStatus({ saved: data.saved, endpoint: data.endpoint_url || "" });
      } catch (err) {
        console.error("Failed to fetch WordPress status:", err);
      }
    }
    checkWordPress();
  }, [apiKey, tab]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const data = await detectSchema(
        { url, business_type: businessType, business_name: businessName },
        apiKey,
      );
      setResult(data);
      toast.success(
        `Found ${data.blocks_found} schema block(s), ${data.missing_recommended.length} missing`,
      );
    } catch (err: any) {
      toast.error(err.message || "Schema detection failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(idx: number, payload: Record<string, any>) {
    const text = `<script type="application/ld+json">\n${JSON.stringify(payload, null, 2)}\n</script>`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(idx);
      setTimeout(() => setCopied(null), 1800);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Copy failed — select manually");
    }
  }

  async function handleBatchInject(e: React.FormEvent) {
    e.preventDefault();
    const urls = batchUrls.split("\n").map(u => u.trim()).filter(Boolean);
    if (!urls.length) {
      toast.error("Enter at least one URL");
      return;
    }
    if (!selectedSchemas.length) {
      toast.error("Select at least one schema type");
      return;
    }

    setBatchLoading(true);
    try {
      const res = await fetch(`${API}/schema/inject-batch`, {
        method: "POST",
        headers: {
          "X-API-KEY": apiKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          urls,
          schema_types: selectedSchemas,
          business_type: businessType,
          business_name: businessName,
          cms_auto_detect: true,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Injection failed");
      }
      const data = await res.json();
      setBatchResult(data);
      toast.success(`Injected ${data.success_count}/${data.total_urls} pages`);
    } catch (err: any) {
      toast.error(err.message || "Batch injection failed");
    } finally {
      setBatchLoading(false);
    }
  }

  function toggleSchema(schema: string) {
    setSelectedSchemas(prev =>
      prev.includes(schema)
        ? prev.filter(s => s !== schema)
        : [...prev, schema]
    );
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Schema Markup"
        subtitle="Detect and inject JSON-LD schema across your site with CMS auto-detection (WordPress, Shopify, Webflow)."
        icon={Braces}
        accent="#8B5CF6"
      />

      {/* Tab switcher */}
      <div className="flex gap-2 mb-6 border-b border-zinc-800">
        <button
          onClick={() => setTab("detect")}
          className={cn(
            "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
            tab === "detect"
              ? "text-violet-300 border-violet-500"
              : "text-zinc-400 border-transparent hover:text-zinc-300"
          )}
        >
          Single Page
        </button>
        <button
          onClick={() => setTab("inject")}
          className={cn(
            "px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-2",
            tab === "inject"
              ? "text-violet-300 border-violet-500"
              : "text-zinc-400 border-transparent hover:text-zinc-300"
          )}
        >
          <Zap className="w-4 h-4" /> Batch Inject
        </button>
      </div>

      {tab === "detect" && (
      <>
        <div className="card p-6 mb-6">
          <form onSubmit={handleSubmit} className="grid md:grid-cols-[2fr_1fr_1fr_auto] gap-3 items-end">
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                URL
              </label>
              <input
                type="url"
                value={url}
                onChange={e => setUrl(e.target.value)}
                className="input-field w-full"
                placeholder="https://example.com/page"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                Business type
              </label>
              <select
                value={businessType}
                onChange={e => setBusinessType(e.target.value)}
                className="input-field w-full"
              >
                {BUSINESS_TYPE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                Business name
              </label>
              <input
                type="text"
                value={businessName}
                onChange={e => setBusinessName(e.target.value)}
                className="input-field w-full"
                placeholder="Optional"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center gap-2 px-6 h-[42px]"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Braces className="w-4 h-4" />
              )}
              {loading ? "Scanning..." : "Scan Page"}
            </button>
          </form>
        </div>

        {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Blocks found" value={result.blocks_found} />
            <Stat
              label="Types detected"
              value={result.detected_types.length}
            />
            <Stat
              label="Missing recommended"
              value={result.missing_recommended.length}
              accent={result.missing_recommended.length > 0 ? "warn" : "ok"}
            />
            <Stat label="Generated stubs" value={result.generated.length} />
          </div>

          {result.parse_errors.length > 0 && (
            <div className="card p-4 border border-red-500/30 bg-red-500/5 text-sm text-red-300">
              {result.parse_errors.join(" · ")}
            </div>
          )}

          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200">
              Detected schema ({result.detected.length})
            </h3>
            {result.detected.length === 0 ? (
              <div className="text-sm text-zinc-500">
                No JSON-LD schema blocks found on this page.
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {result.detected.map((d, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-xs"
                  >
                    <Check className="w-3 h-3 text-emerald-400" />
                    <span className="text-emerald-300 font-medium">{d.type}</span>
                    {d.name && (
                      <span className="text-zinc-400">· {d.name}</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {result.missing_recommended.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-3 text-amber-400">
                Missing recommended ({result.missing_recommended.length})
              </h3>
              <div className="flex flex-wrap gap-2 mb-4">
                {result.missing_recommended.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-xs"
                  >
                    <X className="w-3 h-3 text-amber-400" />
                    <span className="text-amber-200 font-medium">{t}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-4">
                {result.generated.map((g: any, i: number) => {
                  const type = g["@type"];
                  return (
                    <div key={i} className="border border-zinc-800 rounded-xl overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 bg-zinc-900/50 border-b border-zinc-800">
                        <span className="text-sm font-medium text-amber-300">
                          {type}
                        </span>
                        <button
                          onClick={() => handleCopy(i, g)}
                          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition"
                        >
                          {copied === i ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              Copy
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="p-4 text-xs overflow-x-auto text-zinc-300 bg-zinc-950/40">
                        {JSON.stringify(g, null, 2)}
                      </pre>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
      </>
      )}

      {tab === "inject" && (
      <div className="space-y-6">
        {/* WordPress Connection Card */}
        <div className={cn("card p-4 border", wordpressStatus.saved ? "border-emerald-500/30 bg-emerald-500/5" : "border-zinc-700")}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-sm text-zinc-200 mb-1">WordPress Auto-Injection</h3>
              {wordpressStatus.saved ? (
                <p className="text-xs text-emerald-300">✓ Connected to {wordpressStatus.endpoint}</p>
              ) : (
                <p className="text-xs text-zinc-400">Connect your WordPress site for automatic schema injection</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => setWordpressModal(true)}
              className="flex items-center gap-2 text-sm px-3 py-2 bg-violet-500/10 text-violet-300 hover:bg-violet-500/20 rounded-lg transition"
            >
              <Settings2 className="w-4 h-4" />
              {wordpressStatus.saved ? "Update" : "Connect"}
            </button>
          </div>
        </div>

        <div className="card p-6">
          <form onSubmit={handleBatchInject} className="space-y-4">
            <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-2">
              URLs to inject (one per line)
            </label>
            <textarea
              value={batchUrls}
              onChange={e => setBatchUrls(e.target.value)}
              className="input-field w-full h-24 font-mono text-sm"
              placeholder="https://example.com/page-1&#10;https://example.com/page-2&#10;https://example.com/page-3"
              required
            />
            <div className="text-xs text-zinc-500 mt-1">
              {batchUrls.split("\n").filter(u => u.trim()).length} URLs
            </div>
          </div>

          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-2">
              Schema types to inject
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {SCHEMA_TYPES.map(schema => (
                <label key={schema} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedSchemas.includes(schema)}
                    onChange={() => toggleSchema(schema)}
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-sm text-zinc-300">{schema}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                Business type
              </label>
              <select
                value={businessType}
                onChange={e => setBusinessType(e.target.value)}
                className="input-field w-full"
              >
                {BUSINESS_TYPE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                Business name
              </label>
              <input
                type="text"
                value={businessName}
                onChange={e => setBusinessName(e.target.value)}
                className="input-field w-full"
                placeholder="Optional"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={batchLoading}
            className="btn-primary flex items-center gap-2 w-full justify-center py-3"
          >
            {batchLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {batchLoading ? "Injecting…" : "Inject to all URLs"}
          </button>
        </form>
        </div>
      </div>
      )}

      {batchResult && tab === "inject" && (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Total URLs" value={batchResult.total_urls} />
          <Stat label="Processed" value={batchResult.processed_count} />
          <Stat label="Successful" value={batchResult.success_count} accent="ok" />
          <Stat label="Failed" value={batchResult.failure_count} accent={batchResult.failure_count > 0 ? "warn" : "ok"} />
        </div>

        <div className="card p-6">
          <h3 className="font-semibold mb-4 text-zinc-200">Injection details</h3>
          <div className="space-y-2">
            {batchResult.injections?.slice(0, 10).map((inj: any, i: number) => (
              <div key={i} className={cn("flex items-center justify-between p-3 rounded-lg border",
                inj.status === "injected"
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : "bg-red-500/5 border-red-500/20"
              )}>
                <div className="text-sm">
                  <div className="font-medium text-zinc-200 truncate">{inj.url}</div>
                  <div className="text-xs text-zinc-500">{inj.schema_type} via {inj.cms_platform}</div>
                </div>
                <div className={cn("text-xs font-medium",
                  inj.status === "injected" ? "text-emerald-300" : "text-red-300"
                )}>
                  {inj.status === "injected" ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      )}

      <CMSCredentialsModal
        isOpen={wordpressModal}
        platform="wordpress"
        onClose={() => setWordpressModal(false)}
        onSave={() => {
          // Refresh WordPress status
          setTimeout(async () => {
            try {
              const res = await fetch(`${API}/cms/credentials/wordpress`, {
                headers: { "X-API-KEY": apiKey },
              });
              const data = await res.json();
              setWordpressStatus({ saved: data.saved, endpoint: data.endpoint_url || "" });
            } catch (err) {
              console.error("Failed to refresh WordPress status:", err);
            }
          }, 500);
        }}
        apiKey={apiKey}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number | string;
  accent?: "ok" | "warn";
}) {
  const color =
    accent === "warn"
      ? "text-amber-400"
      : accent === "ok"
      ? "text-emerald-400"
      : "text-zinc-100";
  return (
    <div className="bg-zinc-800/30 rounded-lg p-4 border border-zinc-800">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
        {label}
      </div>
      <div className={cn("text-3xl font-semibold font-serif", color)}>
        {value}
      </div>
    </div>
  );
}
