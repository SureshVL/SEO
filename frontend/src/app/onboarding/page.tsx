"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Bot, Check, Globe, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const steps = [
  { id: 1, title: "Your website", icon: Globe, desc: "Tell us about your site" },
  { id: 2, title: "Target keywords", icon: Search, desc: "What do you want to rank for?" },
  { id: 3, title: "First analysis", icon: Bot, desc: "Run your first AI audit" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const apiKey = useAppStore((s) => s.apiKey);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [projectId, setProjectId] = useState("");

  const [form, setForm] = useState({
    name: "",
    url: "",
    niche: "",
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
          target_niche: form.niche || null,
          goal_keywords: [],
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

  async function handleStep2(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const keywords = form.keywords.split(",").map(k => k.trim()).filter(Boolean);
      for (const kw of keywords.slice(0, 10)) {
        await fetch(`${API}/projects/${projectId}/keywords`, {
          method: "POST",
          headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
          body: JSON.stringify({ keyword: kw, target_region: "IN", locale: "en-US" }),
        });
      }
      setStep(3);
    } catch (err: any) {
      toast.error(err.message);
    } finally { setLoading(false); }
  }

  async function handleStep3() {
    setLoading(true);
    try {
      const firstKeyword = form.keywords.split(",")[0]?.trim() || "seo";
      await fetch(`${API}/jobs/research`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey, "Content-Type": "application/json" },
        body: JSON.stringify({
          research_request: {
            client_url: form.url,
            primary_keyword: firstKeyword,
            project_id: projectId,
            target_region: "IN",
          },
        }),
      });
      toast.success("Your first AI analysis is running!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message);
    } finally { setLoading(false); }
  }

  return (
    <div className="min-h-screen bg-surface-1 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-10">
          {steps.map((s) => (
            <div key={s.id} className="flex items-center gap-2">
              <div className={cn(
                "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all",
                step > s.id ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" :
                step === s.id ? "bg-brand-600 text-white pulse-glow" :
                "bg-zinc-800 text-zinc-500 border border-zinc-700"
              )}>
                {step > s.id ? <Check className="w-4 h-4" /> : s.id}
              </div>
              {s.id < 3 && <div className={cn("w-12 h-0.5 rounded", step > s.id ? "bg-emerald-500/30" : "bg-zinc-800")} />}
            </div>
          ))}
        </div>

        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold">{steps[step - 1].title}</h1>
          <p className="text-sm text-zinc-400 mt-1">{steps[step - 1].desc}</p>
        </div>

        {/* Step 1: Website */}
        {step === 1 && (
          <form onSubmit={handleStep1} className="card p-6 space-y-4 animate-fade-in">
            <div>
              <label className="label">Website URL</label>
              <input type="url" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} className="input-field" placeholder="https://yoursite.com" required autoFocus />
            </div>
            <div>
              <label className="label">Project Name (optional)</label>
              <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="input-field" placeholder="e.g. My Company Blog" />
            </div>
            <div>
              <label className="label">Industry / Niche (optional)</label>
              <input type="text" value={form.niche} onChange={e => setForm({ ...form, niche: e.target.value })} className="input-field" placeholder="e.g. SaaS, ecommerce, education" />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* Step 2: Keywords */}
        {step === 2 && (
          <form onSubmit={handleStep2} className="card p-6 space-y-4 animate-fade-in">
            <div>
              <label className="label">Target Keywords (comma-separated)</label>
              <textarea
                value={form.keywords}
                onChange={e => setForm({ ...form, keywords: e.target.value })}
                className="input-field h-32"
                placeholder="best crm software, project management tools, seo platform india"
                required
                autoFocus
              />
              <p className="text-xs text-zinc-500 mt-1.5">Add up to 10 keywords. You can always add more later.</p>
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(1)} className="btn-secondary flex-1">Back</button>
              <button type="submit" disabled={loading} className="btn-primary flex-1 flex items-center justify-center gap-2">
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}

        {/* Step 3: First Analysis */}
        {step === 3 && (
          <div className="card p-8 text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-6">
              <Bot className="w-8 h-8 text-brand-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Ready to run your first AI analysis</h3>
            <p className="text-sm text-zinc-400 mb-6">
              Claude will analyze your website against top competitors for "{form.keywords.split(",")[0]?.trim()}", score your SEO readiness, and generate actionable recommendations.
            </p>
            <div className="flex gap-3">
              <button onClick={() => router.push("/dashboard")} className="btn-secondary flex-1">Skip for now</button>
              <button onClick={handleStep3} disabled={loading} className="btn-primary flex-1 flex items-center justify-center gap-2">
                <Bot className="w-4 h-4" /> Run Analysis
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
