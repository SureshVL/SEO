"use client";

import Link from "next/link";
import { ArrowRight, Check, X } from "lucide-react";

const features = [
  { category: "Core SEO Tools", items: [
    { name: "Keyword Research", omni: true, semrush: true, ahrefs: true, rankiq: true },
    { name: "Rank Tracking", omni: true, semrush: true, ahrefs: true, rankiq: true },
    { name: "Technical Audit", omni: true, semrush: true, ahrefs: true, rankiq: false },
    { name: "Competitor Analysis", omni: true, semrush: true, ahrefs: true, rankiq: false },
    { name: "Content Research", omni: true, semrush: true, ahrefs: true, rankiq: false },
  ]},
  { category: "AI Features", items: [
    { name: "AI-Powered Strategy", omni: true, semrush: false, ahrefs: false, rankiq: false },
    { name: "AI Content Writing", omni: true, semrush: false, ahrefs: false, rankiq: false },
    { name: "Auto-Fix Recommendations", omni: true, semrush: false, ahrefs: false, rankiq: false },
    { name: "AI Competitor Insights", omni: true, semrush: false, ahrefs: false, rankiq: false },
  ]},
  { category: "Integration", items: [
    { name: "GitHub Integration", omni: true, semrush: false, ahrefs: false, rankiq: false },
    { name: "API Access", omni: true, semrush: true, ahrefs: true, rankiq: false },
    { name: "Google Analytics 4", omni: true, semrush: true, ahrefs: true, rankiq: true },
    { name: "Google Search Console", omni: true, semrush: true, ahrefs: true, rankiq: true },
  ]},
  { category: "Reporting", items: [
    { name: "White-label Reports", omni: true, semrush: true, ahrefs: true, rankiq: false },
    { name: "Custom Dashboards", omni: true, semrush: true, ahrefs: true, rankiq: false },
    { name: "Automated Email Reports", omni: true, semrush: true, ahrefs: true, rankiq: false },
  ]},
  { category: "Pricing & Plans", items: [
    { name: "Free Tier", omni: true, semrush: false, ahrefs: false, rankiq: true },
    { name: "Pay-as-you-go", omni: false, semrush: false, ahrefs: false, rankiq: false },
    { name: "Annual Discount", omni: true, semrush: true, ahrefs: true, rankiq: true },
    { name: "India-first Pricing (₹)", omni: true, semrush: false, ahrefs: false, rankiq: false },
  ]},
];

const pricing = [
  { tool: "OMNI-RANK", starter: "₹1,999/mo", growth: "₹4,999/mo", pro: "₹9,999/mo", note: "Free tier available" },
  { tool: "Semrush", starter: "$119/mo", growth: "$229/mo", pro: "$449/mo", note: "US pricing" },
  { tool: "Ahrefs", starter: "$99/mo", growth: "$199/mo", pro: "$399/mo", note: "US pricing" },
  { tool: "RankIQ", starter: "$79/mo", growth: "$149/mo", pro: "$249/mo", note: "US pricing" },
];

export default function ComparePage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <span className="grid place-items-center w-8 h-8 rounded-lg bg-violet-600 text-white text-sm">OR</span>
            OMNI-RANK
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/tools" className="text-sm text-slate-600 hover:text-slate-900">Free Tools</Link>
            <Link href="/" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
              Back to home <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-5 py-12">
        <div className="mb-12 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4">OMNI-RANK vs Competitors</h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Built for Indian SEO teams. AI-first. Transparent pricing. No per-report overages.
          </p>
        </div>

        {/* Features Comparison */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden mb-12">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900 w-48">Feature</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-violet-700">OMNI-RANK</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-slate-600">Semrush</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-slate-600">Ahrefs</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold text-slate-600">RankIQ</th>
                </tr>
              </thead>
              <tbody>
                {features.map((section, idx) => (
                  <tbody key={idx}>
                    <tr className="border-t-2 border-slate-100 bg-slate-50">
                      <td colSpan={5} className="px-6 py-2 text-xs font-bold uppercase tracking-wider text-slate-600">
                        {section.category}
                      </td>
                    </tr>
                    {section.items.map((feature, fidx) => (
                      <tr key={fidx} className="border-b border-slate-100">
                        <td className="px-6 py-3 text-sm text-slate-900">{feature.name}</td>
                        <td className="px-6 py-3 text-center">
                          {feature.omni ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : <X className="w-5 h-5 text-slate-300 mx-auto" />}
                        </td>
                        <td className="px-6 py-3 text-center">
                          {feature.semrush ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : <X className="w-5 h-5 text-slate-300 mx-auto" />}
                        </td>
                        <td className="px-6 py-3 text-center">
                          {feature.ahrefs ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : <X className="w-5 h-5 text-slate-300 mx-auto" />}
                        </td>
                        <td className="px-6 py-3 text-center">
                          {feature.rankiq ? <Check className="w-5 h-5 text-green-600 mx-auto" /> : <X className="w-5 h-5 text-slate-300 mx-auto" />}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pricing Comparison */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden mb-12">
          <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
            <h2 className="text-lg font-bold text-slate-900">Pricing Comparison</h2>
            <p className="text-sm text-slate-600 mt-1">Starting price for Starter / Growth / Pro tiers</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-white border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Platform</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold">Starter</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold">Growth</th>
                  <th className="px-6 py-3 text-center text-sm font-semibold">Pro</th>
                  <th className="px-6 py-3 text-left text-sm text-slate-600">Note</th>
                </tr>
              </thead>
              <tbody>
                {pricing.map((row, idx) => (
                  <tr key={idx} className={`border-b border-slate-100 ${row.tool === "OMNI-RANK" ? "bg-violet-50" : ""}`}>
                    <td className={`px-6 py-3 font-semibold ${row.tool === "OMNI-RANK" ? "text-violet-700" : "text-slate-900"}`}>{row.tool}</td>
                    <td className="px-6 py-3 text-center text-sm font-mono">{row.starter}</td>
                    <td className="px-6 py-3 text-center text-sm font-mono">{row.growth}</td>
                    <td className="px-6 py-3 text-center text-sm font-mono">{row.pro}</td>
                    <td className="px-6 py-3 text-sm text-slate-600">{row.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Why OMNI-RANK */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {[
            { title: "AI-First Architecture", desc: "Every insight is Claude-powered. Real reasoning, not heuristics." },
            { title: "India-First Pricing", desc: "₹/month, not $/month. Built for Indian agencies and in-house teams." },
            { title: "No Report Overages", desc: "Unlimited monthly reports at any tier. Semrush charges per report." },
            { title: "GitHub Integration", desc: "Direct schema fixes and content suggestions to your repo." },
            { title: "Transparent Costs", desc: "Per-day SERP budgets. No surprise overage charges." },
            { title: "Free Tier Forever", desc: "25 daily SERP checks. Perfect for side projects and learning." },
          ].map((item, idx) => (
            <div key={idx} className="p-6 rounded-xl border border-slate-200 bg-white hover:border-violet-300 transition">
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-2xl p-8 md:p-12 text-white text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to switch?</h2>
          <p className="text-white/90 mb-6 max-w-2xl mx-auto">Start with our free tier. No credit card, no time limit.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-violet-700 font-semibold px-8 py-3 rounded-lg hover:bg-slate-50 transition">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
