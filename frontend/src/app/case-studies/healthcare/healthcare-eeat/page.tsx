"use client";

import Link from "next/link";
import { ArrowRight, ArrowLeft } from "lucide-react";

export default function HealthcareCase() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/case-studies" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            All Case Studies <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <article className="max-w-4xl mx-auto px-6 py-16">
        <Link href="/case-studies" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-8">
          <ArrowLeft className="w-4 h-4" /> All Case Studies
        </Link>

        <div className="mb-12">
          <p className="text-sm text-red-600 font-semibold uppercase tracking-wider mb-4">
            Healthcare Case Study
          </p>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            E-E-A-T Recovery: From Invisible to Top 3
          </h1>
          <p className="text-lg text-slate-600 mb-8">
            How HealthCare Plus recovered from Google's core update with E-E-A-T signal optimization.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="text-xs text-red-600 uppercase tracking-wider font-semibold mb-1">Traffic Loss</div>
              <div className="text-3xl font-bold text-slate-900">-72% → +89%</div>
              <div className="text-xs text-slate-600 mt-1">recovery in 5 months</div>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-600 uppercase tracking-wider font-semibold mb-1">Keywords Top 3</div>
              <div className="text-3xl font-bold text-slate-900">8 → 67</div>
              <div className="text-xs text-slate-600 mt-1">738% increase</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-xs text-green-600 uppercase tracking-wider font-semibold mb-1">Author Bios Added</div>
              <div className="text-3xl font-bold text-slate-900">847</div>
              <div className="text-xs text-slate-600 mt-1">credibility signals</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="text-xs text-purple-600 uppercase tracking-wider font-semibold mb-1">YE-E-A-T Score</div>
              <div className="text-3xl font-bold text-slate-900">62 → 89</div>
              <div className="text-xs text-slate-600 mt-1">43% improvement</div>
            </div>
          </div>
        </div>

        <div className="prose prose-slate max-w-none">
          <h2>The Problem</h2>
          <p>
            HealthCare Plus lost 72% of organic traffic after Google's March core update targeted medical content without sufficient E-E-A-T (Experience, Expertise, Authority, Trustworthiness) signals. Their content was medically accurate but lacked author credentials, internal linking, and structural authority markers.
          </p>

          <h2>The Solution: E-E-A-T Audit Framework</h2>
          <p>
            We implemented OMNI-RANK's comprehensive E-E-A-T framework:
          </p>
          <ul>
            <li><strong>Author Credentials</strong>: Added 847 physician/specialist author profiles with credentials, board certifications, and experience</li>
            <li><strong>Internal Authority Linking</strong>: Restructured navigation to build topical authority clusters</li>
            <li><strong>Medical Entity Markup</strong>: Implemented MedicalEntity schema with doctor credentials, specializations, and affiliations</li>
            <li><strong>Clinical Evidence</strong>: Added citation markers linking to peer-reviewed studies and medical references</li>
            <li><strong>Organization Authority</strong>: Built YMYL-compliant organization schema with insurance participation, accreditations, and compliance certifications</li>
          </ul>

          <h2>Results: Recovery + Growth</h2>
          <ul>
            <li>Organic traffic: -72% → +89% (161 point swing)</li>
            <li>Keywords top 3: 8 → 67 (+738%)</li>
            <li>Patient inquiries: 1,200 → 2,268 per month (+89%)</li>
            <li>Conversion rate: Improved 23% (more qualified, qualified patients from SERP)</li>
          </ul>

          <h2>Key Insight</h2>
          <p>
            Google's E-E-A-T requirement isn't about penalizing content. It's about rewarding trustworthy, expert-backed information. HealthCare Plus didn't need new content. They needed to make existing expertise visible to Google through proper schema, author bios, and structural authority signals.
          </p>
        </div>

        <div className="mt-16 p-8 bg-red-50 border border-red-200 rounded-lg text-center">
          <h3 className="text-xl font-bold text-slate-900 mb-3">Audit your E-E-A-T signals</h3>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-red-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-red-700 transition">
            Start Healthcare Audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </article>
    </div>
  );
}
