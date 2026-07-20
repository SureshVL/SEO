"use client";

import Link from "next/link";
import { ArrowRight, ShoppingCart, TrendingUp, Package, Zap, Tag } from "lucide-react";

export default function EcommerceSolutionPage() {
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

      <section className="bg-gradient-to-br from-emerald-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            Rank product pages.<br />
            Dominate SERP features.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            Ecommerce rankings are won on product pages, reviews, and shopping features. Track SERP feature distribution, review snippets, and product card rankings across competitors.
          </p>
          <Link href="/auth/signup" className="btn-primary inline-flex items-center gap-2">
            Free audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">Ecommerce SEO Blindspots</h2>
            {[
              { title: "Product Page Rankings", desc: "Track which product pages rank for long-tail product keywords vs. competitors." },
              { title: "SERP Feature Wars", desc: "Shopping results, reviews, Q&A snippets, images. Miss one feature type and lose 40% of traffic." },
              { title: "Review Schema Ranking", desc: "Does your review schema show in Google? Competitors' reviews might be outranking your products." },
              { title: "SKU-Level Insights", desc: "Which variants/colors/sizes get search volume? Track at the product level, not category." },
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
              { title: "Product Page Tracking", desc: "Monitor individual product page rankings across 500+ keywords daily." },
              { title: "SERP Feature Analytics", desc: "See which competitors own reviews, shopping, Q&A, images. Know what you're missing." },
              { title: "Review & Rating Insights", desc: "Track review snippet rankings, rating distribution, how reviews impact CTR." },
              { title: "Variant-Level SEO", desc: "Understand which colors/sizes/variants get search volume. Optimize inventory." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-emerald-600 font-bold">✓</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-emerald-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12 text-center">Ecommerce Results</h2>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-emerald-400 mb-2">287%</div>
              <div className="text-sm text-slate-300">Avg. organic revenue increase (6-month)</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-emerald-400 mb-2">12x</div>
              <div className="text-sm text-slate-300">Product page traffic velocity increase</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-emerald-400 mb-2">64%</div>
              <div className="text-sm text-slate-300">Competitor SERP feature capture</div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">Ecommerce Features</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            { icon: <ShoppingCart />, title: "Product Page Rankings", desc: "Track individual SKU rankings for every product-related keyword." },
            { icon: <TrendingUp />, title: "SERP Feature Tracking", desc: "Monitor shopping, reviews, Q&A, images — see every feature type." },
            { icon: <Package />, title: "Competitor Price Tracking", desc: "Know when competitors drop prices and rerank. React in hours." },
            { icon: <Tag />, title: "Seasonal Keyword Mapping", desc: "Black Friday, holiday, seasonal keywords — plan inventory & content accordingly." },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 hover:border-emerald-300 transition">
              <div className="text-emerald-600 mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to dominate product search?</h2>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-emerald-700 font-semibold px-8 py-3 rounded-lg">
            Get started free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
