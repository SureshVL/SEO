"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Zap, TrendingUp, Target, Code2, BarChart3, Check, Sparkles } from "lucide-react";

export default function SaaSSolutionPage() {
  const [interval, setInterval] = useState<"month" | "year">("month");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <span className="grid place-items-center w-8 h-8 rounded-lg bg-violet-600 text-white text-sm">OR</span>
            OMNI-RANK
          </Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1 hover:text-violet-800">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-violet-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-violet-700 font-semibold text-sm uppercase mb-4">SaaS SEO Intelligence</div>
          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            Rank your product features.<br />
            Own your category.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            SaaS buyers search for solutions in specific ways: feature comparisons, problem-focused keywords, and intent-based queries. OMNI-RANK tracks all three — and tells you where competitors rank for YOUR keyword clusters.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link href="/auth/signup" className="btn-primary text-base px-8 py-3.5 flex items-center gap-2">
              Free audit for your domain <ArrowRight className="w-4 h-4" />
            </Link>
            <Link href="/tools" className="btn-secondary text-base px-6 py-3.5">
              Try free tools
            </Link>
          </div>
        </div>
      </section>

      {/* Problem + Solution */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">The SaaS SEO Challenge</h2>
            <div className="space-y-4">
              {[
                { title: "Feature Keywords Scattered", desc: "Your product has 50+ features. Competitors rank for specific feature comparisons you don't track." },
                { title: "Comparison Page Wars", desc: "vs-Competitor pages are where SaaS deals are won. But you can't see how you rank for these intent-rich keywords." },
                { title: "Product Launch Rankings", desc: "New features get no organic visibility. You need an SEO roadmap that ties product launches to keyword strategy." },
                { title: "Pricing Page Blind Spot", desc: "Your pricing page is a top landing page, but you can't track its keyword rankings or AI visibility." },
              ].map((item, i) => (
                <div key={i} className="flex gap-4">
                  <div className="w-6 h-6 rounded-lg bg-red-100 flex items-center justify-center shrink-0">
                    <span className="text-red-600 font-bold text-sm">✕</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                    <p className="text-sm text-slate-600">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">How OMNI-RANK Solves It</h2>
            <div className="space-y-4">
              {[
                { title: "AI Agents Track Feature Clusters", desc: "Automatically group your keywords by feature + intent. Know ranking velocity for each cluster." },
                { title: "Competitor Feature Mapping", desc: "See which competitor features drive searches. Find gaps in YOUR feature marketing." },
                { title: "Content + Product Roadmap Sync", desc: "Create SEO content 2 weeks BEFORE launching features. Own the search volume on day 1." },
                { title: "Pricing Page Optimization", desc: "Track pricing page keywords, comparison tables, review snippets. Daily ranking updates." },
              ].map((item, i) => (
                <div key={i} className="flex gap-4">
                  <div className="w-6 h-6 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
                    <Check className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                    <p className="text-sm text-slate-600">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Key Metrics */}
      <section className="bg-slate-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12 text-center">What Winning SaaS SEO Looks Like</h2>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { metric: "3,200%", desc: "Avg keyword ranking velocity increase (week 1 of campaign)" },
              { metric: "18 days", desc: "Time to own 100+ feature-related keywords vs. competitors" },
              { metric: "42%", desc: "Monthly organic traffic increase year-over-year" },
              { metric: "67%", desc: "Competitor feature mapping coverage (keywords tracked)" },
            ].map((item, i) => (
              <div key={i} className="text-center">
                <div className="text-3xl font-bold text-violet-400 mb-2">{item.metric}</div>
                <div className="text-sm text-slate-400">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SaaS-Specific Features */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">SaaS Features Built In</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            {
              icon: <Code2 className="w-6 h-6" />,
              title: "Feature Keyword Clustering",
              desc: "Auto-group keywords by product feature (Pricing, Security, Integrations, etc.). See which features drive search demand.",
            },
            {
              icon: <Target className="w-6 h-6" />,
              title: "Competitor Feature Mapping",
              desc: "Scrape competitor content. Find features they rank for that you don't. Identify SEO gaps in your product messaging.",
            },
            {
              icon: <TrendingUp className="w-6 h-6" />,
              title: "Launch Keyword Roadmap",
              desc: "Schedule SEO content weeks before launching features. Rank on day 1 when searchers look for your new capabilities.",
            },
            {
              icon: <BarChart3 className="w-6 h-6" />,
              title: "Pricing Page Analytics",
              desc: "Track rankings for pricing-adjacent keywords (cost, pricing, ROI, vs. X pricing). Know intent at every funnel stage.",
            },
            {
              icon: <Sparkles className="w-6 h-6" />,
              title: "AI Visibility for Comparisons",
              desc: "Know if ChatGPT, Perplexity, and Gemini cite your comparison pages. AI search is where 30% of SaaS demos start.",
            },
            {
              icon: <Zap className="w-6 h-6" />,
              title: "Real-Time Rank Alerts",
              desc: "Get daily alerts when competitors rank for keywords you own. Respond in hours, not weeks.",
            },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 hover:border-violet-300 transition">
              <div className="text-violet-600 mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Case Study */}
      <section className="bg-slate-100 py-20">
        <div className="max-w-3xl mx-auto px-6">
          <div className="bg-white rounded-lg border border-slate-200 p-8">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
              <span className="text-sm font-semibold text-slate-600">Case Study: Fintech SaaS</span>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-4">From 12 to 2,847 Tracked Keywords</h3>
            <p className="text-slate-600 mb-4">
              A payment SaaS company had 12 primary keywords in Google Search Console. Using OMNI-RANK's feature clustering, they mapped 127 feature-related keywords they were ranking for but didn't know existed.
            </p>
            <p className="text-slate-600 mb-4">
              Within 3 months of optimizing content for competitor-mapped feature comparisons:
            </p>
            <ul className="space-y-2 mb-6">
              <li className="flex items-center gap-2 text-slate-700">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>+2,847 keywords on page 1-3 of Google</span>
              </li>
              <li className="flex items-center gap-2 text-slate-700">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>+340% organic traffic (monthly, sustained)</span>
              </li>
              <li className="flex items-center gap-2 text-slate-700">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>+18% feature adoption (correlated with organic)
                </span>
              </li>
            </ul>
            <div className="text-sm font-mono text-slate-500">
              "OMNI-RANK gave us visibility into feature keywords we didn't even know we owned."
            </div>
            <div className="text-sm text-slate-600 mt-2">— VP Marketing, Payment SaaS</div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-900 mb-3">Choose Your Plan</h2>
          <p className="text-slate-600">Start free. Scale as you launch features.</p>
          <div className="flex justify-center gap-2 mt-6">
            <button
              onClick={() => setInterval("month")}
              className={`px-4 py-2 rounded-lg font-medium text-sm ${
                interval === "month"
                  ? "bg-violet-600 text-white"
                  : "bg-slate-200 text-slate-700"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setInterval("year")}
              className={`px-4 py-2 rounded-lg font-medium text-sm ${
                interval === "year"
                  ? "bg-violet-600 text-white"
                  : "bg-slate-200 text-slate-700"
              }`}
            >
              Annual (-20%)
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              name: "Growth",
              price: "₹4,999",
              features: [
                "5 projects (multiple SaaS products)",
                "300 keywords tracked",
                "Feature clustering + competitor mapping",
                "Daily rank tracking with alerts",
                "AI Visibility for comparison pages",
                "Content studio (AI rewrites)",
              ],
            },
            {
              name: "Pro",
              price: "₹9,999",
              features: [
                "12 projects",
                "800 keywords",
                "Advanced feature analytics",
                "Automated launch roadmap planning",
                "API access (embed in product)",
                "White-label reports",
              ],
              popular: true,
            },
            {
              name: "Agency",
              price: "₹19,999",
              features: [
                "25 projects (multi-SaaS)",
                "2,000 keywords",
                "All Pro features",
                "API + custom integrations",
                "10 team seats",
                "Dedicated support",
              ],
            },
          ].map((plan, i) => (
            <div
              key={i}
              className={`p-6 rounded-lg border transition ${
                plan.popular
                  ? "border-violet-500 bg-violet-50 ring-1 ring-violet-100"
                  : "border-slate-200 bg-white"
              }`}
            >
              <h3 className="font-semibold text-lg text-slate-900 mb-2">{plan.name}</h3>
              <div className="text-2xl font-bold text-slate-900 mb-4">
                {plan.price}
                <span className="text-sm text-slate-600 font-normal">/mo</span>
              </div>
              <ul className="space-y-2 mb-6">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-start gap-2 text-sm text-slate-700">
                    <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="/auth/signup"
                className={`w-full block text-center py-2 rounded-lg font-medium transition ${
                  plan.popular
                    ? "bg-violet-600 text-white hover:bg-violet-700"
                    : "bg-slate-100 text-slate-900 hover:bg-slate-200"
                }`}
              >
                Start free
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to win SaaS keywords?</h2>
          <p className="text-white/90 mb-6">
            Start with a free audit of your domain. No credit card required.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center gap-2 bg-white text-violet-700 font-semibold px-8 py-3 rounded-lg hover:bg-slate-50 transition"
          >
            Get started free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-slate-600">
          © 2026 OMNI-RANK. For SaaS teams that rank.
        </div>
      </footer>
    </div>
  );
}
