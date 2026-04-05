"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Bot, Globe, Search, Shield, Zap } from "lucide-react";

const features = [
  { icon: Bot, title: "AI-Powered Analysis", desc: "Claude-powered SEO analysis that thinks like a senior strategist, not a checklist." },
  { icon: Search, title: "Keyword Intelligence", desc: "Discover untapped opportunities with AI clustering, intent mapping, and priority scoring." },
  { icon: BarChart3, title: "Rank Tracking", desc: "Daily position monitoring across Google, with SERP feature detection and competitor alerts." },
  { icon: Globe, title: "Technical Audits", desc: "Real PageSpeed Insights integration with AI-prioritized fixes and one-click implementation." },
  { icon: Zap, title: "Content Generation", desc: "AI writes SEO-optimized articles with entity coverage, FAQ blocks, and schema markup built in." },
  { icon: Shield, title: "Competitor Intel", desc: "Reverse-engineer top-ranking pages — entities, headings, questions, backlinks — automatically." },
];

const plans = [
  { name: "Starter", price: "₹1,999", period: "/mo", features: ["1 project", "50 keywords", "5 AI reports/mo", "Basic rank tracking"], cta: "Start free trial" },
  { name: "Growth", price: "₹4,999", period: "/mo", features: ["5 projects", "300 keywords", "Unlimited AI reports", "Content writer", "GSC integration"], cta: "Start free trial", popular: true },
  { name: "Agency", price: "₹14,999", period: "/mo", features: ["25 projects", "2,000 keywords", "White-label reports", "API access", "Team seats"], cta: "Contact sales" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface-1">
      {/* Nav */}
      <nav className="border-b border-zinc-800/50 backdrop-blur-sm sticky top-0 z-50 bg-surface-1/80">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center font-bold text-sm">OR</div>
            <span className="font-semibold text-lg">OMNI-RANK</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm text-zinc-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="btn-ghost text-sm">Log in</Link>
            <Link href="/auth/signup" className="btn-primary text-sm flex items-center gap-1.5">
              Get started <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.08),transparent_60%)]" />
        <div className="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center relative">
          <div className="badge-info mb-6 inline-flex">AI-Powered SEO Platform</div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-[1.1] mb-6">
            Rank <span className="text-brand-400">#1</span> with the
            <br />smartest SEO agent
          </h1>
          <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            OMNI-RANK uses Claude AI to analyze competitors, generate content, track rankings, 
            and execute technical fixes — all from one dashboard. Built for India, works globally.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/auth/signup" className="btn-primary text-base px-8 py-3 flex items-center gap-2">
              Start 14-day free trial <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="#features" className="btn-secondary text-base px-6 py-3">See how it works</Link>
          </div>
          <p className="text-xs text-zinc-500 mt-4">No credit card required · Cancel anytime</p>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4">Everything you need to dominate search</h2>
        <p className="text-zinc-400 text-center mb-16 max-w-xl mx-auto">
          Six AI agents working together to analyze, optimize, and grow your organic traffic.
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div key={f.title} className="card-hover p-6 group">
              <div className="w-10 h-10 rounded-lg bg-brand-500/10 flex items-center justify-center mb-4 group-hover:bg-brand-500/20 transition-colors">
                <f.icon className="w-5 h-5 text-brand-400" />
              </div>
              <h3 className="font-semibold text-base mb-2">{f.title}</h3>
              <p className="text-sm text-zinc-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-5xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4">Simple, transparent pricing</h2>
        <p className="text-zinc-400 text-center mb-16">Start free, scale as you grow. Built for Indian businesses.</p>
        <div className="grid md:grid-cols-3 gap-5">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`card p-6 relative ${plan.popular ? "border-brand-500/50 ring-1 ring-brand-500/20" : ""}`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 badge-info text-xs px-3">Most popular</div>
              )}
              <h3 className="font-semibold text-lg mb-1">{plan.name}</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-3xl font-bold">{plan.price}</span>
                <span className="text-zinc-500 text-sm">{plan.period}</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-zinc-300">
                    <span className="text-brand-400 mt-0.5">✓</span> {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/auth/signup"
                className={plan.popular ? "btn-primary w-full text-center block" : "btn-secondary w-full text-center block"}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 py-12">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-brand-600 flex items-center justify-center font-bold text-xs">OR</div>
            <span className="text-sm text-zinc-400">OMNI-RANK © 2026</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-zinc-500">
            <a href="#" className="hover:text-zinc-300">Privacy</a>
            <a href="#" className="hover:text-zinc-300">Terms</a>
            <a href="#" className="hover:text-zinc-300">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
