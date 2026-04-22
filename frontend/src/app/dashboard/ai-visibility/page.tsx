"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, Bot, Check, X } from "lucide-react";
import { cn, scoreBg, scoreColor } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  geoCheck,
  type AIVisibilityReport,
  type KeywordVisibility,
  type LLMEngine,
} from "@/lib/api";
import { toast } from "sonner";

const ENGINE_LABELS: Record<LLMEngine, string> = {
  chat_gpt: "ChatGPT",
  perplexity: "Perplexity",
  gemini: "Gemini",
};

export default function AIVisibilityPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [domain, setDomain] = useState("");
  const [keywordsText, setKeywordsText] = useState("");
  const [engines, setEngines] = useState<Record<LLMEngine, boolean>>({
    chat_gpt: true,
    perplexity: true,
    gemini: true,
  });
  const [includeAiMode, setIncludeAiMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AIVisibilityReport | null>(null);

  useEffect(() => {
    if (businessProfile?.websiteUrl && !domain) {
      setDomain(
        businessProfile.websiteUrl
          .replace(/^https?:\/\//, "")
          .replace(/\/$/, ""),
      );
    }
    if (businessProfile?.keywords?.length && !keywordsText) {
      setKeywordsText(businessProfile.keywords.join("\n"));
    }
  }, [businessProfile]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const keywords = keywordsText
      .split(/\n|,/)
      .map(k => k.trim())
      .filter(Boolean);
    if (!keywords.length) {
      toast.error("Enter at least one keyword");
      return;
    }
    const selectedEngines = (Object.keys(engines) as LLMEngine[]).filter(
      e => engines[e],
    );
    if (!selectedEngines.length) {
      toast.error("Pick at least one engine");
      return;
    }

    setLoading(true);
    setReport(null);
    try {
      const result = await geoCheck(
        {
          keywords,
          domain,
          engines: selectedEngines,
          include_ai_mode: includeAiMode,
        },
        apiKey,
      );
      setReport(result);
      toast.success(
        `Checked ${result.total_keywords} keywords across ${result.engines.length} engines`,
      );
    } catch (err: any) {
      toast.error(err.message || "GEO check failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="AI Visibility (GEO)"
        subtitle="Track whether your domain is cited in Google AI Overviews, AI Mode, and LLM responses from ChatGPT, Perplexity, and Gemini."
        icon={Sparkles}
        accent="#A3E635"
      />

      <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              Domain
            </label>
            <input
              type="text"
              value={domain}
              onChange={e => setDomain(e.target.value)}
              className="input-field w-full"
              placeholder="example.com"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              Keywords (one per line or comma-separated, max 50)
            </label>
            <textarea
              value={keywordsText}
              onChange={e => setKeywordsText(e.target.value)}
              className="input-field w-full h-28 font-mono text-sm"
              placeholder={"best crm software\ncheap vps hosting"}
              required
            />
          </div>
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-500 uppercase tracking-wider">
                Engines:
              </span>
              {(Object.keys(ENGINE_LABELS) as LLMEngine[]).map(eng => (
                <label key={eng} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={engines[eng]}
                    onChange={e =>
                      setEngines({ ...engines, [eng]: e.target.checked })
                    }
                  />
                  {ENGINE_LABELS[eng]}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={includeAiMode}
                onChange={e => setIncludeAiMode(e.target.checked)}
              />
              Include Google AI Mode
            </label>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center gap-2 px-6 ml-auto"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Bot className="w-4 h-4" />
              )}
              {loading ? "Checking..." : "Run GEO Check"}
            </button>
          </div>
        </form>
      </div>

      {report && <ReportView report={report} />}
    </div>
  );
}

function ReportView({ report }: { report: AIVisibilityReport }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ScoreCard label="Overall Score" value={report.overall_score} />
        <ScoreCard
          label="AI Overview Coverage"
          value={report.ai_overview_coverage}
          suffix="%"
        />
        <ScoreCard
          label="AI Overview Citation Rate"
          value={report.ai_overview_citation_rate}
          suffix="%"
        />
        <div className="card p-4 border border-zinc-800">
          <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
            LLM Mentions
          </div>
          <div className="space-y-0.5 text-sm">
            {Object.entries(report.llm_mention_rate).map(([eng, rate]) => (
              <div key={eng} className="flex justify-between">
                <span className="text-zinc-400">
                  {ENGINE_LABELS[eng as LLMEngine] ?? eng}
                </span>
                <span className={cn("font-mono", scoreColor(rate))}>
                  {rate}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold mb-4 text-zinc-200">
          Per-Keyword Visibility
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-zinc-500 uppercase tracking-wider">
              <tr className="border-b border-zinc-800">
                <th className="text-left py-2 pr-3">Keyword</th>
                <th className="text-right py-2 px-2">Score</th>
                <th className="text-center py-2 px-2">AI Overview</th>
                {report.engines.map(eng => (
                  <th key={eng} className="text-center py-2 px-2">
                    {ENGINE_LABELS[eng as LLMEngine] ?? eng}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.keywords.map((k, i) => (
                <KeywordRow
                  key={i}
                  k={k}
                  engines={report.engines}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KeywordRow({
  k,
  engines,
}: {
  k: KeywordVisibility;
  engines: string[];
}) {
  return (
    <tr className="border-b border-zinc-900">
      <td className="py-2 pr-3 text-zinc-200">{k.keyword}</td>
      <td
        className={cn(
          "text-right py-2 px-2 font-mono font-semibold",
          scoreColor(k.visibility_score),
        )}
      >
        {Math.round(k.visibility_score)}
      </td>
      <td className="text-center py-2 px-2">
        {k.ai_overview_present ? (
          k.ai_overview_cited ? (
            <span
              className="inline-flex items-center gap-1 text-emerald-400"
              title={`Cited at position ${k.ai_overview_position}`}
            >
              <Check className="w-4 h-4" /> #{k.ai_overview_position}
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1 text-amber-400"
              title="AI Overview present, domain not cited"
            >
              <X className="w-4 h-4" /> shown
            </span>
          )
        ) : (
          <span className="text-zinc-600">—</span>
        )}
      </td>
      {engines.map(eng => {
        const r = k.llm_results[eng];
        if (!r) return <td key={eng} className="text-center py-2 px-2 text-zinc-600">—</td>;
        if (r.error)
          return (
            <td
              key={eng}
              className="text-center py-2 px-2 text-red-500"
              title={r.error}
            >
              err
            </td>
          );
        if (r.citation_position) {
          return (
            <td key={eng} className="text-center py-2 px-2">
              <span
                className="inline-flex items-center gap-1 text-emerald-400"
                title={`Cited — position ${r.citation_position}`}
              >
                <Check className="w-4 h-4" /> #{r.citation_position}
              </span>
            </td>
          );
        }
        if (r.mentioned) {
          return (
            <td key={eng} className="text-center py-2 px-2 text-blue-400" title="Mentioned in answer text">
              mention
            </td>
          );
        }
        return (
          <td key={eng} className="text-center py-2 px-2 text-zinc-600">
            —
          </td>
        );
      })}
    </tr>
  );
}

function ScoreCard({
  label,
  value,
  suffix = "",
}: {
  label: string;
  value: number;
  suffix?: string;
}) {
  return (
    <div className={cn("card p-4 text-center border", scoreBg(value))}>
      <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
        {label}
      </div>
      <div className={cn("text-3xl font-bold font-serif", scoreColor(value))}>
        {Math.round(value)}
        {suffix}
      </div>
    </div>
  );
}
