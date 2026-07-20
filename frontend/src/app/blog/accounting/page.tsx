"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "tax-season-keyword-strategy", title: "Tax Season SEO: Own Q1-Q2 Before Your Competitors Know What Hit Them", excerpt: "Tax season keywords peak predictably. Winners plan 6 months ahead. Here's the exact calendar for keyword targeting, content, and link building.", date: "2026-01-07", author: "Sarah Chen", category: "Seasonal Strategy", readTime: "8 min read" },
  { slug: "cost-questions-seo", title: "\"How Much Does [Service] Cost?\" Keywords: Convert By Answering Early", excerpt: "\"How much does tax planning cost?\" and \"What's the cost of an audit?\" drive qualified prospects. Most accounting firms ignore these educational keywords.", date: "2026-01-02", author: "Marcus Wong", category: "Content Strategy", readTime: "9 min read" },
  { slug: "local-cpa-search", title: "Local CPA Search: Own \"Accountant Near Me\" in Your City", excerpt: "\"Accountant\" and \"Accountant near me\" rank completely differently. Here's how to dominate both and own your local market.", date: "2025-12-27", author: "Alex Rivera", category: "Local SEO", readTime: "7 min read" },
  { slug: "service-keyword-segmentation", title: "Service Segmentation: Tax, Audit, Bookkeeping, Planning Keywords Tracked Separately", excerpt: "Your firm handles tax and audit. Rank equally for both and you'll cannibalize your traffic. Here's how to segment keywords by service line.", date: "2025-12-19", author: "Sarah Chen", category: "Strategy", readTime: "8 min read" },
];

export default function AccountingBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/accounting" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Accounting Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-green-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Accounting & Tax SEO</h1>
          <p className="text-lg text-slate-600">Own seasonal tax keywords. Convert high-intent \"how much\" questions. Dominate local CPA search.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/accounting/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-green-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-50 text-green-700 font-medium">
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

      <section className="bg-gradient-to-r from-green-600 to-emerald-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Tax & Accounting Keywords</h2>
          <p className="text-green-100 mb-6">Plan ahead for tax season. Know which service keywords drive most clients.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-green-700 font-semibold px-8 py-3 rounded-lg hover:bg-green-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
