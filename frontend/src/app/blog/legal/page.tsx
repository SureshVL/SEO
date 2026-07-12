"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  {
    slug: "location-practice-area-tracking",
    title: "Location + Practice Area Tracking: \"Divorce Lawyer NYC\" vs. \"Divorce Lawyer\"",
    excerpt: "Generic \"divorce lawyer\" and \"divorce lawyer in NYC\" are completely different keywords with different intent. Most law firms rank for one and miss the other. We mapped 5,000+ legal keywords.",
    date: "2026-01-10",
    author: "Alex Rivera",
    category: "Keyword Strategy",
    readTime: "9 min read",
  },
  {
    slug: "review-schema-legal",
    title: "Review Schema Wins: Why Competitor Testimonials Show and Yours Don't",
    excerpt: "Client testimonials are your competitive advantage. But only if Google displays them. We reverse-engineered the schema markup that makes reviews rank on legal SERPs.",
    date: "2026-01-04",
    author: "Sarah Chen",
    category: "Trust Signals",
    readTime: "8 min read",
  },
  {
    slug: "educational-content-legal",
    title: "Educational Content SEO: \"How Much Does a Divorce Cost?\" Ranks. Yours Doesn't.",
    excerpt: "High-intent questions like \"how much does a patent cost?\" and \"what's the process for Chapter 7?\" drive qualified leads. Most law firms ignore them. Here's how to capture them.",
    date: "2025-12-30",
    author: "Marcus Wong",
    category: "Content Strategy",
    readTime: "10 min read",
  },
  {
    slug: "practice-area-segmentation",
    title: "Practice Area Segmentation: Which Areas Drive Most Clients?",
    excerpt: "Your firm handles litigation, IP, employment, and immigration. You can't afford to rank equally for all of them. We show you which practice areas drive the most qualified clients.",
    date: "2025-12-25",
    author: "Alex Rivera",
    category: "Analytics",
    readTime: "7 min read",
  },
];

export default function LegalBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/legal" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Legal Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-blue-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Legal SEO Playbook</h1>
          <p className="text-lg text-slate-600">High-intent client acquisition through location targeting, practice area positioning, and trust signal optimization.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/legal/${post.slug}`} className="group">
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

      <section className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Local Legal Keywords by Practice Area</h2>
          <p className="text-blue-100 mb-6">Know which practice areas drive most clients. Optimize for location + practice area simultaneously.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold px-8 py-3 rounded-lg hover:bg-blue-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
