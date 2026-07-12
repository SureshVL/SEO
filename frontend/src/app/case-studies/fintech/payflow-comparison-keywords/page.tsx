"use client";

import Link from "next/link";
import { ArrowRight, ArrowLeft } from "lucide-react";

export default function FintechCase() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/case-studies" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            All Case Studies <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <article className="max-w-4xl mx-auto px-6 py-16">
        <Link href="/case-studies" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-8">
          <ArrowLeft className="w-4 h-4" /> All Case Studies
        </Link>

        <div className="mb-12">
          <p className="text-sm text-amber-600 font-semibold uppercase tracking-wider mb-4">
            Fintech Case Study
          </p>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Comparison Keyword Dominance: 4.2x Lead Growth
          </h1>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
              <div className="text-xs text-amber-600 uppercase tracking-wider font-semibold mb-1">Comparison Keywords</div>
              <div className="text-3xl font-bold text-slate-900">8 → 34</div>
              <div className="text-xs text-slate-600 mt-1">top 3 rankings</div>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-600 uppercase tracking-wider font-semibold mb-1">Lead Volume</div>
              <div className="text-3xl font-bold text-slate-900">4.2x</div>
              <div className="text-xs text-slate-600 mt-1">increase</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-xs text-green-600 uppercase tracking-wider font-semibold mb-1">Timeline</div>
              <div className="text-3xl font-bold text-slate-900">3</div>
              <div className="text-xs text-slate-600 mt-1">months</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="text-xs text-purple-600 uppercase tracking-wider font-semibold mb-1">Conversion</div>
              <div className="text-3xl font-bold text-slate-900">31%</div>
              <div className="text-xs text-slate-600 mt-1">vs 8% generic</div>
            </div>
          </div>
        </div>

        <div className="prose prose-slate max-w-none">
          <h2>The Challenge</h2>
          <p>
            PayFlow was getting crushed in "payment processor" search results. They ranked well but conversion was terrible — 8% of searches resulted in trial signups. Their competitors owned "PayPal vs. Stripe" and "Stripe vs. Square" comparisons, capturing high-intent shoppers at the buying moment.
          </p>

          <h2>The Strategy: Comparison Keyword Clustering</h2>
          <p>
            We identified 47 comparison keywords where PayFlow could compete:
          </p>
          <ul>
            <li>PayFlow vs. Stripe (direct comparison)</li>
            <li>PayFlow vs. Square (feature comparison)</li>
            <li>PayFlow vs. 2Checkout (pricing comparison)</li>
            <li>Best payment processor for SaaS (category + use case)</li>
            <li>Payment processor with lowest fees (problem-focused)</li>
          </ul>

          <p>
            We created dedicated comparison pages for the top 12 keywords, each structured with:
          </p>
          <ul>
            <li>Feature-by-feature comparison table</li>
            <li>Pricing breakdown</li>
            <li>Use-case specific recommendations ("best for SaaS", "best for agencies")</li>
            <li>FAQ schema addressing common questions</li>
            <li>Trust signals (customer reviews, security certifications)</li>
          </ul>

          <h2>Results</h2>
          <ul>
            <li>Comparison keywords ranking top 3: 8 → 34</li>
            <li>Lead volume: 8 → 34 per day (+325%)</li>
            <li>Conversion rate: 8% → 31% (nearly 4x)</li>
            <li>CAC: -42% (better qualified traffic)</li>
            <li>Customer LTV: +18% (buyers found via comparisons stick around)</li>
          </ul>

          <h2>Key Insight</h2>
          <p>
            Fintech buyers don't convert on brand keywords. They convert on comparison keywords where they're actively deciding between options. PayFlow's 4.2x lead growth came from owning the decision moment, not the awareness moment.
          </p>
        </div>

        <div className="mt-16 p-8 bg-amber-50 border border-amber-200 rounded-lg text-center">
          <h3 className="text-xl font-bold text-slate-900 mb-3">Own your comparison keywords</h3>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-amber-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-amber-700 transition">
            Start Fintech Audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </article>
    </div>
  );
}
