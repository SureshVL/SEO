"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  {
    slug: "comparison-keyword-mastery",
    title: "Vs. Keywords: Where Fintech Buyers Make Decisions (And Your Competitor Wins)",
    excerpt: "\"PayPal vs. Stripe\", \"Robo advisor vs. human advisor\" — comparison keywords drive 8x higher qualified leads. We tracked 2,000+ fintech keywords and found your biggest gap.",
    date: "2026-01-13",
    author: "Marcus Wong",
    category: "Strategy",
    readTime: "10 min read",
  },
  {
    slug: "trust-signals-schema",
    title: "Trust Signal Markup: Why Security Certifications Don't Rank (And How to Fix It)",
    excerpt: "You have SOC 2 compliance. Your competitor ranks for it. The difference: schema markup. Here's the exact code that makes trust signals visible to Google.",
    date: "2026-01-07",
    author: "Sarah Chen",
    category: "Technical SEO",
    readTime: "8 min read",
  },
  {
    slug: "regulatory-content-ranking",
    title: "Regulatory Content SEO: How to Rank for Compliance Without Sounding Legal",
    excerpt: "Your privacy policy and regulatory pages are invisible. Competitors' aren't. They reframe legal language as buyer education. Here's how to do it while staying compliant.",
    date: "2026-01-01",
    author: "Alex Rivera",
    category: "Compliance",
    readTime: "9 min read",
  },
  {
    slug: "intent-clustering-fintech",
    title: "Intent Clustering for Fintech: Problem vs. Solution vs. Comparison Keywords",
    excerpt: "Fintech keywords fall into three distinct intents. Own all three and you own the buyer journey. Most competitors ignore two of them entirely.",
    date: "2025-12-29",
    author: "Marcus Wong",
    category: "Keyword Strategy",
    readTime: "7 min read",
  },
];

export default function FintechBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/fintech" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Fintech Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-amber-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Fintech SEO Playbook</h1>
          <p className="text-lg text-slate-600">Win comparison keywords. Build trust signals. Rank regulatory content.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/fintech/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-amber-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-50 text-amber-700 font-medium">
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

      <section className="bg-gradient-to-r from-amber-600 to-orange-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Fintech Comparison Keywords</h2>
          <p className="text-amber-100 mb-6">Know where you rank vs. competitors for buyer intent keywords.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-amber-700 font-semibold px-8 py-3 rounded-lg hover:bg-amber-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
