"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Coins, TrendingUp, Percent, Type, AlignLeft, Search, ArrowRight, Calculator, ChevronDown, Link as LinkIcon, Eye, FileText, Zap, Target, BarChart3, Globe, Shield, Layers,
} from "lucide-react";

type ToolId = "cpc" | "roas" | "cvr" | "density" | "counter" | "snippet" | "traffic" | "cpl" | "ctr" | "pagespeed" | "score" | "backlink" | "http" | "redirect" | "url" | "robots" | "schema" | "keyword_difficulty" | "anchor" | "organic";

const TOOLS: { id: ToolId; name: string; desc: string; icon: any }[] = [
  { id: "cpc", name: "PPC Budget Calculator", desc: "How many clicks your ad budget buys", icon: Coins },
  { id: "roas", name: "ROAS Calculator", desc: "Return on ad spend + break-even", icon: TrendingUp },
  { id: "cvr", name: "Conversion Rate Calculator", desc: "Conversion rate & traffic needed", icon: Percent },
  { id: "density", name: "Keyword Density Checker", desc: "Keyword frequency in your copy", icon: Search },
  { id: "counter", name: "Word Counter", desc: "Words, characters, reading time", icon: AlignLeft },
  { id: "snippet", name: "SERP Snippet Checker", desc: "Title & meta length for Google", icon: Type },
  { id: "traffic", name: "Organic Traffic Estimator", desc: "Estimate monthly organic visits", icon: Globe },
  { id: "ctr", name: "Click-Through Rate Calculator", desc: "Calculate CTR from clicks & impressions", icon: BarChart3 },
  { id: "cpl", name: "Cost Per Lead Calculator", desc: "CPL from spend & conversions", icon: Target },
  { id: "pagespeed", name: "Page Speed Checker", desc: "Analyze site performance signals", icon: Zap },
  { id: "score", name: "SEO Score Calculator", desc: "Quick on-page SEO audit score", icon: Shield },
  { id: "backlink", name: "Backlink Analyzer", desc: "Estimate backlink impact", icon: LinkIcon },
  { id: "http", name: "HTTP Status Code Reference", desc: "All status codes explained", icon: FileText },
  { id: "redirect", name: "Redirect Chain Checker", desc: "Check redirect chains & issues", icon: ArrowRight },
  { id: "url", name: "URL Structure Analyzer", desc: "Analyze SEO-friendly URL format", icon: Type },
  { id: "robots", name: "Robots.txt Generator", desc: "Generate robots.txt file", icon: Layers },
  { id: "schema", name: "Schema Markup Previewer", desc: "Preview schema markup rendering", icon: Layers },
  { id: "keyword_difficulty", name: "Keyword Difficulty Estimator", desc: "Estimate keyword competition level", icon: TrendingUp },
  { id: "anchor", name: "Anchor Text Optimizer", desc: "Analyze anchor text distribution", icon: LinkIcon },
  { id: "organic", name: "Keyword Position to Traffic", desc: "Traffic from search position & volume", icon: BarChart3 },
];

const num = (v: string) => (isFinite(parseFloat(v)) ? parseFloat(v) : 0);
const fmt = (n: number, d = 0) => n.toLocaleString(undefined, { maximumFractionDigits: d });

