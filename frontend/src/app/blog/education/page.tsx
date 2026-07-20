"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts = [
  { slug: "program-ranking-strategy", title: "Program Page Rankings: Own \"Best [Degree] Programs\"", excerpt: "\"Best MBA programs\" and \"Best MBA programs in California\" rank differently. Winners cluster keywords by degree type + location. Here's how.", date: "2026-01-05", author: "Sarah Chen", category: "Strategy", readTime: "9 min read" },
  { slug: "affordability-content-seo", title: "Affordability Content Ranks: \"Cost of College\" Questions Drive Prospects", excerpt: "\"How much does college cost?\" and \"Cheapest online degrees\" drive enrollment. Most schools ignore these high-intent questions. Here's why they rank for competitors.", date: "2025-12-31", author: "Marcus Wong", category: "Content Strategy", readTime: "8 min read" },
  { slug: "career-outcomes-transparency", title: "Career Outcomes Content: Show ROI and You'll Own Education Search", excerpt: "Prospective students want to know: \"What can I earn with this degree?\" Schools that answer this question transparently rank higher and convert better.", date: "2025-12-25", author: "Alex Rivera", category: "Trust Signals", readTime: "10 min read" },
  { slug: "program-comparison-strategy", title: "Program Comparison Rankings: Online vs. In-Person, Full-Time vs. Part-Time", excerpt: "Different students compare programs by different criteria. Winners segment keywords and content by comparison type, not just by program.", date: "2025-12-20", author: "Sarah Chen", category: "Intent Segmentation", readTime: "7 min read" },
];

export default function EducationBlogPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/education" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Education Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-indigo-50 to-slate-50 py-16">
        <div className="max-w-4xl mx-auto px-6">
          <Link href="/blog" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-6">
            <ArrowLeft className="w-4 h-4" /> All Blogs
          </Link>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">Education SEO Strategy</h1>
          <p className="text-lg text-slate-600">Own program rankings. Answer affordability questions. Show career outcomes ROI.</p>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="space-y-8">
          {posts.map((post) => (
            <article key={post.slug} className="border-b border-slate-200 pb-8 last:border-0">
              <Link href={`/blog/education/${post.slug}`} className="group">
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
          <h2 className="text-3xl font-bold mb-3">Track Education Program Rankings</h2>
          <p className="text-indigo-100 mb-6">Know which programs drive enrollment. Monitor affordability and outcomes rankings.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-indigo-700 font-semibold px-8 py-3 rounded-lg hover:bg-indigo-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
