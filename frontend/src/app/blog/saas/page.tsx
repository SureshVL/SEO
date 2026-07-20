"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  {
    slug: "saas-feature-keyword-clusters",
    title: "The Hidden Keyword Cluster Strategy SaaS Competitors Miss",
    excerpt: "Most SaaS companies rank for product features separately. The winners cluster them. We analyzed 500 B2B SaaS companies and found that intentional feature keyword clustering drives 3.4x more qualified traffic than scattered rankings.",
    date: "2026-01-15",
    author: "Sarah Chen",
    category: "Strategy",
    readTime: "8 min read",
  },
  {
    slug: "launch-day-ranking-seo",
    title: "How to Rank on Day 1: The SaaS Launch SEO Playbook",
    excerpt: "New product launch in 30 days? Don't wait until day 0 to think about SEO. We reverse-engineered 47 successful SaaS launches and found the 3 SEO plays that guarantee first-page rankings by launch day.",
    date: "2026-01-10",
    author: "Marcus Wong",
    category: "Launch Strategy",
    readTime: "10 min read",
  },
  {
    slug: "competitor-feature-mapping",
    title: "Competitor Feature Mapping: Turn Weakness Into Ranking Wins",
    excerpt: "Your competitors have more features than you. But they rank for all of them equally. Find the gaps where they're weak, own those rankings, and force them to compete on your terms.",
    date: "2026-01-05",
    author: "Sarah Chen",
    category: "Competitive Intelligence",
    readTime: "9 min read",
  },
  {
    slug: "pricing-page-seo",
    title: "Why Pricing Pages Rank (And How to Make Yours Compete)",
    excerpt: "Pricing pages drive 40% more qualified leads than product pages for SaaS. But only 12% of SaaS companies optimize them for search. Here's exactly how to rank your pricing page in the top 3.",
    date: "2025-12-28",
    author: "Alex Rivera",
    category: "Conversion Optimization",
    readTime: "7 min read",
  },
];

export default function SaasBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/saas" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            SaaS Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-indigo-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">SaaS SEO Strategy</h1>
          <p className="text-lg text-slate-600">Deep dives into feature clustering, competitive positioning, and launch strategies that rank.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/saas/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-indigo-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium">
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

      <section className="bg-gradient-to-r from-indigo-600 to-blue-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track SaaS Feature Rankings in Real-Time</h2>
          <p className="text-indigo-100 mb-6">Get daily updates on which features drive traffic. Know exactly when competitors enter your keywords.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-indigo-700 font-semibold px-8 py-3 rounded-lg hover:bg-indigo-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
