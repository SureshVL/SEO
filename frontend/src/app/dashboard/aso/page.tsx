"use client";

import { useState } from "react";
import { Smartphone, Loader2, Sparkles, Star, ListChecks } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { runAso } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export default function AsoPage() {
  const { apiKey } = useAppStore();
  const [appLink, setAppLink] = useState("");
  const [appName, setAppName] = useState("");
  const [category, setCategory] = useState("");
  const [primary, setPrimary] = useState("");
  const [secondary, setSecondary] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function run() {
    if (!appLink || !appName || !category || !primary) {
      toast.error("Fill app link, name, category and primary keyword.");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const data = await runAso({
        app_link: appLink,
        app_name: appName,
        category,
        primary_keyword: primary,
        secondary_keywords: secondary.split(",").map(s => s.trim()).filter(Boolean),
        locales: ["en-US"],
      }, apiKey);
      setResult(data);
      toast.success("ASO metadata generated");
    } catch (err: any) {
      toast.error(err?.message || "ASO run failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="App Store Optimization"
        subtitle="Generate store-ready titles, subtitles, keyword fields and review-response playbooks for your iOS/Android app."
        icon={Smartphone}
        accent="#2DD4BF"
      />

      <div className="card p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input label="App store link" value={appLink} onChange={setAppLink} placeholder="https://apps.apple.com/…" />
          <Input label="App name" value={appName} onChange={setAppName} placeholder="Surrvik" />
          <Input label="Category" value={category} onChange={setCategory} placeholder="Productivity" />
          <Input label="Primary keyword" value={primary} onChange={setPrimary} placeholder="task manager" />
          <div className="md:col-span-2">
            <Input label="Secondary keywords (comma-separated)" value={secondary} onChange={setSecondary} placeholder="to-do, planner, notes" />
          </div>
        </div>
        <button onClick={run} disabled={loading} className="btn-primary mt-5 flex items-center gap-2 px-6 h-[42px]">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {loading ? "Optimizing…" : "Generate ASO metadata"}
        </button>
      </div>

      {result && (
        <div className="space-y-6">
          {(result.metadata ?? []).map((m: any, i: number) => (
            <div key={i} className="card p-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold px-2 py-1 rounded-full bg-teal-500/10 text-teal-300">{m.locale}</span>
                <span className="text-xs text-zinc-500">{result.platform}</span>
              </div>
              <Block label="Title variants">
                <ul className="space-y-1">
                  {(m.title_variants ?? []).map((t: string, j: number) => (
                    <li key={j} className="text-sm text-zinc-200">{t} <span className="text-zinc-500 text-xs">({t.length} chars)</span></li>
                  ))}
                </ul>
              </Block>
              <Block label="Subtitle"><p className="text-sm text-zinc-300">{m.subtitle}</p></Block>
              <Block label="Keyword field"><p className="text-sm text-zinc-300 font-mono">{m.keyword_field}</p></Block>
              <Block label="Short description"><p className="text-sm text-zinc-300">{m.short_description}</p></Block>
            </div>
          ))}

          {(result.optimization_notes ?? []).length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-3 text-zinc-200 flex items-center gap-2"><ListChecks className="w-4 h-4" /> Optimization notes</h3>
              <ul className="space-y-2">
                {result.optimization_notes.map((n: string, i: number) => (
                  <li key={i} className="text-sm text-zinc-400 flex gap-2"><span className="text-teal-400">›</span>{n}</li>
                ))}
              </ul>
            </div>
          )}

          {(result.review_response_playbook ?? []).length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-3 text-zinc-200 flex items-center gap-2"><Star className="w-4 h-4" /> Review-response playbook</h3>
              <div className="space-y-3">
                {result.review_response_playbook.map((r: any, i: number) => (
                  <div key={i} className="border border-zinc-800 rounded-lg p-3">
                    <div className="text-xs font-semibold text-teal-300 capitalize mb-1">{r.sentiment}</div>
                    <p className="text-sm text-zinc-300">{r.response_template}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Input({ label, value, onChange, placeholder }: any) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">{label}</span>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="mt-1 w-full bg-zinc-800/50 border border-zinc-700 rounded-lg px-3 py-2 text-sm outline-none focus:border-teal-500/50" />
    </label>
  );
}
function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold mb-1">{label}</div>
      {children}
    </div>
  );
}
