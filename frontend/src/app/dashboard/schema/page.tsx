"use client";

import { useEffect, useState } from "react";
import { Braces, Check, Copy, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { detectSchema, type SchemaDetectionResult } from "@/lib/api";
import { toast } from "sonner";

const BUSINESS_TYPE_OPTIONS = [
  { value: "default", label: "Default (any business)" },
  { value: "local_business", label: "Local Business" },
  { value: "restaurant", label: "Restaurant" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "saas", label: "SaaS" },
  { value: "publisher", label: "Publisher / Blog" },
  { value: "agency", label: "Agency / Services" },
];

export default function SchemaPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [url, setUrl] = useState("");
  const [businessType, setBusinessType] = useState("default");
  const [businessName, setBusinessName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SchemaDetectionResult | null>(null);
  const [copied, setCopied] = useState<number | null>(null);

  useEffect(() => {
    if (!businessProfile) return;
    if (!url && businessProfile.websiteUrl) setUrl(businessProfile.websiteUrl);
    if (!businessName && businessProfile.projectName)
      setBusinessName(businessProfile.projectName);
  }, [businessProfile]);

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

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Braces className="w-6 h-6 text-amber-400" /> Schema Markup
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Detect JSON-LD already on the page, flag missing schema types
          recommended for your business, and generate ready-to-paste markup
          for the gaps.
        </p>
      </div>

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
