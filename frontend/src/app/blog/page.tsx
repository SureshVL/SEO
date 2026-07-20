"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

const verticals = [
  {
    name: "SaaS",
    href: "/blog/saas",
    description: "Feature clustering, competitive positioning, and launch strategies",
    postCount: 4,
    color: "indigo",
  },
  {
    name: "Ecommerce",
    href: "/blog/ecommerce",
    description: "Product page SEO, SERP features, and conversion optimization",
    postCount: 4,
    color: "emerald",
  },
  {
    name: "Healthcare",
    href: "/blog/healthcare",
    description: "E-E-A-T audits, entity mapping, and compliance considerations",
    postCount: 4,
    color: "red",
  },
  {
    name: "Fintech",
    href: "/blog/fintech",
    description: "Comparison keywords, trust signals, and regulatory content",
    postCount: 4,
    color: "amber",
  },
  {
    name: "B2B",
    href: "/blog/b2b",
    description: "Buyer persona segmentation, thought leadership, and sales cycle mapping",
    postCount: 4,
    color: "purple",
  },
  {
    name: "Legal",
    href: "/blog/legal",
    description: "Local intent, practice area tracking, and client acquisition",
    postCount: 4,
    color: "blue",
  },
  {
    name: "Real Estate",
    href: "/blog/realestate",
    description: "Hyper-local SEO, neighborhood pages, and listing optimization",
    postCount: 4,
    color: "amber",
  },
  {
    name: "Local Services",
    href: "/blog/local",
    description: "Map pack optimization, near-me search, and local intent",
    postCount: 4,
    color: "cyan",
  },
];

const colorMap: Record<string, string> = {
  indigo: "from-indigo-50 to-blue-50 border-indigo-200",
  emerald: "from-emerald-50 to-teal-50 border-emerald-200",
  red: "from-red-50 to-pink-50 border-red-200",
  amber: "from-amber-50 to-orange-50 border-amber-200",
  purple: "from-purple-50 to-indigo-50 border-purple-200",
  blue: "from-blue-50 to-cyan-50 border-blue-200",
  cyan: "from-cyan-50 to-blue-50 border-cyan-200",
};

export default function BlogHomePage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <section className="bg-gradient-to-br from-slate-50 via-violet-50 to-blue-50 py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">Industry-Specific SEO Playbooks</h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Deep dives into what actually works for each industry. From feature clustering to E-E-A-T optimization to comparison keyword dominance.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-6">
          {verticals.map((vertical) => {
            const [from, to, border] = colorMap[vertical.color]?.split(" ") || [];
            return (
              <Link
                key={vertical.href}
                href={vertical.href}
                className={`bg-gradient-to-br ${vertical.color === 'indigo' ? 'from-indigo-50 to-blue-50 border-indigo-200' :
                             vertical.color === 'emerald' ? 'from-emerald-50 to-teal-50 border-emerald-200' :
                             vertical.color === 'red' ? 'from-red-50 to-pink-50 border-red-200' :
                             vertical.color === 'amber' ? 'from-amber-50 to-orange-50 border-amber-200' :
                             vertical.color === 'purple' ? 'from-purple-50 to-indigo-50 border-purple-200' :
                             vertical.color === 'blue' ? 'from-blue-50 to-cyan-50 border-blue-200' :
                             vertical.color === 'cyan' ? 'from-cyan-50 to-blue-50 border-cyan-200' :
                             'from-slate-50 to-slate-100 border-slate-200'} border rounded-xl p-6 hover:shadow-lg transition group`}
              >
                <h3 className="text-2xl font-bold text-slate-900 mb-2 group-hover:text-indigo-600">{vertical.name}</h3>
                <p className="text-slate-600 mb-4">{vertical.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-600">{vertical.postCount} articles</span>
                  <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to dominate your industry keywords?</h2>
          <p className="text-violet-100 mb-6">Track your rankings across all verticals. Get daily insights on what's working.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-violet-700 font-semibold px-8 py-3 rounded-lg hover:bg-violet-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
