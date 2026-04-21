"use client";

import { useState } from "react";
import { Download, Grid3x3, Loader2, Play } from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  generateProgrammaticPages,
  type ProgrammaticResult,
  type ProgrammaticTemplate,
} from "@/lib/api";
import { toast } from "sonner";

const DEFAULT_TEMPLATE: ProgrammaticTemplate = {
  name: "City services",
  slug_template: "/{{service}}-in-{{city}}",
  title_template: "{{service}} in {{city}} — Top-Rated Local Providers",
  meta_description_template:
    "Find the best {{service}} in {{city}}. Compare rated providers, prices, and reviews.",
  h1_template: "Best {{service}} in {{city}}",
  body_template:
    "## Why {{city}} trusts local {{service}} experts\n\n" +
    "Whether you need a quick quote or a long-term partner, {{city}}'s top " +
    "{{service}} providers deliver results backed by verified reviews.\n\n" +
    "- Licensed, insured professionals\n" +
    "- Same-week availability\n" +
    "- Transparent pricing in {{city}}\n",
};

const DEFAULT_CSV = `service,city
plumbing,Austin
plumbing,Dallas
plumbing,Houston
electrician,Austin
electrician,Dallas
electrician,Houston
`;

export default function ProgrammaticPage() {
  const { apiKey } = useAppStore();
  const [template, setTemplate] = useState<ProgrammaticTemplate>(DEFAULT_TEMPLATE);
  const [csv, setCsv] = useState<string>(DEFAULT_CSV);
  const [maxPages, setMaxPages] = useState(500);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ProgrammaticResult | null>(null);

  function patch<K extends keyof ProgrammaticTemplate>(key: K, value: ProgrammaticTemplate[K]) {
    setTemplate(t => ({ ...t, [key]: value }));
  }

  async function handleGenerate() {
    setRunning(true);
    try {
      const res = await generateProgrammaticPages(
        { template, csv, max_pages: maxPages },
        apiKey,
      );
      setResult(res);
      if (!res.generated) {
        toast.error("No pages generated — check your CSV headers match the {{variables}}");
      } else {
        toast.success(`Generated ${res.generated} page${res.generated === 1 ? "" : "s"}`);
      }
    } catch (err: any) {
      toast.error(err.message || "Generation failed");
    } finally {
      setRunning(false);
    }
  }

  function exportJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${template.name || "programmatic"}-pages.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Grid3x3 className="w-6 h-6 text-emerald-400" /> Programmatic SEO
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Generate hundreds of SEO pages by combining a template with a CSV dataset.
          Use <code className="text-emerald-300">{`{{variable}}`}</code> placeholders that match
          your CSV column names.
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="card p-6">
            <h3 className="font-semibold text-zinc-200 mb-3">Template</h3>
            <div className="space-y-3">
              <Field label="Name (internal)">
                <input
                  value={template.name || ""}
                  onChange={e => patch("name", e.target.value)}
                  className="input-field"
                  placeholder="City services"
                />
              </Field>
              <Field label="Slug template">
                <input
                  value={template.slug_template}
                  onChange={e => patch("slug_template", e.target.value)}
                  className="input-field font-mono text-sm"
                  placeholder="/{{service}}-in-{{city}}"
                />
              </Field>
              <Field label="Title template">
                <input
                  value={template.title_template}
                  onChange={e => patch("title_template", e.target.value)}
                  className="input-field"
                />
              </Field>
              <Field label="Meta description template">
                <input
                  value={template.meta_description_template}
                  onChange={e => patch("meta_description_template", e.target.value)}
                  className="input-field"
                />
              </Field>
              <Field label="H1 template (optional, falls back to title)">
                <input
                  value={template.h1_template || ""}
                  onChange={e => patch("h1_template", e.target.value)}
                  className="input-field"
                />
              </Field>
              <Field label="Body (markdown)">
                <textarea
                  value={template.body_template}
                  onChange={e => patch("body_template", e.target.value)}
                  className="input-field font-mono text-xs min-h-[160px]"
                />
              </Field>
            </div>
          </div>

          <div className="card p-6">
            <h3 className="font-semibold text-zinc-200 mb-3">Dataset (CSV)</h3>
            <p className="text-xs text-zinc-500 mb-2">
              First row is headers. Column names become <code>{`{{variable}}`}</code> names.
            </p>
            <textarea
              value={csv}
              onChange={e => setCsv(e.target.value)}
              className="input-field font-mono text-xs min-h-[180px]"
            />
            <div className="flex items-center gap-3 mt-3">
              <label className="text-xs text-zinc-500">Max pages</label>
              <input
                type="number"
                min={1}
                max={5000}
                value={maxPages}
                onChange={e => setMaxPages(parseInt(e.target.value || "500", 10))}
                className="input-field w-24"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerate}
              disabled={running}
              className="btn-primary flex items-center gap-2"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Generate pages
            </button>
            {result && (
              <button onClick={exportJson} className="btn-ghost flex items-center gap-2">
                <Download className="w-4 h-4" /> Export JSON
              </button>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="card p-4">
            <h3 className="font-semibold text-zinc-200 mb-3">Result</h3>
            {!result ? (
              <div className="text-sm text-zinc-500">
                Hit <em>Generate pages</em> to preview the output. Nothing is saved until you
                explicitly export.
              </div>
            ) : (
              <>
                <div className="grid grid-cols-4 gap-3 mb-4 text-center">
                  <Stat label="Rows" value={result.total_rows} />
                  <Stat label="Generated" value={result.generated} tone="good" />
                  <Stat label="Skipped" value={result.skipped} tone="warn" />
                  <Stat label="Variables" value={result.variables_used.length} />
                </div>
                {result.variables_used.length > 0 && (
                  <div className="mb-3 text-xs">
                    <span className="text-zinc-500 mr-2">Variables:</span>
                    {result.variables_used.map(v => (
                      <code
                        key={v}
                        className="mr-1 px-1.5 py-0.5 bg-emerald-500/10 text-emerald-300 rounded"
                      >
                        {`{{${v}}}`}
                      </code>
                    ))}
                  </div>
                )}
                {result.warnings.length > 0 && (
                  <div className="mb-3 p-3 border border-amber-500/30 bg-amber-500/5 rounded text-xs">
                    <div className="font-semibold text-amber-300 mb-1">Warnings</div>
                    <ul className="list-disc pl-5 text-amber-200">
                      {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>

          {result && result.pages.length > 0 && (
            <div className="card p-0 overflow-hidden">
              <div className="max-h-[600px] overflow-y-auto divide-y divide-zinc-800">
                {result.pages.map((p, i) => (
                  <div key={i} className="p-4 hover:bg-zinc-900/30">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <code className="text-xs text-emerald-300 font-mono break-all">{p.slug}</code>
                      {p.warnings.length > 0 && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-amber-500/10 text-amber-300 rounded flex-shrink-0">
                          {p.warnings.length} warning{p.warnings.length === 1 ? "" : "s"}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-zinc-200 font-medium mb-1">{p.title}</div>
                    <div className="text-xs text-zinc-500 line-clamp-2">{p.meta_description}</div>
                    {p.warnings.length > 0 && (
                      <div className="mt-2 text-[11px] text-amber-300">
                        {p.warnings.join(" · ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] text-zinc-500 uppercase tracking-wider mb-1">{label}</span>
      {children}
    </label>
  );
}

function Stat({
  label, value, tone = "neutral",
}: {
  label: string; value: number; tone?: "good" | "warn" | "neutral";
}) {
  const color =
    tone === "good" ? "text-emerald-300" :
    tone === "warn" ? "text-amber-300" : "text-zinc-200";
  return (
    <div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider">{label}</div>
    </div>
  );
}
