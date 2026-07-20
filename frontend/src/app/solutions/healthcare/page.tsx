"use client";

import Link from "next/link";
import { ArrowRight, Heart, Shield, TrendingUp, Stethoscope } from "lucide-react";

export default function HealthcareSolutionPage() {
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

      <section className="bg-gradient-to-br from-blue-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">
            Build medical authority.<br />
            Own health searches.
          </h1>
          <p className="text-lg text-slate-600 mb-8 max-w-2xl">
            Healthcare SEO lives or dies on E-E-A-T: Expertise, Experience, Authoritativeness, Trustworthiness. OMNI-RANK audits E-E-A-T signals and tells you exactly what's preventing your brand from ranking for health queries.
          </p>
          <Link href="/auth/signup" className="btn-primary inline-flex items-center gap-2">
            Free E-E-A-T audit <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">Healthcare Ranking Challenges</h2>
            {[
              { title: "E-E-A-T Blindspots", desc: "Missing author bios, credentials, publication dates. Google penalizes you for not proving authority." },
              { title: "Medical Entity Coverage", desc: "Competitors are structured better. You mention a condition 10x but don't mark up entities properly." },
              { title: "Regulatory Complexity", desc: "Privacy, disclaimers, fact-checking compliance. One wrong move and you lose rankings." },
              { title: "Reviews & Reputation", desc: "Patients leaving reviews on Google, Healthgrades, but you can't track how this impacts rankings." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-red-600 font-bold">✕</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>

          <div>
            <h2 className="text-3xl font-bold mb-6 text-slate-900">OMNI-RANK E-E-A-T Framework</h2>
            {[
              { title: "E-E-A-T Signal Audit", desc: "Crawl your site. Flag missing author bios, credentials, publication dates." },
              { title: "Medical Entity Mapping", desc: "Structure every condition, treatment, medication as proper schema. Match competitor rigor." },
              { title: "Compliance Checker", desc: "Audit disclaimers, privacy, fact-checking. Know if regulatory changes hurt you." },
              { title: "Reputation Integration", desc: "Pull patient reviews from Google, Healthgrades. See how they correlate with rankings." },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 mb-4">
                <span className="text-blue-600 font-bold">✓</span>
                <div>
                  <h3 className="font-semibold text-slate-900 mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-600">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-blue-900 text-white py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-3xl font-bold mb-12 text-center">Healthcare Results</h2>
          <div className="grid md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">89%</div>
              <div className="text-sm text-slate-300">E-E-A-T signal improvement (first audit)</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">340%</div>
              <div className="text-sm text-slate-300">Avg. page-1 keyword increase (health queries)</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-blue-400 mb-2">12 weeks</div>
              <div className="text-sm text-slate-300">Time to fix critical compliance issues</div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">Built for Healthcare</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            { icon: <Heart />, title: "E-E-A-T Framework", desc: "Built-in checklist for Expertise, Experience, Authority, Trustworthiness." },
            { icon: <Shield />, title: "HIPAA Compliance", desc: "Audit your site for HIPAA compliance. Know if you're violating privacy regulations." },
            { icon: <Stethoscope />, title: "Medical Entity Database", desc: "Match conditions, medications, procedures to schema.org markup standards." },
            { icon: <TrendingUp />, title: "Reputation Signals", desc: "Integrate Google reviews, Healthgrades, RateMDs to see patient satisfaction impact." },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200 hover:border-blue-300 transition">
              <div className="text-blue-600 mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to own health search?</h2>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold px-8 py-3 rounded-lg">
            Get started free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
