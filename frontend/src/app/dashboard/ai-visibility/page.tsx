"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, Bot, Check, X, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
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

// Mock historical data (in production, fetch from backend)
const MOCK_HISTORY = [
  { date: "2026-01-08", score: 42, coverage: 35, citations: 28 },
  { date: "2026-01-09", score: 44, coverage: 36, citations: 30 },
  { date: "2026-01-10", score: 46, coverage: 38, citations: 32 },
  { date: "2026-01-11", score: 48, coverage: 40, citations: 35 },
  { date: "2026-01-12", score: 50, coverage: 42, citations: 37 },
  { date: "2026-01-13", score: 52, coverage: 44, citations: 40 },
  { date: "2026-01-14", score: 54, coverage: 46, citations: 42 },
];

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
  const [activeTab, setActiveTab] = useState<"dashboard" | "checker">("dashboard");

  useEffect(() => {
    if (businessProfile?.websiteUrl && !domain) {
      setDomain(
        businessProfile.websiteUrl
          .replace(/^https?:\/\//, "")
          .replace(/\/$/, ""),
      );
    }
    if (businessProfile?.keywords?.length && !keywordsText) {
      setKeywordsText(businessProfile.keywords.slice(0, 5).join("\n"));
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
        title="AI Visibility (AEO)"
        subtitle="Track where your brand appears in Google AI Overviews and LLM responses (ChatGPT, Perplexity, Gemini, Copilot)."
        icon={Sparkles}
        accent="#A3E635"
      />

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={cn(
            "px-4 py-2 rounded-lg font-medium text-sm transition",
            activeTab === "dashboard"
              ? "bg-violet-600 text-white"
              : "bg-zinc-900 text-zinc-400 hover:text-zinc-200"
          )}
        >
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab("checker")}
          className={cn(
            "px-4 py-2 rounded-lg font-medium text-sm transition",
            activeTab === "checker"
              ? "bg-violet-600 text-white"
              : "bg-zinc-900 text-zinc-400 hover:text-zinc-200"
          )}
        >
          Run Check
        </button>
      </div>

      {/* Dashboard Tab */}
      {activeTab === "dashboard" && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <KpiCard
              label="AI Visibility Score"
              value={54}
              change={+12}
              color="#A3E635"
            />
            <KpiCard
              label="AI Overview Coverage"
              value={46}
              change={+11}
              suffix="%"
              color="#22D3EE"
            />
            <KpiCard
              label="LLM Citation Rate"
              value={42}
              change={+14}
              suffix="%"
              color="#EC4899"
            />
            <KpiCard
              label="Keywords Tracked"
              value={147}
              change={+3}
              color="#F97316"
            />
          </div>

          {/* Trend Chart */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-zinc-200">7-Day Trend</h3>
              <span className="text-xs text-zinc-500">Last 7 days</span>
            </div>
            <AeoTrendChart data={MOCK_HISTORY} />
          </div>

          {/* Per-Engine Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(Object.entries(ENGINE_LABELS) as [LLMEngine, string][]).map(([engine, label]) => (
              <div key={engine} className="card p-4 border border-zinc-800">
                <div className="flex items-center gap-2 mb-3">
                  <Bot className="w-4 h-4" style={{ color: "#A3E635" }} />
                  <h4 className="font-semibold text-sm">{label}</h4>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Citation Rate</span>
                    <span className="text-emerald-400 font-mono">38%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Mention Rate</span>
                    <span className="text-blue-400 font-mono">12%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Last Checked</span>
                    <span className="text-zinc-400 text-xs">2h ago</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Alerts */}
          <div className="card p-4 border border-amber-900/50 bg-amber-900/10">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold text-amber-200 text-sm">Opportunity</h4>
                <p className="text-xs text-amber-100 mt-1">
                  "Best CRM software" keyword has 0% AI citation but 18 monthly searches. Optimize this page for E-E-A-T signals and entity coverage.
                </p>
              </div>
            </div>
          </div>

          {/* Recommendations */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-zinc-200 mb-4">Recommendations to Boost AEO</h3>
            <div className="space-y-3">
              {[
                { title: "Add Entity Markup", desc: "Implement schema.org markup for better entity coverage in AI responses" },
                { title: "Improve E-E-A-T Signals", desc: "Add author bios, credentials, publication dates to build topical authority" },
                { title: "Optimize for Question Intent", desc: "Create FAQ blocks and Q&A content to match LLM training data patterns" },
                { title: "Update Structured Data", desc: "Refresh FAQPage, Article, and Organization schemas monthly" },
              ].map((rec, i) => (
                <div key={i} className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
                  <div className="font-medium text-sm text-zinc-200">{rec.title}</div>
                  <div className="text-xs text-zinc-500 mt-1">{rec.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Checker Tab */}
      {activeTab === "checker" && (
        <>
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
                  {loading ? "Checking..." : "Run AEO Check"}
                </button>
              </div>
            </form>
          </div>

          {report && <ReportView report={report} />}
        </>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  change,
  suffix = "",
  color = "#8B5CF6",
}: {
  label: string;
  value: number;
  change: number;
  suffix?: string;
  color?: string;
}) {
  return (
    <div className="card p-4 border border-zinc-800">
      <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">
        {label}
      </div>
      <div className="flex items-end justify-between">
        <div className="text-2xl font-bold font-serif" style={{ color }}>
          {value}
          {suffix}
        </div>
        <div className={cn("flex items-center gap-1 text-xs font-medium", change >= 0 ? "text-emerald-400" : "text-red-400")}>
          {change >= 0 ? (
            <TrendingUp className="w-3 h-3" />
          ) : (
            <TrendingDown className="w-3 h-3" />
          )}
          {change > 0 ? "+" : ""}{change}%
        </div>
      </div>
    </div>
  );
}

function AeoTrendChart({ data }: { data: any[] }) {
  const maxScore = Math.max(...data.map(d => d.score));
  const W = 600, H = 200;
  const points = data.map((d, i) => ({
    x: (i / (data.length - 1)) * (W - 40),
    y: H - 40 - (d.score / maxScore) * (H - 80),
    score: d.score,
  }));

  const scorePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <svg width={W} height={H} className="w-full overflow-visible">
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
        <line
          key={v}
          x1="30"
          y1={40 + v * (H - 80)}
          x2={W - 10}
          y2={40 + v * (H - 80)}
          stroke="#3f3f46"
          strokeWidth="1"
          strokeDasharray="4"
        />
      ))}

      {/* Score line */}
      <path
        d={scorePath}
        fill="none"
        stroke="#A3E635"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Points */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#A3E635" />
      ))}

      {/* Y-axis labels */}
      {[0, 25, 50, 75, 100].map((v) => (
        <text
          key={v}
          x="5"
          y={40 + ((100 - v) / 100) * (H - 80) + 4}
          fontSize="11"
          fill="#71717a"
          textAnchor="end"
        >
          {v}
        </text>
      ))}

      {/* X-axis labels */}
      {data.map((d, i) => (
        <text
          key={i}
          x={points[i].x}
          y={H - 5}
          fontSize="10"
          fill="#71717a"
          textAnchor="middle"
        >
          {d.date.slice(-2)}
        </text>
      ))}
    </svg>
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
