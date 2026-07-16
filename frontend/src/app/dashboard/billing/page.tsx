"use client";

import { useState, useEffect } from "react";
import { Check, CreditCard, Loader2, TrendingUp, Zap, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { apiFetch, listProjects, listProjectKeywords, listJobs } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Interval = "month" | "year";

type Plan = {
  id: string;
  name: string;
  priceMonthly: number;      // INR
  agents: number;
  serpPerDay: number;
  features: string[];
  popular?: boolean;
  cta?: string;
};

const PLANS: Plan[] = [
  {
    id: "free",
    name: "Free",
    priceMonthly: 0,
    agents: 2,
    serpPerDay: 25,
    features: [
      "1 project",
      "10 keywords tracked",
      "1 AI report / month",
      "Research + Keyword agents",
      "Community support",
    ],
    cta: "Start free",
  },
  {
    id: "starter",
    name: "Starter",
    priceMonthly: 1999,
    agents: 3,
    serpPerDay: 250,
    features: [
      "1 project",
      "50 keywords tracked",
      "5 AI reports / month",
      "Daily rank tracking",
      "PDF report export",
      "Email support",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    priceMonthly: 4999,
    agents: 6,
    serpPerDay: 1000,
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
    id: "pro",
    name: "Pro",
    priceMonthly: 9999,
    agents: 9,
    serpPerDay: 2500,
    features: [
      "12 projects",
      "800 keywords tracked",
      "Google AI Mode analysis",
      "Automated SEO audits",
      "Programmatic SEO engine",
      "CRO + ASO audits",
      "Priority pipeline",
      "Chat + email support",
    ],
  },
  {
    id: "agency",
    name: "Agency",
    priceMonthly: 19999,
    agents: 12,
    serpPerDay: 5000,
    features: [
      "25 projects",
      "2,000 keywords tracked",
      "White-label reports",
      "REST API access",
      "10 team seats",
      "Revenue attribution",
      "Custom integrations",
      "Dedicated success manager",
    ],
  },
];

const LIMITS: Record<string, { projects: number; keywords: number; reports: number }> = {
  free: { projects: 1, keywords: 10, reports: 1 },
  starter: { projects: 1, keywords: 50, reports: 5 },
  growth: { projects: 5, keywords: 300, reports: 999 },
  pro: { projects: 12, keywords: 800, reports: 999 },
  agency: { projects: 25, keywords: 2000, reports: 999 },
};

const ANNUAL_DISCOUNT = 0.20;

function inr(n: number) {
  return n === 0 ? "Free" : `₹${n.toLocaleString("en-IN")}`;
}

function priceForInterval(plan: Plan, interval: Interval): { display: string; note: string } {
  if (plan.priceMonthly === 0) return { display: "Free", note: "forever" };
  if (interval === "month") return { display: `${inr(plan.priceMonthly)}`, note: "/month" };
  const annual = Math.round(plan.priceMonthly * 12 * (1 - ANNUAL_DISCOUNT));
  const perMonth = Math.round(annual / 12);
  return { display: `${inr(perMonth)}`, note: `/mo · billed ${inr(annual)} yearly` };
}

export default function BillingPage() {
  const { apiKey, businessProfile } = useAppStore();
  const [interval, setInterval] = useState<Interval>("month");
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [currentPlan] = useState("free"); // TODO: fetch from org
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
    const email = encodeURIComponent(businessProfile?.websiteUrl || "user@example.com");
    try {
      let res = await apiFetch(
        `/billing/subscribe?plan=${planId}&email=${email}&interval=${interval}`,
        { method: "POST" },
      );
      let provider = "Razorpay";
      if (!res.ok) {
        res = await apiFetch(
          `/billing/stripe/checkout?plan=${planId}&email=${email}&interval=${interval}`,
          { method: "POST" },
        );
        provider = "Stripe";
      }
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start checkout");
      }
      const data = await res.json();
      if (planId === "free") {
        toast.success("Free plan activated. Enjoy!");
      } else if (data.checkout_url) {
        window.open(data.checkout_url, "_blank");
        toast.success(`Redirecting to ${provider}…`);
      } else {
        toast.info("Subscription created. Complete payment to activate.");
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally { setUpgrading(null); }
  }

  const limits = LIMITS[currentPlan] || LIMITS.free;

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
      <PageHeader
        title="Billing & Plans"
        subtitle="Choose a plan. Switch monthly or save 20% with annual billing."
        icon={Zap}
        accent="#FACC15"
      />

      {/* Current plan + usage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        <div className="card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-zinc-400" /> Current Plan
          </h3>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-3xl font-bold font-serif text-brand-400 capitalize">{currentPlan}</span>
            <span className="text-zinc-500 text-sm">
              {PLANS.find(p => p.id === currentPlan)
                ? priceForInterval(PLANS.find(p => p.id === currentPlan)!, "month").display + "/month"
                : ""}
            </span>
          </div>
          <p className="text-xs text-zinc-500 mb-4">Active</p>
          <div className="text-xs text-zinc-600 bg-zinc-900/40 rounded-lg px-3 py-2">
            Cancel anytime · Payments via Razorpay (IN) or Stripe (intl)
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

      {/* Interval toggle */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">Plans</h2>
        <div className="inline-flex items-center gap-1 rounded-full border border-zinc-800 bg-zinc-900/50 p-1 text-xs">
          <button
            onClick={() => setInterval("month")}
            className={cn(
              "px-3 py-1.5 rounded-full transition-colors",
              interval === "month" ? "bg-brand-600 text-white" : "text-zinc-400 hover:text-zinc-200",
            )}
          >
            Monthly
          </button>
          <button
            onClick={() => setInterval("year")}
            className={cn(
              "px-3 py-1.5 rounded-full transition-colors flex items-center gap-1.5",
              interval === "year" ? "bg-brand-600 text-white" : "text-zinc-400 hover:text-zinc-200",
            )}
          >
            Annual
            <span className={cn(
              "text-[10px] font-bold px-1.5 py-0.5 rounded",
              interval === "year" ? "bg-white/20 text-white" : "bg-emerald-500/20 text-emerald-400",
            )}>
              -20%
            </span>
          </button>
        </div>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {PLANS.map(plan => {
          const isCurrent = plan.id === currentPlan;
          const { display, note } = priceForInterval(plan, interval);
          return (
            <div
              key={plan.id}
              className={cn(
                "card p-5 flex flex-col relative",
                plan.popular ? "border-brand-500/40 bg-brand-500/5" : "",
                isCurrent ? "border-emerald-500/30" : "",
              )}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full whitespace-nowrap">
                  Most popular
                </div>
              )}
              {isCurrent && (
                <div className="absolute -top-3 right-3 bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full">
                  Current
                </div>
              )}

              <div className="mb-4">
                <h3 className="font-bold text-base mb-1">{plan.name}</h3>
                <div className="flex items-baseline gap-1 min-h-[36px]">
                  <span className="text-2xl font-bold font-serif">{display}</span>
                </div>
                <div className="text-[11px] text-zinc-500 min-h-[16px]">{note}</div>
              </div>

              <div className="flex items-center gap-3 mb-4 p-2.5 rounded-lg bg-zinc-900/50 border border-zinc-800/50">
                <Bot className="w-4 h-4 text-brand-400 shrink-0" />
                <div className="text-xs">
                  <div className="font-semibold text-zinc-200">{plan.agents} AI Agents</div>
                  <div className="text-zinc-500">{plan.serpPerDay.toLocaleString()} SERP checks/day</div>
                </div>
              </div>

              <ul className="space-y-2 flex-1 mb-5">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-2 text-xs text-zinc-300">
                    <Check className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleUpgrade(plan.id)}
                disabled={isCurrent || upgrading === plan.id}
                className={cn(
                  "w-full py-2 rounded-lg text-xs font-medium flex items-center justify-center gap-2 transition-all",
                  isCurrent
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 cursor-default"
                    : plan.popular
                    ? "btn-primary"
                    : "btn-secondary",
                )}
              >
                {upgrading === plan.id ? (
                  <><Loader2 className="w-3 h-3 animate-spin" /> Processing…</>
                ) : isCurrent ? (
                  <><Check className="w-3 h-3" /> Current</>
                ) : plan.id === "free" ? (
                  "Start free"
                ) : (
                  `Choose ${plan.name}`
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Payment rails note */}
      <div className="mt-8 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/40 text-xs text-zinc-500 flex items-start gap-3">
        <CreditCard className="w-4 h-4 shrink-0 mt-0.5" />
        <div>
          <p>India: <strong className="text-zinc-400">Razorpay</strong> (INR, incl. GST). International: <strong className="text-zinc-400">Stripe</strong> (USD).</p>
          <p className="mt-1">Annual billing saves 20% vs monthly. Cancel anytime — no lock-in.</p>
        </div>
      </div>
    </div>
  );
}
