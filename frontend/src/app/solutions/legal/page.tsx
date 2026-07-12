"use client";

import Link from "next/link";
import { ArrowRight, Scale, TrendingUp, Shield, Zap } from "lucide-react";

export default function LegalSolutionPage() {
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

      <section className="bg-gradient-to-br from-blue-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            Own legal search.<br />
            Win high-intent clients.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            Legal buyers search with intent: "divorce lawyer near me", "DUI attorney", "patent filing cost". They're ready to hire. Track these high-value keywords daily and know exactly where you rank vs. competitors.
          </p>
          <Link href="/auth/signup" className="btn-primary inline-flex items-center gap-2">
            Free keyword audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">Legal SEO Blindspots</h2>
            {[
              { title: "Local Intent Lost", desc: "\"Divorce lawyer\" vs. \"divorce lawyer in Chicago\" rank completely differently. You can't track location variants." },
              { title: "Practice Area Rankings Scattered", desc: "Multiple practice areas (litigation, IP, employment). You can't see which areas drive most clients." },
              { title: "Review Schema Invisible", desc: "Competitors' Google reviews and testimonials show prominently. Yours don't. Why?" },
              { title: "Cost/Process Questions Unranked", desc: "\"How much does a trademark cost?\" and \"How to file bankruptcy?\" are high-intent but you don't rank them." },
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
            <h2 className="text-3xl font-bold mb-6 text-slate-900">OMNI-RANK Solutions</h2>
            {[
              { title: "Location + Practice Area Tracking", desc: "Track \"bankruptcy lawyer Brooklyn\" separately from \"bankruptcy lawyer Queens\". Local intent matters." },
              { title: "Practice Area Rankings", desc: "See which practice areas drive most client inquiries. Allocate content budget accordingly." },
              { title: "Review Schema Optimization", desc: "Audit why competitors' reviews rank but yours don't. Fix schema, improve CTR." },
              { title: "Educational Content Rankings", desc: "Rank process/cost questions (\"How much does X cost?\"). Position as trusted advisor, not just advertiser." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-blue-600 font-bold">✓</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-blue-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12 text-center">Legal Practice Results</h2>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">287%</div>
              <div className="text-sm text-slate-300">Qualified client inquiries increase</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">1,200+</div>
              <div className="text-sm text-slate-300">High-intent legal keywords tracked</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">6 weeks</div>
              <div className="text-sm text-slate-300">To rank #1-3 for top 50 keywords</div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">Built for Law Firms</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            { icon: <Scale />, title: "Practice Area Segmentation", desc: "Track Bankruptcy, Immigration, Family Law, IP separately. Know which areas drive cases." },
            { icon: <TrendingUp />, title: "Local Market Dominance", desc: "\"Lawyer near me\" variations. Own your metro area, not just generic keywords." },
            { icon: <Shield />, title: "Trust Signals Audit", desc: "Bar association status, certifications, testimonials. Know what competitors showcase." },
            { icon: <Zap />, title: "Educational Content Ranking", desc: "Make \"how to\" and \"cost\" questions rank. Position as trusted advisor." },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 hover:border-blue-300 transition">
              <div className="text-blue-600 mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to win high-intent legal clients?</h2>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold px-8 py-3 rounded-lg">
            Get started free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
