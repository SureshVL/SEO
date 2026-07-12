"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Coins, TrendingUp, Percent, Type, AlignLeft, Search, ArrowRight, Calculator,
} from "lucide-react";

type ToolId = "cpc" | "roas" | "cvr" | "density" | "counter" | "snippet";

const TOOLS: { id: ToolId; name: string; desc: string; icon: any }[] = [
  { id: "cpc", name: "PPC Budget Calculator", desc: "How many clicks your ad budget buys", icon: Coins },
  { id: "roas", name: "ROAS Calculator", desc: "Return on ad spend + break-even", icon: TrendingUp },
  { id: "cvr", name: "Conversion Rate Calculator", desc: "Conversion rate & traffic needed", icon: Percent },
  { id: "density", name: "Keyword Density Checker", desc: "Keyword frequency in your copy", icon: Search },
  { id: "counter", name: "Word Counter", desc: "Words, characters, reading time", icon: AlignLeft },
  { id: "snippet", name: "SERP Snippet Checker", desc: "Title & meta length for Google", icon: Type },
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
        <div className="flex items-center gap-2 text-violet-700 text-xs font-bold uppercase tracking-widest">
          <Calculator className="w-4 h-4" /> Free SEO &amp; PPC Tools
        </div>
        <h1 className="text-3xl md:text-4xl font-bold mt-2 tracking-tight">Free marketing calculators</h1>
        <p className="text-slate-500 mt-2 max-w-2xl">Fast, no-signup tools for everyday SEO and paid-search decisions. Everything runs in your browser.</p>

        <div className="grid md:grid-cols-3 gap-3 mt-8">
          {TOOLS.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setActive(t.id)}
                className={`text-left p-4 rounded-xl border transition ${active === t.id ? "border-violet-500 bg-violet-50 ring-1 ring-violet-200" : "border-slate-200 bg-white hover:border-slate-300"}`}>
                <Icon className={`w-5 h-5 ${active === t.id ? "text-violet-600" : "text-slate-400"}`} />
                <div className="font-semibold text-sm mt-2">{t.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t.desc}</div>
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
        </div>

        <div className="mt-8 rounded-2xl bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="font-bold text-lg">Want the keyword mix your budget can actually buy?</div>
            <div className="text-white/80 text-sm mt-1">OMNI-RANK's Budget Keywords turns a spend target into a ranked, allocated plan.</div>
          </div>
          <Link href="/auth/login" className="shrink-0 bg-white text-violet-700 font-semibold px-5 py-2.5 rounded-lg">Try it free</Link>
        </div>
      </div>
    </div>
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
