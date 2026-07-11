"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight, Bot, Check, Globe, Search, MapPin, Store, Sparkles
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 50+ Indian cities
const INDIAN_CITIES = [
  { label: "Hyderabad", code: "hyderabad" },
  { label: "Mumbai", code: "mumbai" },
  { label: "Delhi", code: "delhi" },
  { label: "Bangalore", code: "bangalore" },
  { label: "Chennai", code: "chennai" },
  { label: "Pune", code: "pune" },
  { label: "Kolkata", code: "kolkata" },
  { label: "Ahmedabad", code: "ahmedabad" },
  { label: "Jaipur", code: "jaipur" },
  { label: "Surat", code: "surat" },
  { label: "Lucknow", code: "lucknow" },
  { label: "Kanpur", code: "kanpur" },
  { label: "Nagpur", code: "nagpur" },
  { label: "Visakhapatnam", code: "visakhapatnam" },
  { label: "Bhopal", code: "bhopal" },
  { label: "Patna", code: "patna" },
  { label: "Vadodara", code: "vadodara" },
  { label: "Ghaziabad", code: "ghaziabad" },
  { label: "Ludhiana", code: "ludhiana" },
  { label: "Agra", code: "agra" },
  { label: "Nashik", code: "nashik" },
  { label: "Rajkot", code: "rajkot" },
  { label: "Meerut", code: "meerut" },
  { label: "Coimbatore", code: "coimbatore" },
  { label: "Kochi", code: "kochi" },
  { label: "Indore", code: "indore" },
  { label: "Chandigarh", code: "chandigarh" },
  { label: "Guwahati", code: "guwahati" },
  { label: "Bhubaneswar", code: "bhubaneswar" },
  { label: "Thiruvananthapuram", code: "thiruvananthapuram" },
];

// 12 business type categories
const BUSINESS_TYPES = [
  { label: "Restaurant / Food", code: "restaurant", emoji: "🍽️" },
  { label: "Healthcare / Clinic", code: "healthcare", emoji: "🏥" },
  { label: "Education / Coaching", code: "education", emoji: "📚" },
  { label: "Real Estate", code: "real_estate", emoji: "🏠" },
  { label: "SaaS / Tech", code: "saas", emoji: "💻" },
  { label: "E-commerce / Retail", code: "ecommerce", emoji: "🛒" },
  { label: "Legal / CA Services", code: "legal", emoji: "⚖️" },
  { label: "Travel / Hospitality", code: "travel", emoji: "✈️" },
  { label: "Fitness / Wellness", code: "fitness", emoji: "💪" },
  { label: "Finance / Insurance", code: "finance", emoji: "💰" },
  { label: "Manufacturing / B2B", code: "manufacturing", emoji: "🏭" },
  { label: "Other / General", code: "general", emoji: "🌐" },
];

