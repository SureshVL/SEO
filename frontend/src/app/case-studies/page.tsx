"use client";

import Link from "next/link";
import { ArrowRight, TrendingUp } from "lucide-react";

const caseStudies = [
  {
    title: "SaaS Feature Clustering: 340% Keyword Growth",
    company: "Acme CRM",
    vertical: "saas",
    metrics: { before: 47, after: 207, improvement: "340%", timeframe: "6 months" },
    description: "Feature-focused keyword clustering increased rankings from 47 to 207 for core feature keywords.",
  },
  {
    title: "Ecommerce Product SEO: 28% Revenue Increase",
    company: "ShopFlow",
    vertical: "ecommerce",
    metrics: { before: "12%", after: "28%", improvement: "+16%", timeframe: "4 months" },
    description: "Product page optimization with schema markup increased organic revenue contribution.",
  },
  {
    title: "Healthcare E-E-A-T: 89% More Qualified Traffic",
    company: "HealthCare Plus",
    vertical: "healthcare",
    metrics: { before: 1200, after: 2268, improvement: "89%", timeframe: "5 months" },
    description: "E-E-A-T signal optimization reclaimed lost traffic from Google's core update.",
  },
  {
    title: "Fintech Comparison Keywords: 4.2x Leads",
    company: "PayFlow",
    vertical: "fintech",
    metrics: { before: 8, after: 34, improvement: "4.2x", timeframe: "3 months" },
    description: "Dominating 'vs.' comparison keywords captured buyer decision-making intent.",
  },
  {
    title: "B2B Persona Segmentation: 287% Pipeline Growth",
    company: "CloudTech Inc",
    vertical: "b2b",
    metrics: { before: "18%", after: "52%", improvement: "+34%", timeframe: "7 months" },
    description: "Buyer persona segmentation aligned keyword strategy to sales cycle stages.",
  },
  {
    title: "Legal Practice Area Ranking: 156% Client Growth",
    company: "Law Firm Associates",
    vertical: "legal",
    metrics: { before: 23, after: 59, improvement: "156%", timeframe: "4 months" },
    description: "Location + practice area tracking increased qualified lead volume across all areas.",
  },
];

export default function CaseStudiesPage() {
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
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">Real Results. Real Numbers. Real Companies.</h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            How brands across 13 industries used OMNI-RANK to dominate keyword rankings and drive qualified leads.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-8">
          {caseStudies.map((study, i) => (
            <Link
              key={i}
              href={`/case-studies/${study.vertical}/${study.title.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
              className="group"
            >
              <div className="card p-6 h-full border border-slate-200 hover:border-violet-300 hover:shadow-lg transition">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-xs text-violet-600 font-semibold uppercase tracking-wider mb-2">
                      Case Study
                    </p>
                    <h3 className="text-xl font-bold text-slate-900 group-hover:text-violet-600 transition">
                      {study.title}
                    </h3>
                  </div>
                  <TrendingUp className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                </div>

                <p className="text-sm text-slate-600 mb-6">{study.description}</p>

                <div className="space-y-2 mb-6 pb-6 border-b border-slate-200">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Company</span>
                    <span className="font-semibold text-slate-900">{study.company}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Timeframe</span>
                    <span className="font-semibold text-slate-900">{study.metrics.timeframe}</span>
                  </div>
                </div>

                <div className="text-center">
                  <div className="text-3xl font-bold text-emerald-600 mb-1">
                    {study.metrics.improvement}
                  </div>
                  <p className="text-xs text-slate-600">improvement</p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Get Your Success Story Next</h2>
          <p className="text-violet-100 mb-6">Join companies that have already increased keyword rankings and qualified leads.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-violet-700 font-semibold px-8 py-3 rounded-lg hover:bg-violet-50 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
