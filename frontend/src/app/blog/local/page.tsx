"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "google-business-optimization", title: "Google Business Profile Mastery: Every Field Matters", excerpt: "Your profile is incomplete or outdated. Competitors' are perfect. We reviewed 1,000 profiles and found 8 fields that drive 60% of your visibility.", date: "2026-01-08", author: "Marcus Wong", category: "Local SEO", readTime: "7 min read" },
  { slug: "near-me-search-ranking", title: "\"Near Me\" Rankings: The Keywords Nobody Tracks", excerpt: "\"Plumber near me\" and \"Best plumber near me\" have different intents and different ranking requirements. Here's how to own both.", date: "2026-01-03", author: "Sarah Chen", category: "Strategy", readTime: "8 min read" },
  { slug: "review-seo-local", title: "Review SEO: Why Your Reviews Don't Show + How to Fix It", excerpt: "Google filters reviews based on recency, relevance, and reviewer authority. Most local businesses don't know this. Here's the exact strategy that makes reviews rank.", date: "2025-12-28", author: "Alex Rivera", category: "Trust Signals", readTime: "9 min read" },
  { slug: "multi-location-strategy", title: "Multi-Location Strategy: Own Your Market vs. Your Chain", excerpt: "Running 5+ locations? You need a different strategy than single-location businesses. We show you how top chains dominate both local and regional searches.", date: "2025-12-20", author: "Marcus Wong", category: "Expansion", readTime: "10 min read" },
];

export default function LocalBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/local" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Local Services Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-cyan-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Local Services SEO</h1>
          <p className="text-lg text-slate-600">Master Google Business, near-me search, and review optimization for local dominance.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/local/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-cyan-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-cyan-50 text-cyan-700 font-medium">
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

      <section className="bg-gradient-to-r from-cyan-600 to-blue-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Local Keyword Rankings</h2>
          <p className="text-cyan-100 mb-6">Know your map pack position. Monitor \"near me\" searches daily.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-cyan-700 font-semibold px-8 py-3 rounded-lg hover:bg-cyan-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