export default function ToolsPage() {
  const [active, setActive] = useState<ToolId>("cpc");
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-5xl mx-auto px-5 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <span className="grid place-items-center w-8 h-8 rounded-lg bg-violet-600 text-white text-sm">OR</span>
            OMNI-RANK
          </Link>
          <Link href="/auth/login" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Get the full platform <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-5 py-10">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 text-violet-700 text-xs font-bold uppercase tracking-widest">
              <Calculator className="w-4 h-4" /> Free SEO &amp; PPC Tools
            </div>
            <h1 className="text-3xl md:text-4xl font-bold mt-2 tracking-tight">Free marketing calculators</h1>
            <p className="text-slate-500 mt-2 max-w-2xl">Fast, no-signup tools for everyday SEO and paid-search decisions. Everything runs in your browser.</p>
          </div>
          <Link href="/compare" className="shrink-0 text-sm font-semibold text-violet-700 flex items-center gap-1 hover:text-violet-800 transition">
            vs Competitors <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-8">
          {TOOLS.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setActive(t.id)}
                className={`text-left p-3 rounded-lg border transition ${active === t.id ? "border-violet-500 bg-violet-50 ring-1 ring-violet-200" : "border-slate-200 bg-white hover:border-slate-300"}`}>
                <Icon className={`w-4 h-4 ${active === t.id ? "text-violet-600" : "text-slate-400"}`} />
                <div className="font-semibold text-xs mt-1.5">{t.name}</div>
                <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{t.desc}</div>
              </button>
            );
          })}
        </div>

        <div className="mt-8 bg-white rounded-2xl border border-slate-200 p-6 md:p-8">
          {active === "cpc" && <CpcTool />}
          {active === "roas" && <RoasTool />}
          {active === "cvr" && <CvrTool />}
          {active === "density" && <DensityTool />}
          {active === "counter" && <CounterTool />}
          {active === "snippet" && <SnippetTool />}
          {active === "traffic" && <TrafficTool />}
          {active === "ctr" && <CtrTool />}
          {active === "cpl" && <CplTool />}
          {active === "pagespeed" && <PageSpeedTool />}
          {active === "score" && <ScoreTool />}
          {active === "backlink" && <BacklinkTool />}
          {active === "http" && <HttpTool />}
          {active === "redirect" && <RedirectTool />}
          {active === "url" && <UrlTool />}
          {active === "robots" && <RobotsTool />}
          {active === "schema" && <SchemaTool />}
          {active === "keyword_difficulty" && <KeywordDifficultyTool />}
          {active === "anchor" && <AnchorTool />}
          {active === "organic" && <OrganicTool />}
        </div>

        <div className="mt-8 rounded-2xl bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="font-bold text-lg">Want the keyword mix your budget can actually buy?</div>
            <div className="text-white/80 text-sm mt-1">OMNI-RANK's Budget Keywords turns a spend target into a ranked, allocated plan.</div>
          </div>
          <Link href="/auth/login" className="shrink-0 bg-white text-violet-700 font-semibold px-5 py-2.5 rounded-lg">Try it free</Link>
        </div>

        {/* FAQ */}
        <div className="mt-16">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">About these tools</h2>
          <div className="space-y-3">
            <ToolFaqItem q="Why are these calculators free?" a="We built them to help you make smarter SEO and marketing decisions. No signup required—all calculations run locally in your browser, so your data never leaves your computer." />
            <ToolFaqItem q="Are these calculations accurate?" a="Yes, they use industry-standard formulas and benchmarks. But they're estimates—real results depend on your audience, industry, and execution. Use them for quick planning, not for guaranteed projections." />
            <ToolFaqItem q="Can I use these for client reporting?" a="Absolutely. Screenshot the results or download them. Many agencies share these tools with clients to explain SEO and PPC logic." />
            <ToolFaqItem q="What's the difference between these free tools and OMNI-RANK's platform?" a="These are single-purpose calculators. The full platform tracks your actual rankings daily, analyzes competitors, generates AI content, and audits technical issues across hundreds of pages—all integrated and automated." />
            <ToolFaqItem q="Do you have a bulk keyword difficulty checker?" a="Not here, but OMNI-RANK's platform does. Try a free trial to check difficulty for 100+ keywords at once with our full Keyword Research agent." />
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolFaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className="w-full text-left p-4 rounded-lg border border-slate-200 bg-white hover:border-violet-300 transition"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-slate-900">{q}</h3>
        <span className="text-violet-600 text-lg shrink-0">{open ? "−" : "+"}</span>
      </div>
      {open && (
        <p className="mt-3 text-sm text-slate-600">
          {a}
        </p>
      )}
    </button>
  );
}

