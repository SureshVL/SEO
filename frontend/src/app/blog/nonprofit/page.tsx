"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "donor-intent-keywords", title: "Donor Intent Keywords: Own \"Donate to [Cause]\" Search", excerpt: "Donors search with clear intent: \"donate to environmental nonprofits\", \"donate money to education\". Winners optimize for these high-intent keywords.", date: "2026-01-04", author: "Sarah Chen", category: "Donor Acquisition", readTime: "8 min read" },
  { slug: "volunteer-recruitment-seo", title: "Volunteer Recruitment SEO: Own \"Volunteer Opportunities\"", excerpt: "\"Volunteer opportunities\" and \"Where to volunteer\" are high-intent keywords. Most nonprofits ignore them. Here's how to capture volunteering prospects.", date: "2025-12-30", author: "Marcus Wong", category: "Recruitment", readTime: "7 min read" },
  { slug: "impact-storytelling-strategy", title: "Impact Stories That Rank: From Blog Posts to Rankings", excerpt: "Donor impact stories drive conversions but don't rank. We show you how to structure and optimize impact stories for both Google and human readers.", date: "2025-12-23", author: "Alex Rivera", category: "Content Strategy", readTime: "9 min read" },
  { slug: "nonprofit-transparency-seo", title: "Nonprofit Transparency Pages: Annual Reports + Financial Disclosures Rank", excerpt: "Donors want transparency. Annual reports and financial pages should rank. Here's how to structure them for search without compromising credibility.", date: "2025-12-18", author: "Sarah Chen", category: "Trust Signals", readTime: "8 min read" },
];

export default function NonprofitBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/nonprofit" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Nonprofit Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-rose-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Nonprofit SEO Playbook</h1>
          <p className="text-lg text-slate-600">Own donor intent. Recruit volunteers. Build trust through transparency.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/nonprofit/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-rose-600 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-rose-50 text-rose-700 font-medium">
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

      <section className="bg-gradient-to-r from-rose-600 to-pink-600 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Donor & Volunteer Keywords</h2>
          <p className="text-rose-100 mb-6">Know which causes drive traffic. Monitor donor intent search performance.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-rose-700 font-semibold px-8 py-3 rounded-lg hover:bg-rose-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
