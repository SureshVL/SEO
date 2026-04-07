"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Bot, Globe, Search, Shield, Zap } from "lucide-react";

const features = [
  { icon: Bot, title: "AI Research Engine", desc: "Claude & Gemini analyze competitors, decode intent, and generate strategy — like having a senior SEO on call 24/7." },
  { icon: Search, title: "Keyword Intelligence", desc: "Real search volume, CPC, difficulty via DataForSEO. AI clusters keywords by intent and maps content plans." },
  { icon: BarChart3, title: "Daily Rank Tracking", desc: "Position monitoring with SERP feature detection. Know when competitors move before they do." },
  { icon: Globe, title: "Backlink Intelligence", desc: "Full backlink profiles, referring domains, anchor analysis. Find link opportunities your competitors missed." },
  { icon: Shield, title: "Technical Audits", desc: "PageSpeed, Core Web Vitals, schema validation, crawl errors. AI prioritizes what actually moves rankings." },
  { icon: Zap, title: "Content Studio", desc: "AI writes SEO content with entity coverage, FAQ blocks, and E-E-A-T signals — calibrated against real SERP data." },
];

const plans = [
  { name: "Starter", price: "\u20B91,999", features: ["1 project", "50 keywords", "5 AI reports/mo", "Daily rank tracking"], cta: "Start free trial" },
  { name: "Growth", price: "\u20B94,999", features: ["5 projects", "300 keywords", "Unlimited reports", "Backlink monitoring", "Content studio", "Competitor alerts"], cta: "Start free trial", popular: true },
  { name: "Agency", price: "\u20B914,999", features: ["25 projects", "2,000 keywords", "White-label reports", "API access", "Team seats (10)", "Priority support"], cta: "Contact sales" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen grain" style={{ background: "#110f0d" }}>
      {/* Nav */}
      <nav style={{ borderBottom: "1px solid rgba(200, 180, 150, 0.06)", background: "rgba(17, 15, 13, 0.9)", backdropFilter: "blur(12px)" }} className="sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-serif font-bold text-sm" style={{ background: "linear-gradient(135deg, #c87941, #8b5a2b)", color: "#faf8f5" }}>OR</div>
            <span className="font-serif text-lg" style={{ color: "#e8e0d4" }}>Omni-Rank</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-sans" style={{ color: "rgba(200, 180, 150, 0.5)" }}>
            <a href="#features" className="hover:text-amber-200 transition-colors">Features</a>
            <a href="#pricing" className="hover:text-amber-200 transition-colors">Pricing</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="btn-ghost text-sm">Log in</Link>
            <Link href="/auth/signup" className="btn-primary text-sm flex items-center gap-1.5">
              Get started <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero — editorial, asymmetric */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 20%, rgba(200, 121, 65, 0.06), transparent 60%)" }} />
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 80% 80%, rgba(107, 143, 113, 0.04), transparent 50%)" }} />
        <div className="max-w-5xl mx-auto px-6 pt-28 pb-24 relative">
          <div className="max-w-3xl">
            <p className="font-sans text-xs uppercase tracking-[0.2em] mb-6" style={{ color: "var(--copper)" }}>AI-Powered SEO Intelligence Platform</p>
            <h1 className="font-serif text-6xl md:text-7xl leading-[1.05] mb-8" style={{ color: "#e8e0d4" }}>
              The SEO analyst<br />
              <span className="italic" style={{ color: "var(--copper-light)" }}>that never sleeps</span>
            </h1>
            <p className="text-lg font-sans leading-relaxed mb-12 max-w-xl" style={{ color: "rgba(200, 180, 150, 0.55)" }}>
              Omni-Rank combines DataForSEO&apos;s data depth with AI reasoning to analyze competitors, 
              generate content, track rankings, and execute technical fixes — autonomously.
            </p>
            <div className="flex items-center gap-4">
              <Link href="/auth/signup" className="btn-primary text-base px-8 py-3.5 flex items-center gap-2">
                Start 14-day free trial <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="#features" className="btn-secondary text-base px-6 py-3.5">How it works</Link>
            </div>
            <p className="text-xs font-sans mt-5" style={{ color: "rgba(200, 180, 150, 0.25)" }}>No credit card required &middot; Cancel anytime</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-28">
        <p className="font-sans text-xs uppercase tracking-[0.2em] mb-4" style={{ color: "var(--copper)" }}>Capabilities</p>
        <h2 className="font-serif text-4xl mb-4" style={{ color: "#e8e0d4" }}>Six agents. One mission.</h2>
        <p className="font-sans mb-16 max-w-lg" style={{ color: "rgba(200, 180, 150, 0.45)" }}>
          Each agent specializes in one dimension of SEO, working together like a senior strategy team.
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px" style={{ background: "rgba(200, 180, 150, 0.06)" }}>
          {features.map((f) => (
            <div key={f.title} className="p-8 group transition-all duration-300" style={{ background: "#110f0d" }}>
              <f.icon className="w-5 h-5 mb-5" style={{ color: "var(--copper)" }} />
              <h3 className="font-serif text-xl mb-3" style={{ color: "#e8e0d4" }}>{f.title}</h3>
              <p className="text-sm font-sans leading-relaxed" style={{ color: "rgba(200, 180, 150, 0.45)" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-5xl mx-auto px-6 py-28">
        <p className="font-sans text-xs uppercase tracking-[0.2em] mb-4 text-center" style={{ color: "var(--copper)" }}>Pricing</p>
        <h2 className="font-serif text-4xl text-center mb-4" style={{ color: "#e8e0d4" }}>Transparent. Simple.</h2>
        <p className="font-sans text-center mb-16" style={{ color: "rgba(200, 180, 150, 0.45)" }}>Start free, scale as you grow. Built for Indian businesses.</p>
        <div className="grid md:grid-cols-3 gap-5">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className="card p-7 relative"
              style={plan.popular ? { borderColor: "rgba(200, 121, 65, 0.3)" } : {}}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs px-3 py-0.5 rounded-full font-sans font-medium" style={{ background: "rgba(200, 121, 65, 0.15)", color: "var(--copper-light)", border: "1px solid rgba(200, 121, 65, 0.2)" }}>
                  Most popular
                </div>
              )}
              <h3 className="font-serif text-2xl mb-1" style={{ color: "#e8e0d4" }}>{plan.name}</h3>
              <div className="flex items-baseline gap-1 mb-7">
                <span className="font-serif text-3xl" style={{ color: plan.popular ? "var(--copper-light)" : "#e8e0d4" }}>{plan.price}</span>
                <span className="text-sm font-sans" style={{ color: "rgba(200, 180, 150, 0.35)" }}>/mo</span>
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm font-sans" style={{ color: "rgba(200, 180, 150, 0.6)" }}>
                    <span style={{ color: "var(--sage)" }}>&#10003;</span> {f}
                  </li>
                ))}
              </ul>
              <Link href="/auth/signup" className={plan.popular ? "btn-primary w-full text-center block" : "btn-secondary w-full text-center block"}>
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid rgba(200, 180, 150, 0.06)" }} className="py-12">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded flex items-center justify-center font-serif font-bold text-xs" style={{ background: "var(--copper-dark)", color: "#faf8f5" }}>OR</div>
            <span className="text-sm font-sans" style={{ color: "rgba(200, 180, 150, 0.3)" }}>Omni-Rank &copy; 2026</span>
          </div>
          <div className="flex items-center gap-6 text-xs font-sans" style={{ color: "rgba(200, 180, 150, 0.2)" }}>
            <a href="#" className="hover:text-amber-200 transition-colors">Privacy</a>
            <a href="#" className="hover:text-amber-200 transition-colors">Terms</a>
            <a href="#" className="hover:text-amber-200 transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
