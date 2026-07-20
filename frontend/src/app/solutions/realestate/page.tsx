"use client";
import Link from "next/link";
import { ArrowRight, Home, TrendingUp, MapPin } from "lucide-react";

export default function RealEstatePage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/auth/signup" className="text-sm font-semibold text-violet-700">Start free trial <ArrowRight className="w-4 h-4" /></Link>
        </div>
      </header>
      <section className="bg-gradient-to-br from-amber-50 to-slate-50 py-24">
        <div className="max-w-4xl mx-auto px-6">
          <h1 className="text-5xl font-bold text-slate-900 mb-6">Rank your listings. Dominate local search.</h1>
          <p className="text-lg text-slate-600 mb-8">Real estate buyers search hyper-locally: \"homes for sale\", \"neighborhoods\", \"property values\". Track every micro-market variation and own your city.</p>
          <Link href="/auth/signup" className="btn-primary inline-flex items-center gap-2">Free market analysis <ArrowRight className="w-4 h-4" /></Link>
        </div>
      </section>
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-12 text-slate-900">For Real Estate Agents & Teams</h2>
        <div className="grid md:grid-cols-2 gap-8">
          {[
            { icon: <Home className="w-6 h-6 text-amber-600" />, title: "Neighborhood Landing Pages", desc: "Rank for \"best neighborhoods\", \"where to live\", micro-market keywords." },
            { icon: <MapPin className="w-6 h-6 text-amber-600" />, title: "Hyper-Local SEO", desc: "Zip code, neighborhood, school district variations. Own your micromarkets." },
            { icon: <TrendingUp className="w-6 h-6 text-amber-600" />, title: "Listing Page Rankings", desc: "Individual property pages ranking. Know which properties drive search." },
          ].map((item, i) => (
            <div key={i} className="p-6 rounded-lg border border-slate-200">
              <div className="mb-3">{item.icon}</div>
              <h3 className="font-semibold text-slate-900 mb-2">{item.title}</h3>
              <p className="text-sm text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="bg-gradient-to-r from-amber-600 to-orange-600 text-white py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-3">Ready to own your local market?</h2>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-white text-amber-700 font-semibold px-8 py-3 rounded-lg">Get started free <ArrowRight className="w-4 h-4" /></Link>
        </div>
      </section>
    </div>
  );
}
