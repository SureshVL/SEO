"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "quote-keyword-strategy", title: "Quote Keywords: Own \"[Insurance Type] Quote\" Search", excerpt: "\"Car insurance quote\" and \"Best car insurance quotes\" drive high-intent shoppers. We tracked quote keyword volume and found your biggest opportunity gaps.", date: "2026-01-03", author: "Sarah Chen", category: "Conversion Strategy", readTime: "8 min read" },
  { slug: "coverage-education-content", title: "Coverage Education Content: Rank \"What Does [Coverage] Include?\"", excerpt: "Shoppers search high-intent education questions before buying. \"What does comprehensive coverage include?\" drives qualified leads that competitors ignore.", date: "2025-12-28", author: "Marcus Wong", category: "Content Strategy", readTime: "9 min read" },
  { slug: "rate-alert-seo", title: "Rate Alerts & Price Comparison: Own the Quote Aggregator Space", excerpt: "Rate comparison keywords are contested but valuable. Here's how insurance brands outrank Kayak and TheZebra for buyer intent.", date: "2025-12-22", author: "Alex Rivera", category: "Competitive Intelligence", readTime: "10 min read" },
  { slug: "claims-process-transparency", title: "Claims Process Transparency: Rank \"How to File a Claim\"", excerpt: "Claims process questions are low-volume but high-conversion. Customers find them when they need you most. Make sure you rank.", date: "2025-12-17", author: "Sarah Chen", category: "Trust Signals", readTime: "7 min read" },
];

export default function InsuranceBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/insurance" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Insurance Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-blue-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Insurance SEO Strategy</h1>
          <p className="text-lg text-slate-600">Own quote keywords. Educate on coverage. Rank claims process content.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/insurance/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-blue-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-blue-50 text-blue-700 font-medium">
                  {post.category}
                </span>
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  {new Date(post.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                </div>
                <div className="flex items-center gap-1">
                  <User className="w-4 h-4" />
                  {post.author}
                </div>
                <span>{post.readTime}</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Insurance Quote Rankings</h2>
          <p className="text-blue-100 mb-6">Know which coverage types drive traffic. Monitor quote keyword performance.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