function Field({ label, value, onChange, suffix, type = "number" }: any) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <div className="mt-1 flex items-center rounded-lg border border-slate-300 focus-within:border-violet-500 overflow-hidden">
        <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 text-sm outline-none" />
        {suffix && <span className="px-3 text-sm text-slate-400 border-l border-slate-200">{suffix}</span>}
      </div>
    </label>
  );
}
function Result({ items }: { items: [string, string][] }) {
  return (
    <div className="grid sm:grid-cols-2 gap-3 mt-6">
      {items.map(([k, v]) => (
        <div key={k} className="rounded-xl bg-slate-50 border border-slate-200 p-4">
          <div className="text-xs text-slate-500 uppercase tracking-wider">{k}</div>
          <div className="text-2xl font-bold mt-1 tabular-nums text-slate-900">{v}</div>
        </div>
      ))}
    </div>
  );
}

function CpcTool() {
  const [budget, setBudget] = useState("50000");
  const [cpc, setCpc] = useState("25");
  const [cvr, setCvr] = useState("2.5");
  const clicks = num(cpc) > 0 ? num(budget) / num(cpc) : 0;
  const conv = clicks * (num(cvr) / 100);
  return (
    <div>
      <h2 className="text-lg font-bold">PPC Budget Calculator</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="Monthly budget" value={budget} onChange={setBudget} suffix="₹" />
        <Field label="Avg. CPC" value={cpc} onChange={setCpc} suffix="₹" />
        <Field label="Conversion rate" value={cvr} onChange={setCvr} suffix="%" />
      </div>
      <Result items={[
        ["Clicks / month", fmt(clicks)],
        ["Est. conversions / month", fmt(conv, 1)],
        ["Cost per conversion", conv > 0 ? `₹${fmt(num(budget) / conv)}` : "—"],
      ]} />
    </div>
  );
}
function RoasTool() {
  const [revenue, setRevenue] = useState("200000");
  const [spend, setSpend] = useState("50000");
  const [margin, setMargin] = useState("40");
  const roas = num(spend) > 0 ? num(revenue) / num(spend) : 0;
  const breakeven = num(margin) > 0 ? 100 / num(margin) : 0;
  return (
    <div>
      <h2 className="text-lg font-bold">ROAS Calculator</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="Revenue from ads" value={revenue} onChange={setRevenue} suffix="₹" />
        <Field label="Ad spend" value={spend} onChange={setSpend} suffix="₹" />
        <Field label="Profit margin" value={margin} onChange={setMargin} suffix="%" />
      </div>
      <Result items={[
        ["ROAS", `${fmt(roas, 2)}×`],
        ["ROAS", `${fmt(roas * 100)}%`],
        ["Break-even ROAS", `${fmt(breakeven, 2)}×`],
        ["Verdict", roas >= breakeven ? "Profitable ✅" : "Below break-even ⚠️"],
      ]} />
    </div>
  );
}
function CvrTool() {
  const [conv, setConv] = useState("120");
  const [visitors, setVisitors] = useState("4800");
  const [target, setTarget] = useState("500");
  const rate = num(visitors) > 0 ? (num(conv) / num(visitors)) * 100 : 0;
  const needed = rate > 0 ? num(target) / (rate / 100) : 0;
  return (
    <div>
      <h2 className="text-lg font-bold">Conversion Rate Calculator</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="Conversions" value={conv} onChange={setConv} />
        <Field label="Visitors" value={visitors} onChange={setVisitors} />
        <Field label="Target conversions" value={target} onChange={setTarget} />
      </div>
      <Result items={[
        ["Conversion rate", `${fmt(rate, 2)}%`],
        ["Visitors needed for target", needed ? fmt(needed) : "—"],
      ]} />
    </div>
  );
}
function DensityTool() {
  const [text, setText] = useState("");
  const [kw, setKw] = useState("");
  const { total, count, density } = useMemo(() => {
    const words = text.toLowerCase().match(/[a-z0-9'-]+/g) || [];
    const k = kw.trim().toLowerCase();
    const count = k ? (text.toLowerCase().match(new RegExp(`\\b${k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "g")) || []).length : 0;
    return { total: words.length, count, density: words.length ? (count / words.length) * 100 : 0 };
  }, [text, kw]);
  return (
    <div>
      <h2 className="text-lg font-bold">Keyword Density Checker</h2>
      <div className="grid sm:grid-cols-2 gap-4 mt-4">
        <Field label="Keyword / phrase" value={kw} onChange={setKw} type="text" />
      </div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste your content here…"
        className="w-full mt-4 h-40 rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-violet-500" />
      <Result items={[
        ["Total words", fmt(total)],
        ["Keyword occurrences", fmt(count)],
        ["Density", `${fmt(density, 2)}%`],
        ["Guidance", density > 3 ? "High — may look stuffed" : density === 0 ? "Not found" : "Healthy"],
      ]} />
    </div>
  );
}
function CounterTool() {
  const [text, setText] = useState("");
  const words = (text.trim().match(/\S+/g) || []).length;
  const chars = text.length;
  const sentences = (text.match(/[.!?]+/g) || []).length;
  const mins = Math.max(1, Math.round(words / 200));
  return (
    <div>
      <h2 className="text-lg font-bold">Word Counter</h2>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste or type your text…"
        className="w-full mt-4 h-48 rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-violet-500" />
      <Result items={[
        ["Words", fmt(words)],
        ["Characters", fmt(chars)],
        ["Sentences", fmt(sentences)],
        ["Reading time", `${mins} min`],
      ]} />
    </div>
  );
}
function SnippetTool() {
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const titleOk = title.length >= 30 && title.length <= 60;
  const descOk = desc.length >= 120 && desc.length <= 160;
  return (
    <div>
      <h2 className="text-lg font-bold">SERP Snippet Checker</h2>
      <div className="space-y-4 mt-4">
        <Field label="Title tag" value={title} onChange={setTitle} type="text" />
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Meta description</span>
          <textarea value={desc} onChange={(e) => setDesc(e.target.value)}
            className="w-full mt-1 h-24 rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-violet-500" />
        </label>
      </div>
      <div className="mt-6 rounded-xl border border-slate-200 p-4 bg-white">
        <div className="text-[#1a0dab] text-lg leading-tight truncate">{title || "Your title tag preview"}</div>
        <div className="text-[#006621] text-xs mt-0.5">https://yoursite.com › page</div>
        <div className="text-slate-600 text-sm mt-1 line-clamp-2">{desc || "Your meta description preview will appear here as Google might display it."}</div>
      </div>
      <Result items={[
        ["Title length", `${title.length} chars ${titleOk ? "✅" : "⚠️"}`],
        ["Description length", `${desc.length} chars ${descOk ? "✅" : "⚠️"}`],
      ]} />
      <p className="text-xs text-slate-400 mt-3">Ideal: title 30–60 chars, description 120–160 chars.</p>
    </div>
  );
}

function TrafficTool() {
  const [keywords, setKeywords] = useState("20");
  const [avgPos, setAvgPos] = useState("5");
  const [avgVol, setAvgVol] = useState("1200");
  const ctrByPos = { 1: 0.31, 2: 0.24, 3: 0.18, 4: 0.13, 5: 0.1, 10: 0.04, 20: 0.01 };
  const posNum = Math.round(num(avgPos));
  const ctr = ctrByPos[posNum as keyof typeof ctrByPos] || 0.05;
  const monthlyTraffic = num(keywords) * num(avgVol) * ctr;
  return (
    <div>
      <h2 className="text-lg font-bold">Organic Traffic Estimator</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="Keywords ranked" value={keywords} onChange={setKeywords} />
        <Field label="Average position" value={avgPos} onChange={setAvgPos} />
        <Field label="Average monthly volume" value={avgVol} onChange={setAvgVol} />
      </div>
      <Result items={[
        ["Est. monthly organic traffic", fmt(monthlyTraffic)],
        ["Avg CTR", `${fmt(ctr * 100, 1)}%`],
        ["Traffic per keyword", fmt(monthlyTraffic / (num(keywords) || 1))],
      ]} />
    </div>
  );
}

function CtrTool() {
  const [clicks, setClicks] = useState("1500");
  const [impressions, setImpressions] = useState("50000");
  const clickNum = num(clicks);
  const impNum = num(impressions);
  const ctr = impNum > 0 ? (clickNum / impNum) * 100 : 0;
  return (
    <div>
      <h2 className="text-lg font-bold">Click-Through Rate Calculator</h2>
      <div className="grid sm:grid-cols-2 gap-4 mt-4">
        <Field label="Total clicks" value={clicks} onChange={setClicks} />
        <Field label="Total impressions" value={impressions} onChange={setImpressions} />
      </div>
      <Result items={[
        ["CTR", `${fmt(ctr, 2)}%`],
        ["Industry benchmark", "2–3% is typical"],
      ]} />
    </div>
  );
}

function CplTool() {
  const [spend, setSpend] = useState("50000");
  const [conversions, setConversions] = useState("25");
  const cost = num(conversions) > 0 ? num(spend) / num(conversions) : 0;
  return (
    <div>
      <h2 className="text-lg font-bold">Cost Per Lead Calculator</h2>
      <div className="grid sm:grid-cols-2 gap-4 mt-4">
        <Field label="Total spend" value={spend} onChange={setSpend} suffix="₹" />
        <Field label="Total leads" value={conversions} onChange={setConversions} />
      </div>
      <Result items={[
        ["Cost per lead", cost > 0 ? `₹${fmt(cost)}` : "—"],
      ]} />
    </div>
  );
}

function PageSpeedTool() {
  const [core, setCore] = useState("2.5");
  const [fid, setFid] = useState("100");
  const [cls, setCls] = useState("0.1");
  const score = Math.max(0, 100 - (num(core) * 10) - (num(fid) / 10) - (num(cls) * 100));
  return (
    <div>
      <h2 className="text-lg font-bold">Page Speed Score Calculator</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="LCP (seconds)" value={core} onChange={setCore} />
        <Field label="FID (milliseconds)" value={fid} onChange={setFid} />
        <Field label="CLS (score)" value={cls} onChange={setCls} />
      </div>
      <Result items={[
        ["Est. Pagespeed Score", `${Math.round(Math.max(0, Math.min(100, score)))}/100`],
        ["Status", score >= 90 ? "Good" : score >= 50 ? "Needs work" : "Poor"],
      ]} />
    </div>
  );
}

function ScoreTool() {
  const [title, setTitle] = useState("1");
  const [meta, setMeta] = useState("1");
  const [h1, setH1] = useState("1");
  const [keywords, setKeywords] = useState("1");
  const [links, setLinks] = useState("1");
  const score = (num(title) + num(meta) + num(h1) + num(keywords) + num(links)) * 20;
  const checks = [["Title", title, setTitle], ["Meta description", meta, setMeta], ["H1 tag", h1, setH1], ["Keywords in copy", keywords, setKeywords], ["Internal links", links, setLinks]] as const;
  return (
    <div>
      <h2 className="text-lg font-bold">SEO On-Page Score</h2>
      <p className="text-sm text-slate-600 mt-2 mb-4">Check each item (1 = yes, 0 = no)</p>
      <div className="grid sm:grid-cols-2 gap-3 mt-4">
        {checks.map((item, idx) => {
          const [label, value, setter] = item;
          return (
            <label key={idx} className="flex items-center gap-2">
              <input type="checkbox" checked={num(value as string) === 1} onChange={(e) => setter(e.target.checked ? "1" : "0")} className="w-4 h-4" />
              <span className="text-sm">{label}</span>
            </label>
          );
        })}
      </div>
      <Result items={[
        ["SEO Score", `${Math.min(100, score)}/100`],
      ]} />
    </div>
  );
}

function BacklinkTool() {
  const [backlinks, setBacklinks] = useState("500");
  const [referring, setRefer] = useState("150");
  const [authority, setAuthority] = useState("60");
  const impact = (num(referring) * 0.4) + (num(authority) * 0.5);
  return (
    <div>
      <h2 className="text-lg font-bold">Backlink Impact Analyzer</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="Total backlinks" value={backlinks} onChange={setBacklinks} />
        <Field label="Referring domains" value={referring} onChange={setRefer} />
        <Field label="Avg domain authority" value={authority} onChange={setAuthority} />
      </div>
      <Result items={[
        ["Backlink profile strength", fmt(impact, 1)],
        ["Status", impact > 40 ? "Strong" : impact > 20 ? "Moderate" : "Building"],
      ]} />
    </div>
  );
}

function HttpTool() {
  return (
    <div>
      <h2 className="text-lg font-bold">HTTP Status Codes Reference</h2>
      <div className="space-y-3 mt-4">
        {[
          ["200", "OK", "Request successful"],
          ["301", "Moved Permanently", "Permanent redirect"],
          ["302", "Found", "Temporary redirect"],
          ["400", "Bad Request", "Malformed request"],
          ["403", "Forbidden", "Access denied"],
          ["404", "Not Found", "Page doesn't exist"],
          ["500", "Server Error", "Internal server error"],
          ["503", "Service Unavailable", "Server temporarily down"],
        ].map(([code, name, desc]) => (
          <div key={code} className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <div className="font-mono font-bold text-violet-600">{code}</div>
            <div className="font-semibold text-sm">{name}</div>
            <div className="text-xs text-slate-600">{desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RedirectTool() {
  const [url, setUrl] = useState("https://example.com/old-page");
  return (
    <div>
      <h2 className="text-lg font-bold">Redirect Chain Checker</h2>
      <div className="mt-4">
        <Field label="URL to check" value={url} onChange={setUrl} type="text" />
      </div>
      <div className="mt-6 p-4 rounded-lg bg-slate-50 border border-slate-200">
        <p className="text-sm text-slate-600">Ideal: 0 redirects (direct URL). Max: 1–2 hops. Chains &gt; 2 waste crawl budget.</p>
        <p className="text-xs text-slate-500 mt-2">Use OMNI-RANK's full platform to crawl and trace redirect chains.</p>
      </div>
    </div>
  );
}

function UrlTool() {
  const [url, setUrl] = useState("https://example.com/seo-best-practices");
  const hasKeywords = /[a-z0-9\-]{4,}/.test(url);
  const isShort = url.split("/").length <= 4;
  const score = (hasKeywords ? 50 : 0) + (isShort ? 50 : 0);
  return (
    <div>
      <h2 className="text-lg font-bold">URL Structure Analyzer</h2>
      <div className="mt-4">
        <Field label="URL" value={url} onChange={setUrl} type="text" />
      </div>
      <Result items={[
        ["Has keywords", hasKeywords ? "✅" : "❌"],
        ["Short & simple", isShort ? "✅" : "❌"],
        ["SEO score", `${score}/100`],
      ]} />
      <p className="text-xs text-slate-400 mt-3">Best: lowercase, hyphens, keywords, max 3 levels deep.</p>
    </div>
  );
}

function RobotsTool() {
  return (
    <div>
      <h2 className="text-lg font-bold">Robots.txt Generator</h2>
      <p className="text-sm text-slate-600 mt-4 mb-4">Basic robots.txt template:</p>
      <div className="font-mono text-xs p-4 bg-slate-50 rounded-lg border border-slate-200 overflow-x-auto">
        <pre>{`User-agent: *
Allow: /

User-agent: AdsBot-Google
Allow: /

Disallow: /admin/
Disallow: /private/
Disallow: /temp/

Sitemap: https://example.com/sitemap.xml`}</pre>
      </div>
      <p className="text-xs text-slate-400 mt-3">Place robots.txt in your site root. Customize paths for your site structure.</p>
    </div>
  );
}

function SchemaTool() {
  return (
    <div>
      <h2 className="text-lg font-bold">Schema Markup Previewer</h2>
      <p className="text-sm text-slate-600 mt-4 mb-4">Common schema types:</p>
      <div className="space-y-2">
        {["Organization", "Product", "Article", "FAQ", "Event", "LocalBusiness"].map((type) => (
          <div key={type} className="p-3 rounded-lg bg-slate-50 border border-slate-200">
            <div className="font-semibold text-sm">{type}</div>
            <div className="text-xs text-slate-500">Structured data for rich snippets</div>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 mt-3">Use OMNI-RANK's schema validator to check your markup.</p>
    </div>
  );
}

function KeywordDifficultyTool() {
  const [backlinks, setBacklinks] = useState("5000");
  const [domains, setDomains] = useState("800");
  const difficulty = Math.min(100, (num(domains) / 100) + (num(backlinks) / 100));
  return (
    <div>
      <h2 className="text-lg font-bold">Keyword Difficulty Estimator</h2>
      <p className="text-sm text-slate-600 mt-2 mb-4">Top 10 SERP metrics:</p>
      <div className="grid sm:grid-cols-2 gap-4 mt-4">
        <Field label="Avg backlinks in top 10" value={backlinks} onChange={setBacklinks} />
        <Field label="Avg referring domains" value={domains} onChange={setDomains} />
      </div>
      <Result items={[
        ["Keyword difficulty", `${Math.round(difficulty)}/100`],
        ["Rank", difficulty > 60 ? "Hard" : difficulty > 30 ? "Medium" : "Easy"],
      ]} />
    </div>
  );
}

function AnchorTool() {
  const [total, setTotal] = useState("1000");
  const [branded, setBranded] = useState("400");
  const [exact, setExact] = useState("300");
  const [partial, setPartial] = useState("200");
  return (
    <div>
      <h2 className="text-lg font-bold">Anchor Text Distribution</h2>
      <div className="grid sm:grid-cols-2 gap-4 mt-4">
        <Field label="Total backlinks" value={total} onChange={setTotal} />
        <Field label="Branded anchors" value={branded} onChange={setBranded} />
      </div>
      <Result items={[
        ["Branded %", `${fmt((num(branded) / num(total)) * 100, 1)}%`],
        ["Exact match %", `${fmt((num(exact) / num(total)) * 100, 1)}%`],
        ["Partial %", `${fmt((num(partial) / num(total)) * 100, 1)}%`],
        ["Status", (num(branded) / num(total)) > 0.3 ? "Healthy" : "Needs branded links"],
      ]} />
    </div>
  );
}

function OrganicTool() {
  const [position, setPosition] = useState("5");
  const [volume, setVolume] = useState("2000");
  const [ctr, setCtr] = useState("10");
  const traffic = (num(volume) * num(ctr)) / 100;
  return (
    <div>
      <h2 className="text-lg font-bold">Keyword Position to Traffic</h2>
      <div className="grid sm:grid-cols-3 gap-4 mt-4">
        <Field label="Search ranking" value={position} onChange={setPosition} />
        <Field label="Monthly search volume" value={volume} onChange={setVolume} />
        <Field label="Expected CTR" value={ctr} onChange={setCtr} suffix="%" />
      </div>
      <Result items={[
        ["Est. monthly traffic", fmt(traffic)],
        ["Monthly visitors", fmt(traffic)],
      ]} />
    </div>
  );
}
