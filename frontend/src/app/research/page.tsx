"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, TrendingUp, BarChart3, Lock, Download, Sparkles, Mail } from "lucide-react";

export default function ResearchPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // In production, send to backend/email service
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setEmail("");
    }, 3000);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            OR OMNI-RANK
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/tools" className="text-sm text-slate-600 hover:text-slate-900">Free Tools</Link>
            <Link href="/auth/signup" className="text-sm font-semibold text-violet-700">
              Platform Login
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-violet-50 via-slate-50 to-indigo-50 py-20">
        <div className="max-w-4xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-100 text-violet-700 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            Monthly AI Search Trends
          </div>
          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            How AI is reshaping search.<br />
            Industry by industry.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            Every month, OMNI-RANK analyzes 10M+ AI search queries across ChatGPT, Perplexity, Gemini, and Google AI Overviews. We track how brands get cited, what content wins, and which industries are being transformed.
          </p>

          {/* Stats */}
          <div className="grid md:grid-cols-4 gap-4 mb-12">
            {[
              { label: "Queries Analyzed", value: "10M+" },
              { label: "AI Engines", value: "4" },
              { label: "Industries Covered", value: "20" },
              { label: "Updated", value: "Monthly" },
            ].map((stat, i) => (
              <div key={i} className="p-3 rounded-lg bg-white border border-slate-200">
                <div className="text-xs text-slate-600 font-medium">{stat.label}</div>
                <div className="text-xl font-bold text-slate-900 mt-1">{stat.value}</div>
              </div>
            ))}
          </div>

          <Link
            href="#subscribe"
            className="inline-flex items-center gap-2 bg-violet-600 text-white font-semibold px-8 py-3.5 rounded-lg hover:bg-violet-700 transition"
          >
            Get January Report Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* What's Inside */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-slate-900 mb-12">Inside Every Monthly Report</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            {
              title: "AI Citation Trends",
              desc: "Which brands got cited most in AI responses this month? How did citation patterns shift vs. last month?",
              metrics: ["Top 100 brands cited", "Citation rate by industry", "Month-over-month change"],
            },
            {
              title: "Industry Deep Dives",
              desc: "SaaS, Ecommerce, Healthcare, Fintech, B2B. See how AI search is unique to your industry.",
              metrics: ["20 vertical analyses", "Competitive rankings", "Emerging keyword clusters"],
            },
            {
              title: "Content That Wins",
              desc: "Which content types get cited by AI? Case studies, comparison pages, how-to guides?",
              metrics: ["Content format breakdown", "Word count analysis", "Structural elements"],
            },
            {
              title: "Keyword Shifts",
              desc: "Which keywords now have AI Overviews? Which ones lost it? Track volatility.",
              metrics: ["New AI Overview keywords", "Lost opportunities", "Ranking movement"],
            },
            {
              title: "E-E-A-T Signals",
              desc: "What makes a brand credible enough to cite? Author bios, credentials, structure?",
              metrics: ["E-E-A-T scoring framework", "Competitor benchmarks", "Gap analysis"],
            },
            {
              title: "Predictions",
              desc: "Our AI analysts predict next month's trends. Where are buyers searching next?",
              metrics: ["Emerging verticals", "Query volume forecasts", "Competitive alerts"],
            },
          ].map((section, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 bg-white">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">{section.title}</h3>
              <p className="text-sm text-slate-600 mb-4">{section.desc}</p>
              <ul className="space-y-1">
                {section.metrics.map((m, j) => (
                  <li key={j} className="flex items-center gap-2 text-xs text-slate-600">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-400"></span>
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Sample Insights */}
      <section className="bg-slate-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12">Sample Insights from Last Month</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                title: "SaaS AI Citation Surge",
                stat: "+34%",
                desc: "SaaS brands got cited 34% more often in ChatGPT responses this month vs. last month.",
              },
              {
                title: "Comparison Page Wins",
                stat: "68%",
                desc: "68% of AI citations came from comparison pages (vs. product pages at 18%).",
              },
              {
                title: "E-E-A-T Gap",
                stat: "89%",
                desc: "89% of non-cited domains were missing author credentials in their author schema.",
              },
              {
                title: "Perplexity Dominance",
                stat: "44%",
                desc: "Perplexity now accounts for 44% of all AI search citations (vs. ChatGPT at 31%).",
              },
              {
                title: "Fintech Authority",
                stat: "12x",
                desc: "Fintech brands rank 12x higher in AI citations if they have security certifications marked up.",
              },
              {
                title: "Healthcare Reachability",
                stat: "-18%",
                desc: "Healthcare pages lost 18% AI citation rate. Likely due to stricter E-E-A-T enforcement.",
              },
            ].map((insight, i) => (
              <div key={i} className="p-6 rounded-lg border border-slate-700 bg-slate-800/50">
                <div className="text-violet-400 font-bold text-2xl mb-2">{insight.stat}</div>
                <h3 className="font-semibold text-white mb-2">{insight.title}</h3>
                <p className="text-sm text-slate-300">{insight.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Who This Is For */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold text-slate-900 mb-12">Who Reads This Report</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              title: "Marketing Leaders",
              desc: "Understand how AI is reshaping search. Inform content strategy, budget allocation, hiring.",
            },
            {
              title: "SEO Strategists",
              desc: "Get monthly guardrails on what's working. Know when algorithms shift. Stay ahead of competitors.",
            },
            {
              title: "Content Teams",
              desc: "Learn what content wins in AI responses. Adjust tone, structure, entity coverage accordingly.",
            },
          ].map((persona, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 bg-white text-center">
              <h3 className="font-semibold text-slate-900 mb-2">{persona.title}</h3>
              <p className="text-sm text-slate-600">{persona.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Subscribe Section */}
      <section id="subscribe" className="bg-gradient-to-r from-violet-600 to-indigo-600 py-20">
        <div className="max-w-2xl mx-auto px-6">
          <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12">
            <div className="flex items-center gap-2 mb-6">
              <Lock className="w-5 h-5 text-violet-600" />
              <span className="text-sm font-semibold text-violet-600">GATED CONTENT</span>
            </div>

            <h2 className="text-3xl font-bold text-slate-900 mb-3">Get January's Report Free</h2>
            <p className="text-slate-600 mb-8">
              Join 2,000+ marketers getting monthly AI search trends. Unsubscribe anytime.
            </p>

            {submitted ? (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                <div className="flex items-center gap-2 text-emerald-700 font-medium">
                  <Check className="w-5 h-5" />
                  Check your email for the download link!
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-3">
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 text-sm placeholder-slate-500 focus:outline-none focus:border-violet-500"
                />
                <button
                  type="submit"
                  className="w-full bg-violet-600 text-white font-semibold py-3 rounded-lg hover:bg-violet-700 transition flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download January Report
                </button>
                <p className="text-xs text-slate-600 text-center">
                  We respect your privacy. Unsubscribe at any time.
                </p>
              </form>
            )}

            <div className="mt-8 pt-8 border-t border-slate-200">
              <p className="text-xs text-slate-600 mb-4 font-medium uppercase">Also Includes:</p>
              <ul className="space-y-2">
                {[
                  "Full PDF report (30+ pages)",
                  "Monthly metrics spreadsheet",
                  "Per-industry competitive rankings",
                  "Next month's predictions",
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                    <TrendingUp className="w-4 h-4 text-violet-600" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="max-w-5xl mx-auto px-6 py-16 text-center">
        <h2 className="text-2xl font-bold text-slate-900 mb-4">Want real-time AI Visibility tracking?</h2>
        <p className="text-slate-600 mb-6 max-w-2xl mx-auto">
          The monthly report shows trends. The OMNI-RANK platform tracks your brand's AI visibility daily.
        </p>
        <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-violet-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-violet-700 transition">
          Try Platform Free <ArrowRight className="w-4 h-4" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-8 bg-white">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-slate-600">
          © 2026 OMNI-RANK. Monthly research report.
        </div>
      </footer>
    </div>
  );
}

// Import Check icon
import { Check } from "lucide-react";
