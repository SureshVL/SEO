"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Circle, Clock } from "lucide-react";

// Case Study Zero — OMNI-RANK optimizing its own parent company's website,
// surrvik.com, in the open. Every number below is real and independently
// verifiable (view source on surrvik.com). The "after" data fills in as the
// optimization proceeds — this is a live, in-progress case study, not a
// finished testimonial.

const BASELINE = [
  { label: "Page title", value: '"React App"', note: "framework default — no brand, no keywords" },
  { label: "Crawlable words", value: "11", note: "search engines & AI assistants see almost nothing" },
  { label: "HTML delivered", value: "644 bytes", note: "an empty create-react-app shell" },
  { label: "Structured data", value: "None", note: "no schema for rich results or AI answers" },
  { label: "H1 heading", value: "Missing", note: "no primary on-page signal" },
  { label: "Rendering", value: "Client-side", note: "content invisible without JavaScript" },
];

const PLAN = [
  { done: false, text: "Migrate from client-side create-react-app to a server-rendered stack (SSR/prerender) so crawlers and AI engines can read the site" },
  { done: false, text: "Real title, meta description and H1 built from the brand + primary services" },
  { done: false, text: "Organization / WebSite / Product schema for rich results and AI citations" },
  { done: false, text: "Publish depth on the products and services the business actually sells" },
  { done: false, text: "Track rankings, AI-search visibility and Search Console — measure the lift" },
];

export default function CaseStudiesPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            Start free trial <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-slate-50 via-violet-50 to-blue-50 py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <span className="inline-flex items-center gap-2 text-xs font-semibold text-violet-700 bg-white border border-violet-200 rounded-full px-3 py-1 mb-6">
            <Clock className="w-3.5 h-3.5" /> Case Study Zero · live &amp; in progress
          </span>
          <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
            We&apos;re fixing our own SEO in the open
          </h1>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto mb-6">
            Instead of showing you invented success stories, we&apos;re running OMNI-RANK on
            our own parent company&apos;s website — <strong>surrvik.com</strong> — and publishing
            the real before-and-after as it happens. Every number below is live and
            verifiable: view source on the site and check it yourself.
          </p>
          <p className="text-xs text-slate-500 max-w-2xl mx-auto bg-white/70 border border-slate-200 rounded-lg px-4 py-3">
            Verified client case studies will be added here, with written permission, as pilot
            engagements complete. We would rather show you one honest work-in-progress than a
            wall of fictional testimonials.
          </p>
        </div>
      </section>

      {/* The starting point */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <p className="text-xs text-violet-600 font-semibold uppercase tracking-wider mb-2">The starting point · today</p>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900">
            surrvik.com scored <span className="text-rose-600">19/100</span> — here&apos;s why
          </h2>
          <p className="text-slate-600 mt-3 max-w-2xl mx-auto">
            The site is an empty create-react-app shell. To a search engine or an AI assistant,
            it is almost invisible. This is the honest baseline we&apos;re starting from.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {BASELINE.map((b) => (
            <div key={b.label} className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">{b.label}</div>
              <div className="text-xl font-bold text-slate-900 mb-1">{b.value}</div>
              <div className="text-xs text-slate-500">{b.note}</div>
            </div>
          ))}
        </div>
      </section>

      {/* The plan */}
      <section className="max-w-3xl mx-auto px-6 pb-16">
        <div className="bg-white border border-slate-200 rounded-2xl p-8">
          <h2 className="text-xl font-bold text-slate-900 mb-1">The plan OMNI-RANK generated</h2>
          <p className="text-sm text-slate-500 mb-6">
            Worked top to bottom — highest-impact fix first. We&apos;ll tick each item and post
            the ranking, AI-visibility and traffic movement as it lands.
          </p>
          <ul className="space-y-4">
            {PLAN.map((step, i) => (
              <li key={i} className="flex items-start gap-3">
                {step.done
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                  : <Circle className="w-5 h-5 text-slate-300 flex-shrink-0 mt-0.5" />}
                <span className="text-sm text-slate-700">{step.text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Results placeholder — honest */}
        <div className="mt-6 border-2 border-dashed border-slate-200 rounded-2xl p-8 text-center">
          <Clock className="w-6 h-6 text-slate-400 mx-auto mb-3" />
          <h3 className="font-semibold text-slate-800">Results — in progress</h3>
          <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
            The &ldquo;after&rdquo; numbers (crawlable content, rankings, AI citations, organic
            traffic) will appear here as the work ships. Bookmark this page and watch it fill in —
            no invented figures until there are real ones.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Run the same audit on your site</h2>
          <p className="text-violet-100 mb-6">
            See exactly what OMNI-RANK sees — free, no card required.
          </p>
          <Link href="/audit" className="inline-flex items-center gap-2 bg-white text-violet-700 font-semibold px-8 py-3 rounded-lg hover:bg-violet-50 transition">
            Audit my site free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
