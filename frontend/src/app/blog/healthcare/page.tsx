"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  {
    slug: "eeat-audit-guide",
    title: "E-E-A-T Audit: Why Your Medical Content Doesn't Rank (And How to Fix It)",
    excerpt: "Google's E-E-A-T filter removes 60% of healthcare content from SERPs. We show you the exact audit framework used by 50+ medical practices to reclaim rankings.",
    date: "2026-01-12",
    author: "Dr. James Mitchell",
    category: "Core Algorithm",
    readTime: "11 min read",
  },
  {
    slug: "medical-entity-mapping",
    title: "Medical Entity Schema: How Competitors Show Authority You Can't",
    excerpt: "Competitors' doctor profiles, affiliations, and credentials rank. Yours don't. It's because they structured their schema differently. Here's the winning schema markup.",
    date: "2026-01-08",
    author: "Sarah Chen",
    category: "Technical SEO",
    readTime: "9 min read",
  },
  {
    slug: "compliance-seo",
    title: "Privacy + Compliance SEO: Make Your HIPAA Pages Rank",
    excerpt: "Privacy policies and compliance pages are necessary but invisible to Google. Learn how winning healthcare sites optimize these pages for search without sacrificing legal rigor.",
    date: "2026-01-02",
    author: "Alex Rivera",
    category: "Compliance",
    readTime: "8 min read",
  },
  {
    slug: "reputation-integration",
    title: "Reputation Integration: Turn Patient Reviews Into Ranking Power",
    excerpt: "Patient reviews are your biggest trust signal. Most clinics lose them to disconnected platforms. See how top practices integrate reviews into their ranking strategy.",
    date: "2025-12-27",
    author: "Dr. James Mitchell",
    category: "Trust Signals",
    readTime: "7 min read",
  },
];

export default function HealthcareBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/healthcare" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Healthcare Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-red-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Healthcare SEO Strategy</h1>
          <p className="text-lg text-slate-600">Navigate E-E-A-T, medical entity markup, and compliance while ranking for patient queries.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/healthcare/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-red-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-red-50 text-red-700 font-medium">
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

      <section className="bg-gradient-to-r from-red-600 to-pink-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Patient Search Intent</h2>
          <p className="text-red-100 mb-6">Know which conditions drive traffic. Monitor E-E-A-T compliance daily.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-red-700 font-semibold px-8 py-3 rounded-lg hover:bg-red-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
