"use client";

import Link from "next/link";
import { ArrowRight, Briefcase, TrendingUp, Users, Zap } from "lucide-react";

export default function B2BSolutionPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-purple-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            Become the thought leader.<br />
            Rank above consultancies.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            B2B searches are problem-focused + role-specific. CTOs search differently than CFOs. OMNI-RANK segments your keywords by buyer role and shows you exactly where competitors are winning mindshare.
          </p>
          <Link href="/auth/signup" className="btn-primary inline-flex items-center gap-2">
            Free competitive landscape audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">B2B SEO Challenges</h2>
            {[
              { title: "Long Sales Cycle Confusion", desc: "Sales cycle is 6+ months. You can't tell which keywords drive real opportunities." },
              { title: "Role-Based Intent Invisible", desc: "CTO, CFO, VP Sales all search for same solutions differently. You rank for one, miss the others." },
              { title: "Consultancy Dominance", desc: "Every solution keyword is flooded with Big 4 case studies. How do you compete?" },
              { title: "Thought Leadership Gap", desc: "Competitors publish 10x more research. You can't see what's actually getting traffic." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-red-600 font-bold">✕</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">OMNI-RANK B2B Strategy</h2>
            {[
              { title: "Buyer Persona Segmentation", desc: "Cluster keywords by buyer role (CTO, CFO, VP Sales). See where each decision-maker searches." },
              { title: "Consultancy Benchmarking", desc: "Know exactly what McKinsey, BCG, Deloitte rank for. Find undefended keywords." },
              { title: "Thought Leadership ROI", desc: "Publish research. Track which pieces drive rankings + backlinks + buyer conversations." },
              { title: "Sales Cycle Visibility", desc: "Map keywords to sales stage (awareness, consideration, decision). Know where pipeline starts." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-purple-600 font-bold">✓</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-purple-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12 text-center">B2B Enterprise Results</h2>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-purple-400 mb-2">512%</div>
              <div className="text-sm text-slate-300">Enterprise keyword rankings (12 months)</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-400 mb-2">218</div>
              <div className="text-sm text-slate-300">Avg. high-intent B2B keywords ranking</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-purple-400 mb-2">34%</div>
              <div className="text-sm text-slate-300">Sales pipeline influence (attributed)</div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">Built for Enterprise B2B</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            { icon: <Briefcase />, title: "Buyer Persona Segmentation", desc: "Map keywords to CTO, CFO, VP Sales, CEO. See where each searches." },
            { icon: <Users />, title: "Consultancy Competitive Intelligence", desc: "Benchmark vs. McKinsey, BCG, Deloitte. Find undefended authority keywords." },
            { icon: <TrendingUp />, title: "Thought Leadership Tracking", desc: "Publish research. Track which pieces rank, get backlinks, and drive leads." },
            { icon: <Zap />, title: "Sales Cycle Mapping", desc: "Map keywords to awareness, consideration, decision. Know where your pipeline starts." },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 hover:border-purple-300 transition">
              <div className="text-purple-600 mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to own B2B thought leadership?</h2>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-purple-700 font-semibold px-8 py-3 rounded-lg">
            Get started free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
