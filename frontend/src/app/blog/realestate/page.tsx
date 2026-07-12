"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "neighborhood-landing-pages", title: "Neighborhood Landing Pages: Own Your Micro-Markets", excerpt: "Most real estate agents compete nationally for generic keywords. Winners rank locally for neighborhood keywords. Here's the exact framework.", date: "2026-01-09", author: "Sarah Chen", category: "Local SEO", readTime: "9 min read" },
  { slug: "hyper-local-seo", title: "Hyper-Local SEO: Zip Code + School District + Market Segments", excerpt: "\"Homes in Palo Alto\" and \"Homes in Palo Alto near Stanford\" are different markets. Track them separately and you'll own your city.", date: "2026-01-04", author: "Marcus Wong", category: "Strategy", readTime: "8 min read" },
  { slug: "listing-page-rankings", title: "Listing Page Rankings: From Zero to Ranked in 30 Days", excerpt: "Individual property listings should rank for hyper-local keywords. Most agents ignore them. Here's how top agents get listing pages to rank.", date: "2025-12-29", author: "Alex Rivera", category: "Technical SEO", readTime: "10 min read" },
  { slug: "market-analysis-seo", title: "Market Analysis Content: Turn Data Into Ranking Authority", excerpt: "Market data is your unique asset. Reframe it as \"neighborhood guides\" and you'll rank for 50+ keyword variations while competitors fight for the same 5 keywords.", date: "2025-12-20", author: "Sarah Chen", category: "Content Strategy", readTime: "7 min read" },
];

export default function RealEstateBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/realestate" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Real Estate Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-amber-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Real Estate SEO Strategy</h1>
          <p className="text-lg text-slate-600">Own your neighborhoods. Rank hyper-local keywords. Dominate your micro-markets.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/realestate/${post.slug}`} className="group">
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
          <h2 className="text-3xl font-bold mb-3">Track Neighborhood Keyword Rankings</h2>
          <p className="text-amber-100 mb-6">Own your micro-markets. Know which neighborhoods drive most leads.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-amber-700 font-semibold px-8 py-3 rounded-lg hover:bg-amber-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
