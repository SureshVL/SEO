"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "thought-leadership-content", title: "Thought Leadership Content: Publish Research That Ranks + Converts", excerpt: "Publishing research feels productive but doesn't rank. We analyzed 150 consulting firms and found the 3 content formats that guarantee organic traffic and qualified leads.", date: "2026-01-06", author: "Sarah Chen", category: "Content Strategy", readTime: "10 min read" },
  { slug: "industry-expertise-positioning", title: "Industry Expertise Positioning: Own Your Vertical Keywords", excerpt: "\"Management consulting\" and \"Logistics consulting\" are completely different markets. Winners cluster keywords by expertise. Here's how to position as the authority.", date: "2026-01-01", author: "Marcus Wong", category: "Strategy", readTime: "9 min read" },
  { slug: "consultant-bio-seo", title: "Consultant Bio SEO: Make Partner Profiles Rank (Not Disappear)", excerpt: "Your partners are your differentiator. But their bio pages are invisible to Google. Here's how to make them rank and drive qualified leads.", date: "2025-12-26", author: "Alex Rivera", category: "Technical SEO", readTime: "8 min read" },
  { slug: "case-study-ranking-strategy", title: "Case Study SEO: From Hidden PDFs to Ranked Web Pages", excerpt: "Case studies drive conversions but most are locked in PDFs. Winners convert them to web pages optimized for search. We show you how.", date: "2025-12-21", author: "Sarah Chen", category: "Content Strategy", readTime: "7 min read" },
];

export default function ConsultingBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/consulting" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Consulting Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-slate-700 to-slate-900 text-white py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-300 hover:text-white mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold mb-4">Consulting Firm SEO</h1>
          <p className="text-lg text-slate-300">Build thought leadership. Position consultants as authorities. Rank case studies.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/consulting/${post.slug}`} className="group">
                <h2 className="text-2xl font-bold text-slate-900 mb-3 group-hover:text-slate-700 transition">
                  {post.title}
                </h2>
              </Link>
              <p className="text-slate-600 mb-4">{post.excerpt}</p>
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">
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

      <section className="bg-gradient-to-r from-slate-700 to-slate-900 text-white py-16 mt-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Track Consulting Firm Rankings</h2>
          <p className="text-slate-300 mb-6">Know which expertise areas drive inbound leads. Monitor case study rankings.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-slate-700 font-semibold px-8 py-3 rounded-lg hover:bg-slate-100 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
