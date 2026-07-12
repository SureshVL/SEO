"use client";

import Link from "next/link";
import { ArrowRight, ArrowLeft } from "lucide-react";

export default function LegalCase() {
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
          <p className="text-sm text-blue-600 font-semibold uppercase tracking-wider mb-4">
            Legal Case Study
          </p>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            Location + Practice Area Tracking: 156% Client Growth
          </h1>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-600 uppercase tracking-wider font-semibold mb-1">Practice Area Keywords</div>
              <div className="text-3xl font-bold text-slate-900">23 → 59</div>
              <div className="text-xs text-slate-600 mt-1">top 3 rankings</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="text-xs text-purple-600 uppercase tracking-wider font-semibold mb-1">Client Growth</div>
              <div className="text-3xl font-bold text-slate-900">156%</div>
              <div className="text-xs text-slate-600 mt-1">annual</div>
            </div>
            <div className="p-4 bg-pink-50 rounded-lg border border-pink-200">
              <div className="text-xs text-pink-600 uppercase tracking-wider font-semibold mb-1">Local Keywords</div>
              <div className="text-3xl font-bold text-slate-900">+340</div>
              <div className="text-xs text-slate-600 mt-1">location + practice area</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-xs text-green-600 uppercase tracking-wider font-semibold mb-1">Timeline</div>
              <div className="text-3xl font-bold text-slate-900">4</div>
              <div className="text-xs text-slate-600 mt-1">months</div>
            </div>
          </div>
        </div>

        <div className="prose prose-slate max-u-none">
          <h2>The Challenge</h2>
          <p>
            Law Firm Associates handled bankruptcy, immigration, family law, and employment law. They were competing nationally for generic "bankruptcy lawyer" keywords without capturing location-specific intent. Someone searching "bankruptcy lawyer Chicago" had completely different needs than "bankruptcy lawyer" at the national level.
          </p>

          <h2>The Solution: Location + Practice Area Grid</h2>
          <p>
            We created an intentional keyword strategy grid:
          </p>
          <ul>
            <li><strong>National keywords</strong>: "Bankruptcy lawyer", "Immigration lawyer", "Family lawyer"</li>
            <li><strong>Location keywords</strong>: "Bankruptcy lawyer Chicago", "Bankruptcy lawyer near me", "Chicago bankruptcy attorney"</li>
            <li><strong>Intent keywords</strong>: "How much does bankruptcy cost?", "How to file Chapter 7?", "What happens after immigration?", "Child custody lawyers"</li>
          </ul>

          <p>
            For each combination of location + practice area, we created:
          </p>
          <ul>
            <li>Dedicated practice area landing pages (Bankruptcy, Immigration, Family Law, Employment)</li>
            <li>Location-specific pages per practice area (Bankruptcy in Chicago, Bankruptcy in NYC, etc.)</li>
            <li>Educational content answering intent questions (FAQ-targeted)</li>
            <li>Attorney bio pages optimized for local search</li>
          </ul>

          <h2>Results</h2>
          <ul>
            <li>Practice area rankings (top 3): 23 → 59 (+157%)</li>
            <li>New clients from organic search: 8/mo → 20/mo (+150%)</li>
            <li>Qualified leads (not tire-kickers): 6/mo → 17/mo (+183%)</li>
            <li>Cost per qualified lead: -31%</li>
            <li>Average case value: +23% (location-targeted leads are more serious)</li>
          </ul>

          <h2>Why Location + Practice Area Matters</h2>
          <p>
            Legal services are inherently local. A family lawyer in Chicago can't serve someone in Phoenix. By creating an intentional grid of location + practice area keywords, Law Firm Associates:
          </p>
          <ul>
            <li>Stopped losing leads to national competitors</li>
            <li>Attracted only local, qualified prospects</li>
            <li>Could measure which practice areas drove most revenue by location</li>
            <li>Optimized marketing budget allocation by practice area performance</li>
          </ul>
        </div>

        <div className="mt-16 p-8 bg-blue-50 border border-blue-200 rounded-lg text-center">
          <h3 className="text-xl font-bold text-slate-900 mb-3">Track your legal practice area keywords</h3>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-blue-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-blue-700 transition">
            Start Legal Audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </article>
    </div>
  );
}
