"use client";

import { useEffect, useState } from "react";
import {
  Check,
  Copy,
  Gauge,
  Lightbulb,
  Loader2,
  Sparkles,
  Target,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import {
  generateContentBrief,
  scoreContent,
  type ContentBrief,
  type ContentScore,
} from "@/lib/api";
import { toast } from "sonner";

export default function ContentBriefPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [keyword, setKeyword] = useState("");
  const [domain, setDomain] = useState("");
  const [scoreUrl, setScoreUrl] = useState("");
  const [scoreMarkdown, setScoreMarkdown] = useState("");

  const [brief, setBrief] = useState<ContentBrief | null>(null);
  const [score, setScore] = useState<ContentScore | null>(null);

  const [briefLoading, setBriefLoading] = useState(false);
  const [scoreLoading, setScoreLoading] = useState(false);

  useEffect(() => {
    if (!businessProfile) return;
    if (!keyword && businessProfile.keywords?.[0]) {
      setKeyword(businessProfile.keywords[0]);
    }
    if (!domain && businessProfile.websiteUrl) {
      setDomain(cleanDomain(businessProfile.websiteUrl));
    }
  }, [businessProfile]);

  async function handleGenerateBrief(e: React.FormEvent) {
    e.preventDefault();
    setBriefLoading(true);
    setBrief(null);
    setScore(null);
    try {
      const data = await generateContentBrief(
        { keyword, domain, scrape_top_n: 5 },
        apiKey,
      );
      setBrief(data);
      toast.success(
        `Brief ready · ${data.recommended_headings.length} headings · target ${data.target_word_count} words`,
      );
    } catch (err: any) {
      toast.error(err.message || "Brief generation failed");
    } finally {
      setBriefLoading(false);
    }
  }

  async function handleScore(e: React.FormEvent) {
    e.preventDefault();
    if (!scoreUrl && !scoreMarkdown) {
      toast.error("Paste a URL or markdown to score");
      return;
    }
    setScoreLoading(true);
    try {
      const data = await scoreContent(
        {
          keyword,
          url: scoreUrl,
          markdown: scoreMarkdown,
          brief: brief ?? undefined,
        },
        apiKey,
      );
      setScore(data);
      toast.success(`Score ${data.total} / 100`);
    } catch (err: any) {
      toast.error(err.message || "Scoring failed");
    } finally {
      setScoreLoading(false);
    }
  }

  async function copyBrief() {
    if (!brief) return;
    const text = formatBriefMarkdown(brief);
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Brief copied as markdown");
    } catch {
      toast.error("Copy failed");
    }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Lightbulb className="w-6 h-6 text-amber-400" /> Content Brief &amp; Score
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Pull the top SERP competitors, generate a writing brief (headings,
          entities, questions), then score any URL or draft against the
          competitive landscape.
        </p>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleGenerateBrief} className="grid md:grid-cols-[2fr_1fr_auto] gap-3 items-end">
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              Target keyword
            </label>
            <input
              type="text"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              className="input-field w-full"
              placeholder="best seo tools"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              Your domain (optional)
            </label>
            <input
              type="text"
              value={domain}
              onChange={e => setDomain(e.target.value)}
              className="input-field w-full"
              placeholder="example.com"
            />
          </div>
          <button
            type="submit"
            disabled={briefLoading}
            className="btn-primary flex items-center gap-2 px-6 h-[42px]"
          >
            {briefLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {briefLoading ? "Analyzing SERP..." : "Generate Brief"}
          </button>
        </form>
      </div>

      {brief && (
        <div className="space-y-6 mb-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Target words" value={brief.target_word_count} />
            <Stat label="SERP median" value={brief.serp_median_words} />
            <Stat label="Recommended H2s" value={brief.recommended_headings.length} />
            <Stat label="Entities" value={brief.must_cover_entities.length} />
          </div>

          {brief.ai_overview_present && (
            <div className="card p-4 border border-amber-500/30 bg-amber-500/5 text-sm">
              <div className="text-amber-300 font-medium mb-1 flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> AI Overview detected
              </div>
              <p className="text-zinc-300">{brief.ai_overview_snippet}</p>
            </div>
          )}

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-zinc-200">Content brief</h3>
              <button
                onClick={copyBrief}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200"
              >
                <Copy className="w-3 h-3" /> Copy as markdown
              </button>
            </div>

            <div className="grid md:grid-cols-2 gap-6 text-sm">
              <Section title={`Recommended H2s (${brief.recommended_headings.length})`}>
                <ul className="space-y-1.5 text-zinc-300">
                  {brief.recommended_headings.map((h, i) => (
                    <li key={i}>· {h}</li>
                  ))}
                </ul>
              </Section>

              <Section title={`Must-cover entities (${brief.must_cover_entities.length})`}>
                <div className="flex flex-wrap gap-1.5">
                  {brief.must_cover_entities.map((e, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 text-xs rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30"
                    >
                      {e}
                    </span>
                  ))}
                </div>
              </Section>

              <Section title={`Questions to answer (${brief.questions_to_answer.length})`}>
                <ul className="space-y-1.5 text-zinc-300">
                  {brief.questions_to_answer.map((q, i) => (
                    <li key={i}>· {q}</li>
                  ))}
                </ul>
              </Section>

              <Section title="Meta">
                <div className="space-y-2 text-zinc-300">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Title</div>
                    <div className="text-xs">{brief.meta_title_suggestion || "—"}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Description</div>
                    <div className="text-xs">{brief.meta_description_suggestion || "—"}</div>
                  </div>
                </div>
              </Section>
            </div>
          </div>

          <div className="card p-6">
            <h3 className="font-semibold mb-3 text-zinc-200">
              Top SERP competitors ({brief.competitors.length})
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-zinc-500 border-b border-zinc-800">
                    <th className="py-2">#</th>
                    <th className="py-2">URL</th>
                    <th className="py-2">Title</th>
                    <th className="py-2 text-right">Words</th>
                    <th className="py-2 text-right">H2/H3s</th>
                  </tr>
                </thead>
                <tbody>
                  {brief.competitors.map((c, i) => (
                    <tr key={i} className="border-b border-zinc-800/50">
                      <td className="py-2 text-zinc-500">{c.position ?? i + 1}</td>
                      <td className="py-2 max-w-[320px] truncate">
                        <a href={c.url} target="_blank" rel="noreferrer" className="text-amber-300 hover:underline">
                          {c.url}
                        </a>
                      </td>
                      <td className="py-2 max-w-[280px] truncate text-zinc-300">{c.title}</td>
                      <td className="py-2 text-right text-zinc-300">{c.word_count || "—"}</td>
                      <td className="py-2 text-right text-zinc-400">{c.headings.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className="card p-6 mb-6">
        <h3 className="font-semibold mb-3 text-zinc-200 flex items-center gap-2">
          <Gauge className="w-4 h-4 text-amber-400" /> Score content
        </h3>
        <p className="text-xs text-zinc-500 mb-4">
          Scored against the brief above (if generated) or a fresh SERP pull.
        </p>
        <form onSubmit={handleScore} className="space-y-3">
          <div className="grid md:grid-cols-[2fr_auto] gap-3 items-end">
            <div>
              <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
                URL to score
              </label>
              <input
                type="url"
                value={scoreUrl}
                onChange={e => setScoreUrl(e.target.value)}
                className="input-field w-full"
                placeholder="https://yoursite.com/post"
              />
            </div>
            <button
              type="submit"
              disabled={scoreLoading}
              className="btn-primary flex items-center gap-2 px-6 h-[42px]"
            >
              {scoreLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Target className="w-4 h-4" />
              )}
              {scoreLoading ? "Scoring..." : "Score"}
            </button>
          </div>
          <div>
            <label className="block text-xs text-zinc-500 uppercase tracking-wider mb-1">
              …or paste markdown
            </label>
            <textarea
              value={scoreMarkdown}
              onChange={e => setScoreMarkdown(e.target.value)}
              rows={6}
              className="input-field w-full font-mono text-xs"
              placeholder="# My draft&#10;&#10;Paste your draft markdown to score it against the brief."
            />
          </div>
        </form>
      </div>

      {score && (
        <div className="space-y-4">
          <div className="card p-6 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-wider text-zinc-500 mb-1">
                Content score
              </div>
              <div className={cn("text-5xl font-bold font-serif", scoreColor(score.total))}>
                {score.total}
                <span className="text-2xl text-zinc-500 font-sans"> / 100</span>
              </div>
              <div className="text-xs text-zinc-500 mt-2">
                {score.word_count} words · SERP median {score.serp_median_words}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <Metric label="Length" value={score.breakdown.length} max={20} />
              <Metric label="Headings" value={score.breakdown.headings} max={25} />
              <Metric label="Entities" value={score.breakdown.entities} max={25} />
              <Metric label="Questions" value={score.breakdown.questions} max={15} />
              <Metric label="Keyword use" value={score.breakdown.keyword_usage} max={15} />
            </div>
          </div>

          {score.recommendations.length > 0 && (
            <div className="card p-6">
              <h3 className="font-semibold mb-3 text-amber-400">
                Recommendations ({score.recommendations.length})
              </h3>
              <ul className="space-y-2 text-sm text-zinc-300">
                {score.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <Check className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-2">
        {title}
      </div>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-zinc-800/30 rounded-lg p-4 border border-zinc-800">
      <div className="text-[10px] text-zinc-500 uppercase tracking-wider">
        {label}
      </div>
      <div className="text-3xl font-semibold font-serif text-zinc-100">
        {value}
      </div>
    </div>
  );
}

function Metric({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-zinc-400">{label}</span>
        <span className="text-zinc-300 font-medium">
          {value} / {max}
        </span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-amber-400 to-amber-600"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function scoreColor(total: number): string {
  if (total >= 80) return "text-emerald-400";
  if (total >= 60) return "text-amber-400";
  return "text-rose-400";
}

function cleanDomain(url: string): string {
  return url
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/\/.*$/, "");
}

function formatBriefMarkdown(b: ContentBrief): string {
  const lines: string[] = [];
  lines.push(`# Content brief — ${b.keyword}`);
  lines.push("");
  lines.push(`**Target word count:** ${b.target_word_count} (SERP median: ${b.serp_median_words})`);
  lines.push("");
  if (b.meta_title_suggestion) {
    lines.push(`**Meta title:** ${b.meta_title_suggestion}`);
  }
  if (b.meta_description_suggestion) {
    lines.push(`**Meta description:** ${b.meta_description_suggestion}`);
  }
  lines.push("");
  lines.push("## Recommended H2 sections");
  b.recommended_headings.forEach(h => lines.push(`- ${h}`));
  lines.push("");
  lines.push("## Must-cover entities");
  lines.push(b.must_cover_entities.join(", "));
  lines.push("");
  lines.push("## Questions to answer");
  b.questions_to_answer.forEach(q => lines.push(`- ${q}`));
  return lines.join("\n");
}
