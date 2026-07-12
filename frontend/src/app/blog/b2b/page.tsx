"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  {
    slug: "buyer-persona-segmentation",
    title: "B2B Buyer Personas: CTOs Search Differently Than CFOs (Track Both)",
    excerpt: "\"Cloud infrastructure\" means different things to CTOs vs. CFOs. Most B2B companies miss this segmentation entirely. We mapped 1,000+ B2B keywords across 5 buyer personas.",
    date: "2026-01-11",
    author: "Sarah Chen",
    category: "Strategy",
    readTime: "10 min read",
  },
  {
    slug: "consultancy-benchmarking",
    title: "Consultancy Benchmarking: Find Where McKinsey Isn't Ranking",
    excerpt: "Your competitors include McKinsey and BCG. You can't outrank them on every keyword. But we found 60+ high-value keywords where they have zero presence. Here's how to find yours.",
    date: "2026-01-06",
    author: "Marcus Wong",
    category: "Competitive Intelligence",
    readTime: "11 min read",
  },
  {
    slug: "thought-leadership-roi",
    title: "Thought Leadership ROI: Which Research Pieces Actually Drive Leads?",
    excerpt: "Publishing research feels productive. But which pieces drive rankings? We analyzed 200+ B2B thought leadership campaigns and found the 3 formats that guarantee organic traffic.",
    date: "2025-12-31",
    author: "Alex Rivera",
    category: "Content Strategy",
    readTime: "9 min read",
  },
  {
    slug: "sales-cycle-mapping",
    title: "Sales Cycle Keyword Mapping: Know Your Pipeline Before Your Sales Team Does",
    excerpt: "B2B sales cycles are 6+ months. Awareness keywords differ from decision keywords differ from negotiation keywords. Map your keywords to pipeline stages and you'll know where leads come from.",
    date: "2025-12-24",
    author: "Sarah Chen",
    category: "Revenue Intelligence",
    readTime: "8 min read",
  },
];

export default function B2BBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/b2b" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            B2B Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-purple-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">B2B Enterprise SEO</h1>
          <p className="text-lg text-slate-600">Buyer persona segmentation, thought leadership, and sales cycle mapping for enterprises.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/b2b/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-purple-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-purple-50 text-purple-700 font-medium">
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

      <section className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Map B2B Buyer Personas to Keywords</h2>
          <p className="text-purple-100 mb-6">Track CTO, CFO, VP Sales keywords separately. Know your competitive landscape.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-purple-700 font-semibold px-8 py-3 rounded-lg hover:bg-purple-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
