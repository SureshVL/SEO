"use client";

import { useState, useEffect } from "react";
import { Check, CreditCard, Loader2, TrendingUp, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { listProjects, listProjectKeywords, listJobs } from "@/lib/api";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    price: "₹1,999",
    priceNum: 1999,
    period: "/month",
    features: [
      "1 project",
      "50 keywords tracked",
      "5 AI reports/month",
      "Basic rank tracking",
      "PDF report export",
      "Email support",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    price: "₹4,999",
    priceNum: 4999,
    period: "/month",
    popular: true,
    features: [
      "5 projects",
      "300 keywords tracked",
      "Unlimited AI reports",
      "AI content writer",
      "GA4 + GSC integration",
      "Competitor monitoring",
      "Monthly trend reports",
      "Priority support",
    ],
  },
  {
    id: "agency",
    name: "Agency",
    price: "₹14,999",
    priceNum: 14999,
    period: "/month",
    features: [
      "25 projects",
      "2,000 keywords tracked",
      "White-label reports",
      "API access",
      "10 team seats",
      "Revenue attribution",
      "Custom integrations",
      "Dedicated support",
    ],
  },
];

const LIMITS: Record<string, { projects: number; keywords: number; reports: number }> = {
  starter: { projects: 1, keywords: 50, reports: 5 },
  growth: { projects: 5, keywords: 300, reports: 999 },
  agency: { projects: 25, keywords: 2000, reports: 999 },
};

export default function BillingPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [currentPlan] = useState("starter"); // comes from org in prod
  const [usage, setUsage] = useState({ projects: 0, keywords: 0, reports: 0 });
  const [loadingUsage, setLoadingUsage] = useState(true);

  useEffect(() => {
    async function fetchUsage() {
      try {
        const projects = await listProjects(apiKey);
        const jobs = await listJobs(apiKey);
        let totalKw = 0;
        for (const p of projects.slice(0, 3)) {
          try {
            const kws = await listProjectKeywords(p.id, apiKey);
            totalKw += kws.length;
          } catch {}
        }
        setUsage({
          projects: projects.length,
          keywords: totalKw,
          reports: jobs.filter(j => j.status === "completed").length,
        });
      } catch {}
      finally { setLoadingUsage(false); }
    }
    fetchUsage();
  }, [apiKey]);

  async function handleUpgrade(planId: string) {
    if (planId === currentPlan) return;
    setUpgrading(planId);
    try {
      const res = await fetch(
        `${API}/billing/subscribe?plan=${planId}&email=${encodeURIComponent(businessProfile?.websiteUrl || "user@example.com")}`,
        { method: "POST", headers: { "X-API-KEY": apiKey } },
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start checkout");
      }
      const data = await res.json();
      if (data.checkout_url) {
        window.open(data.checkout_url, "_blank");
        toast.success("Redirecting to Razorpay…");
      } else {
        toast.info("Subscription created. Complete payment in your Razorpay dashboard.");
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally { setUpgrading(null); }
  }

  const limits = LIMITS[currentPlan];

  function UsageBar({ used, limit, label }: { used: number; limit: number; label: string }) {
    const pct = limit >= 999 ? 10 : Math.min((used / limit) * 100, 100);
    const isNearLimit = pct > 80;
    return (
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-zinc-400">{label}</span>
          <span className={cn("font-medium", isNearLimit ? "text-amber-400" : "text-zinc-300")}>
            {used} / {limit >= 999 ? "∞" : limit}
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all", isNearLimit ? "bg-amber-500" : "bg-brand-500")}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Zap className="w-6 h-6 text-amber-400" /> Billing & Plans
        </h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your subscription. Prices in INR, billed monthly via Razorpay.</p>
      </div>

      {/* Current plan + usage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        <div className="card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-zinc-400" /> Current Plan
          </h3>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-bold font-serif text-brand-400 capitalize">{currentPlan}</span>
            <span className="text-zinc-500 text-sm">{PLANS.find(p => p.id === currentPlan)?.price}/month</span>
          </div>
          <p className="text-xs text-zinc-500 mb-4">Trial active · Renews automatically</p>
          <div className="text-xs text-zinc-600 bg-zinc-900/40 rounded-lg px-3 py-2">
            Billed via Razorpay · Cancel anytime
          </div>
        </div>

        <div className="card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-zinc-400" /> Usage This Month
          </h3>
          {loadingUsage ? (
            <div className="flex items-center gap-2 text-zinc-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading…
            </div>
          ) : (
            <div className="space-y-3">
              <UsageBar used={usage.projects} limit={limits.projects} label="Projects" />
              <UsageBar used={usage.keywords} limit={limits.keywords} label="Keywords tracked" />
              <UsageBar used={usage.reports} limit={limits.reports} label="AI reports" />
            </div>
          )}
        </div>
      </div>

      {/* Plan cards */}
      <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">Plans</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {PLANS.map(plan => {
          const isCurrent = plan.id === currentPlan;
          return (
            <div
              key={plan.id}
              className={cn(
                "card p-6 flex flex-col relative",
                plan.popular ? "border-brand-500/40 bg-brand-500/5" : "",
                isCurrent ? "border-emerald-500/30" : "",
              )}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full">
                  Most popular
                </div>
              )}
              {isCurrent && (
                <div className="absolute -top-3 right-4 bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full">
                  Current
                </div>
              )}

              <div className="mb-5">
                <h3 className="font-bold text-lg mb-1">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold font-serif">{plan.price}</span>
                  <span className="text-zinc-500 text-sm">{plan.period}</span>
                </div>
              </div>

              <ul className="space-y-2.5 flex-1 mb-6">
                {plan.features.map(f => (
                  <li key={f} className="flex items-center gap-2.5 text-sm text-zinc-300">
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleUpgrade(plan.id)}
                disabled={isCurrent || upgrading === plan.id}
                className={cn(
                  "w-full py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all",
                  isCurrent
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 cursor-default"
                    : plan.popular
                    ? "btn-primary"
                    : "btn-secondary",
                )}
              >
                {upgrading === plan.id ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing…</>
                ) : isCurrent ? (
                  <><Check className="w-3.5 h-3.5" /> Current plan</>
                ) : (
                  `Upgrade to ${plan.name}`
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Razorpay note */}
      <div className="mt-8 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/40 text-xs text-zinc-500 flex items-start gap-3">
        <CreditCard className="w-4 h-4 shrink-0 mt-0.5" />
        <div>
          <p>Payments processed securely via <strong className="text-zinc-400">Razorpay</strong>. All amounts in INR including GST.</p>
          <p className="mt-1">Configure Razorpay plan IDs in your backend <code className="text-brand-400">.env</code> — set <code className="text-brand-400">RAZORPAY_KEY_ID</code>, <code className="text-brand-400">RAZORPAY_KEY_SECRET</code>, and plan-specific <code className="text-brand-400">RAZORPAY_PLAN_ID_*</code> vars.</p>
        </div>
      </div>
    </div>
  );
}