const steps = [
  { id: 1, title: "Your website", icon: Globe, desc: "Tell us about your site" },
  { id: 2, title: "Your city", icon: MapPin, desc: "Where are your customers?" },
  { id: 3, title: "Business type", icon: Store, desc: "What kind of business?" },
  { id: 4, title: "Target keywords", icon: Search, desc: "What do you want to rank for?" },
  { id: 5, title: "First analysis", icon: Bot, desc: "Run your first AI audit" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { apiKey, setBusinessProfile } = useAppStore();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [projectId, setProjectId] = useState("");

  const [form, setForm] = useState({
    name: "",
    url: "",
    city: "",
    cityCode: "",
    businessType: "",
    businessTypeLabel: "",
    keywords: "",
  });

  async function handleStep1(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name || new URL(form.url).hostname,
          client_url: form.url,
          target_niche: null,
          goal_keywords: [],
          settings: { city: form.cityCode, business_type: form.businessType },
        }),
      });
      if (!res.ok) throw new Error("Failed to create project");
      const project = await res.json();
      setProjectId(project.id);
      setStep(2);
    } catch (err: any) {
      toast.error(err.message);
    } finally { setLoading(false); }
  }

  function handleStep2(city: { label: string; code: string }) {
    setForm({ ...form, city: city.label, cityCode: city.code });
    setStep(3);
  }

  function handleStep3(bt: { label: string; code: string }) {
    setForm({ ...form, businessType: bt.code, businessTypeLabel: bt.label });
    setStep(4);
  }

  async function handleStep4(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const keywords = form.keywords.split(",").map(k => k.trim()).filter(Boolean);
      for (const kw of keywords.slice(0, 10)) {
        await fetch(`${API}/projects/${projectId}/keywords`, {
          method: "POST",
          headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
          body: JSON.stringify({
            keyword: kw,
            target_region: "IN",
            locale: "en-US",
          }),
        });
      }
      // Save business profile to store for auto-wiring into tools
      setBusinessProfile({
        city: form.city,
        cityCode: form.cityCode,
        businessType: form.businessType,
        businessTypeLabel: form.businessTypeLabel,
        keywords: keywords,
        websiteUrl: form.url,
        projectId,
        projectName: form.name || new URL(form.url).hostname,
      });
      setStep(5);
    } catch (err: any) {
      toast.error(err.message);
    } finally { setLoading(false); }
  }

  async function handleStep5() {
    setLoading(true);
    try {
      const firstKeyword = form.keywords.split(",")[0]?.trim() || "seo";
      const localKeyword = form.city ? `${firstKeyword} in ${form.city}` : firstKeyword;
      await fetch(`${API}/jobs/research`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({
          research_request: {
            client_url: form.url,
            primary_keyword: localKeyword,
            project_id: projectId,
            target_region: "IN",
            business_type: form.businessType,
            city: form.cityCode,
          },
        }),
      });
      toast.success("Your first AI analysis is running!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message);
    } finally { setLoading(false); }
  }

  const [citySearch, setCitySearch] = useState("");
  const filteredCities = INDIAN_CITIES.filter(c =>
    c.label.toLowerCase().includes(citySearch.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-surface-1 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Brand */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold text-xs font-serif">OR</div>
            <span className="font-bold text-lg">OMNI-RANK</span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="flex items-center justify-center gap-1.5 mb-10">
          {steps.map((s) => (
            <div key={s.id} className="flex items-center gap-1.5">
              <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300",
                step > s.id ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" :
                step === s.id ? "bg-brand-600 text-white ring-2 ring-brand-400/30" :
                "bg-zinc-800 text-zinc-600 border border-zinc-700"
              )}>
                {step > s.id ? <Check className="w-3.5 h-3.5" /> : s.id}
              </div>
              {s.id < 5 && <div className={cn("w-8 h-0.5 rounded", step > s.id ? "bg-emerald-500/30" : "bg-zinc-800")} />}
            </div>
          ))}
        </div>

        <div className="text-center mb-6">
          <h1 className="text-xl font-bold">{steps[step - 1].title}</h1>
          <p className="text-sm text-zinc-400 mt-1">{steps[step - 1].desc}</p>
        </div>

        {/* Step 1: Website */}
        {step === 1 && (
          <form onSubmit={handleStep1} className="card p-6 space-y-4 animate-fade-in">
            <div>
              <label className="label">Website URL</label>
              <input type="url" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })}
                className="input-field" placeholder="https://yoursite.com" required autoFocus />
            </div>
            <div>
              <label className="label">Project Name (optional)</label>
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                className="input-field" placeholder="e.g. My Company" />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* Step 2: City */}
        {step === 2 && (
          <div className="card p-6 animate-fade-in space-y-4">
            <input
              type="text"
              value={citySearch}
              onChange={e => setCitySearch(e.target.value)}
              className="input-field"
              placeholder="Search city..."
              autoFocus
            />
            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
              {filteredCities.map((city) => (
                <button
                  key={city.code}
                  onClick={() => handleStep2(city)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-left transition-all border",
                    form.cityCode === city.code
                      ? "bg-brand-600/20 border-brand-500/40 text-brand-300"
                      : "bg-zinc-800/40 border-zinc-700/40 text-zinc-300 hover:bg-zinc-700/40"
                  )}
                >
                  <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                  {city.label}
                </button>
              ))}
            </div>
            <button onClick={() => setStep(3)} className="btn-ghost text-sm w-full text-center">
              Skip — target all India
            </button>
          </div>
        )}

        {/* Step 3: Business Type */}
        {step === 3 && (
          <div className="card p-6 animate-fade-in">
            <div className="grid grid-cols-2 gap-2">
              {BUSINESS_TYPES.map((bt) => (
                <button
                  key={bt.code}
                  onClick={() => handleStep3(bt)}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-3 rounded-lg text-sm text-left transition-all border",
                    form.businessType === bt.code
                      ? "bg-brand-600/20 border-brand-500/40 text-brand-300"
                      : "bg-zinc-800/40 border-zinc-700/40 text-zinc-300 hover:bg-zinc-700/40"
                  )}
                >
                  <span className="text-lg">{bt.emoji}</span>
                  <span className="text-xs font-medium leading-tight">{bt.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Keywords */}
        {step === 4 && (
          <form onSubmit={handleStep4} className="card p-6 space-y-4 animate-fade-in">
            {form.city && (
              <div className="flex items-center gap-2 text-xs bg-brand-500/10 border border-brand-500/20 rounded-lg px-3 py-2 text-brand-300">
                <Sparkles className="w-3.5 h-3.5" />
                We'll auto-localise keywords for <strong>{form.city}</strong> ({form.businessTypeLabel})
              </div>
            )}
            <div>
              <label className="label">Target Keywords (comma-separated)</label>
              <textarea
                value={form.keywords}
                onChange={e => setForm({ ...form, keywords: e.target.value })}
                className="input-field h-28"
                placeholder={`e.g. ${form.businessType === "restaurant" ? "best restaurant near me, biryani in " + (form.city || "Hyderabad") : "seo tools india, rank higher google"}`}
                required
                autoFocus
              />
              <p className="text-xs text-zinc-500 mt-1.5">Up to 10 keywords. City context is auto-added.</p>
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(3)} className="btn-secondary flex-1">Back</button>
              <button type="submit" disabled={loading} className="btn-primary flex-1 flex items-center justify-center gap-2">
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}

        {/* Step 5: Launch */}
        {step === 5 && (
          <div className="card p-8 text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-5">
              <Bot className="w-8 h-8 text-brand-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Ready to launch</h3>
            <div className="text-sm text-zinc-400 mb-5 space-y-1">
              <p>🌆 City: <span className="text-zinc-200">{form.city || "All India"}</span></p>
              <p>🏢 Business: <span className="text-zinc-200">{form.businessTypeLabel}</span></p>
              <p>🔑 Keywords: <span className="text-zinc-200">{form.keywords.split(",").slice(0, 3).join(", ")}{form.keywords.split(",").length > 3 ? "…" : ""}</span></p>
            </div>
            <p className="text-sm text-zinc-500 mb-6">
              Claude will analyse competitors for your primary keyword with city-level targeting baked in.
            </p>
            <div className="flex gap-3">
              <button onClick={() => router.push("/dashboard")} className="btn-secondary flex-1">Skip for now</button>
              <button onClick={handleStep5} disabled={loading} className="btn-primary flex-1 flex items-center justify-center gap-2">
                <Bot className="w-4 h-4" /> Run Analysis
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
