"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  {
    slug: "product-page-seo-strategy",
    title: "Product Page SEO: From 20 Keywords Ranking to 200+",
    excerpt: "Your competitors optimize individual product pages independently. You should own entire keyword clusters per product category. We show you how to 10x your product page traffic.",
    date: "2026-01-14",
    author: "Alex Rivera",
    category: "Strategy",
    readTime: "9 min read",
  },
  {
    slug: "serp-features-ecommerce",
    title: "Why Your Products Disappear on SERP: Rich Results Strategy",
    excerpt: "Only 8% of ecommerce sites optimize for Google Shopping, FAQ schema, and product reviews properly. The ones that do capture 40% more clicks from SERPs. Here's the exact checklist.",
    date: "2026-01-09",
    author: "Sarah Chen",
    category: "Technical SEO",
    readTime: "8 min read",
  },
  {
    slug: "review-schema-domination",
    title: "Review Schema Domination: How Top Brands Display 5 Stars on Google",
    excerpt: "Competitor products have stars, reviews, and prices showing on SERP. Yours don't. It's not luck — it's schema. We reverse-engineered 1,000 top ecommerce sites to show you exactly how.",
    date: "2026-01-03",
    author: "Marcus Wong",
    category: "Schema Markup",
    readTime: "7 min read",
  },
  {
    slug: "variant-seo-guide",
    title: "Product Variant SEO: Stop Cannibalizing Your Own Rankings",
    excerpt: "You have 50 color variations of the same shirt. They're all competing for the same keywords. Learn how winners handle variants to prevent cannibalization and maximize rankings.",
    date: "2025-12-26",
    author: "Alex Rivera",
    category: "Technical SEO",
    readTime: "10 min read",
  },
];

export default function EcommerceBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/ecommerce" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Ecommerce Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-emerald-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Ecommerce SEO Playbook</h1>
          <p className="text-lg text-slate-600">Grow product page traffic. Master schema, reviews, and variant optimization.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/ecommerce/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-emerald-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium">
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

      <section className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Every Product Page Ranking</h2>
          <p className="text-emerald-100 mb-6">Know which products drive traffic. Track price competitiveness in SERPs.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-emerald-700 font-semibold px-8 py-3 rounded-lg hover:bg-emerald-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
