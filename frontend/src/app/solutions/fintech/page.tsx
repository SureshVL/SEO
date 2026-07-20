"use client";

import Link from "next/link";
import { ArrowRight, CreditCard, TrendingUp, Lock, Zap } from "lucide-react";

export default function FintechSolutionPage() {
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

      <section className="bg-gradient-to-br from-amber-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            Rank for financial intent.<br />
            Own trust + comparison.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            Fintech buyers search for specific problems and compare solutions obsessively. Track comparison keywords, trust signals, compliance messaging, and security-related searches — where your biggest competitors fight hardest.
          </p>
          <Link href="/auth/signup" className="btn-primary inline-flex items-center gap-2">
            Free competitive analysis <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">Fintech Ranking Barriers</h2>
            {[
              { title: "Comparison Keywords Lost", desc: "Competitors own vs. keyword space. 'PayPal vs. Stripe' — are you ranking?" },
              { title: "Trust + Security Invisible", desc: "Compliance certifications matter but don't rank. Competitors have better schema." },
              { title: "Regulatory Language Penalized", desc: "Your privacy & compliance pages are too legal. Google doesn't index them for search intent." },
              { title: "Financial Advisor Disconnect", desc: "Advisor vs. robo-advisor rankings. You can't see keyword intent shift." },
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
            <h2 className="text-3xl font-bold mb-6 text-slate-900">OMNI-RANK Fintech Focus</h2>
            {[
              { title: "Comparison Keyword Tracking", desc: "Own 'vs.' keywords, comparisons, benchmarks. Beat competitors on buyer intent." },
              { title: "Trust Signal Auditing", desc: "Audit compliance certs, security badges, privacy markup. Know what competitors showcase." },
              { title: "Regulatory Content Ranking", desc: "Make compliance pages rank. Reframe legal as buyer education, not liability." },
              { title: "Intent Clustering", desc: "Problem-focused (how to), comparison (best), solution-focused (alternative to X)." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-amber-600 font-bold">✓</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-amber-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12 text-center">Fintech Results</h2>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-amber-400 mb-2">420%</div>
              <div className="text-sm text-slate-300">Comparison keyword rankings gained</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-amber-400 mb-2">67%</div>
              <div className="text-sm text-slate-300">Fintech buyer intent keywords owned</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-amber-400 mb-2">8 weeks</div>
              <div className="text-sm text-slate-300">Time to rank for top 50 competitor keywords</div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">Fintech-Specific Features</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            { icon: <CreditCard />, title: "Comparison Keyword Dominance", desc: "Track vs., alternatives, comparison queries. Own the buying decision moment." },
            { icon: <Lock />, title: "Trust & Security Signals", desc: "Audit SSL, security certifications, privacy badges. Know what competitors showcase." },
            { icon: <TrendingUp />, title: "Intent-Based Clustering", desc: "Problem-focused, solution-focused, comparison keywords. Know buyer stage." },
            { icon: <Zap />, title: "Regulatory Content SEO", desc: "Make compliance pages rank. Reframe legal language as buyer education." },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 hover:border-amber-300 transition">
              <div className="text-amber-600 mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-amber-600 to-orange-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to win fintech buyers?</h2>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-amber-700 font-semibold px-8 py-3 rounded-lg">
            Get started free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
