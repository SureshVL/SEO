"use client";

import Link from "next/link";
import { ArrowRight, ArrowLeft, TrendingUp, Target, Users, DollarSign } from "lucide-react";

export default function EcommerceCaseStudy() {
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
          <p className="text-sm text-emerald-600 font-semibold uppercase tracking-wider mb-4">
            Ecommerce Case Study
          </p>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Product Page SEO: 28% Revenue Increase in 4 Months
          </h1>
          <p className="text-lg text-slate-600 mb-8">
            How ShopFlow used schema markup and SERP feature optimization to boost organic revenue contribution.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
              <div className="text-xs text-emerald-600 uppercase tracking-wider font-semibold mb-1">Revenue from Organic</div>
              <div className="text-3xl font-bold text-slate-900">12% → 28%</div>
              <div className="text-xs text-slate-600 mt-1">+16 percentage points</div>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-600 uppercase tracking-wider font-semibold mb-1">Timeline</div>
              <div className="text-3xl font-bold text-slate-900">4</div>
              <div className="text-xs text-slate-600 mt-1">months</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="text-xs text-purple-600 uppercase tracking-wider font-semibold mb-1">Product Page CTR</div>
              <div className="text-3xl font-bold text-slate-900">+34%</div>
              <div className="text-xs text-slate-600 mt-1">from SERP features</div>
            </div>
            <div className="p-4 bg-pink-50 rounded-lg border border-pink-200">
              <div className="text-xs text-pink-600 uppercase tracking-wider font-semibold mb-1">AOV Impact</div>
              <div className="text-3xl font-bold text-slate-900">+$12</div>
              <div className="text-xs text-slate-600 mt-1">avg order value</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 mb-8">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Users className="w-4 h-4 text-emerald-600" />
              <span>Founded 2015 • Austin, TX</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Target className="w-4 h-4 text-emerald-600" />
              <span>Direct-to-Consumer • Fashion</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span>$45M ARR</span>
            </div>
          </div>
        </div>

        <div className="prose prose-slate max-w-none">
          <h2>The Challenge</h2>
          <p>
            ShopFlow's SEO performance was stagnant. They ranked for product keywords but competitors' listings displayed stars, reviews, and prices directly on Google SERPs. ShopFlow's didn't. The result: 18% lower CTR than competitors, even when ranking at the same position.
          </p>

          <p>
            Their product pages also lacked proper schema markup for structured data. Review aggregators were appearing in search results more prominently than their own product pages.
          </p>

          <h2>The OMNI-RANK Strategy</h2>
          <p>
            We identified three quick wins:
          </p>

          <h3>1. Product Schema Markup Implementation</h3>
          <ul>
            <li>Added Product, Review, Offer, and AggregateRating schema to all 2,400 product pages</li>
            <li>Ensured inventory status, pricing, and shipping info were schema-marked</li>
            <li>Implemented organization-level review schema aggregation</li>
          </ul>

          <h3>2. Review SEO Optimization</h3>
          <ul>
            <li>Extracted reviews from internal system into proper ReviewSchema</li>
            <li>Increased average review count per product from 3 to 18</li>
            <li>Implemented review request automation post-purchase</li>
          </ul>

          <h3>3. Variant Handling Fix</h3>
          <ul>
            <li>Prevented canonical tag cannibalization across color/size variants</li>
            <li>Each variant (red shirt, blue shirt) got its own ranking opportunity</li>
            <li>Added variant-specific keywords instead of generic product titles</li>
          </ul>

          <h2>Results: From 12% to 28%</h2>
          <p>
            Within 4 months:
          </p>
          <ul>
            <li>SERP CTR increased 34% (stars, prices, reviews now visible)</li>
            <li>Product page impressions: +89%</li>
            <li>Organic revenue increased from 12% to 28% of total revenue</li>
            <li>Average order value increased $12 (higher AOV from organic)</li>
            <li>Return rate decreased 7% (better qualified traffic from rich results)</li>
          </ul>

          <h2>Why This Matters</h2>
          <p>
            Schema markup isn't "nice to have" for ecommerce. It's the difference between ranking and converting. Google prioritizes rich results, and shoppers click based on visible signals (stars, prices, reviews). ShopFlow's 16-point increase in revenue attribution came purely from visibility improvements on SERPs, not rank improvements.
          </p>
        </div>

        <div className="mt-16 p-8 bg-emerald-50 border border-emerald-200 rounded-lg text-center">
          <h3 className="text-xl font-bold text-slate-900 mb-3">Optimize your product pages for SERP features</h3>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-emerald-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-emerald-700 transition">
            Start Free Audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </article>
    </div>
  );
}
