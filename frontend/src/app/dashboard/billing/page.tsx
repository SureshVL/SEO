"use client";

import { useState } from "react";
import { Check, CreditCard, Loader2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { toast } from "sonner";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const plans = [
  { id: "starter", name: "Starter", price: "₹1,999", priceNum: 1999, features: ["1 project", "50 keywords", "5 AI reports/mo", "Basic rank tracking", "Email support"], current: false },
  { id: "growth", name: "Growth", price: "₹4,999", priceNum: 4999, features: ["5 projects", "300 keywords", "Unlimited AI reports", "AI content writer", "GSC integration", "Competitor monitoring", "Priority support"], popular: true },
  { id: "agency", name: "Agency", price: "₹14,999", priceNum: 14999, features: ["25 projects", "2,000 keywords", "White-label reports", "API access", "Team seats (10)", "Dedicated support", "Custom integrations"] },
];

export default function BillingPage() {
  const apiKey = useAppStore((s) => s.apiKey);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [currentPlan] = useState("starter"); // would come from org data

  async function handleUpgrade(planId: string) {
    setUpgrading(planId);
    try {
      const res = await fetch(`${API}/billing/subscribe?plan=${planId}&email=user@example.com`, {
        method: "POST",
        headers: { "X-API-KEY": apiKey },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start checkout");
      }
      const data = await res.json();
      if (data.checkout_url) {
        window.open(data.checkout_url, "_blank");
        toast.success("Redirecting to Razorpay checkout...");
      } else {
        toast.info("Subscription created. Complete payment in Razorpay dashboard.");
      }
    } catch (err: any) {
      toast.error(err.message);
    } finally { setUpgrading(null); }
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Zap className="w-6 h-6 text-amber-400" /> Billing & Plans</h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your subscription and usage.</p>
      </div>

      {/* Current Usage */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="metric-card">
          <div className="metric-label">Current Plan</div>
          <div className="metric-value text-brand-400">Starter</div>
          <div className="text-xs text-zinc-500 mt-1">Trial active</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">AI Reports Used</div>
          <div className="metric-value text-zinc-200">0 / 5</div>
          <div className="w-full bg-zinc-800 rounded-full h-1.5 mt-2"><div className="bg-brand-500 h-1.5 rounded-full" style={{ width: "0%" }} /></div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Keywords Used</div>
          <div className="metric-value text-zinc-200">0 / 50</div>
          <div className="w-full bg-zinc-800 rounded-full h-1.5 mt-2"><div className="bg-teal-500 h-1.5 rounded-full" style={{ width: "0%" }} /></div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Credits</div>
          <div className="metric-value text-emerald-400">10</div>
          <div className="text-xs text-zinc-500 mt-1">Free signup credits</div>
        </div>
      </div>

      {/* Plans */}
      <h2 className="text-lg font-semibold mb-4">Available Plans</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
        {plans.map((plan) => {
          const isCurrent = currentPlan === plan.id;
          return (
            <div key={plan.id} className={cn("card p-6 relative", plan.popular && "border-brand-500/50 ring-1 ring-brand-500/20")}>
              {plan.popular && <div className="absolute -top-3 left-1/2 -translate-x-1/2 badge-info text-xs px-3">Recommended</div>}
              <h3 className="font-semibold text-lg">{plan.name}</h3>
              <div className="flex items-baseline gap-1 mt-2 mb-6">
                <span className="text-3xl font-bold">{plan.price}</span>
                <span className="text-zinc-500 text-sm">/mo</span>
              </div>
              <ul className="space-y-2.5 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-zinc-300">
                    <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" /> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => !isCurrent && handleUpgrade(plan.id)}
                disabled={isCurrent || upgrading === plan.id}
                className={cn("w-full text-center py-2.5 rounded-lg font-medium text-sm",
                  isCurrent ? "bg-zinc-800 text-zinc-400 cursor-default" :
                  plan.popular ? "btn-primary" : "btn-secondary"
                )}
              >
                {isCurrent ? "Current plan" : upgrading === plan.id ? (
                  <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Processing...</span>
                ) : "Upgrade"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Payment History */}
      <h2 className="text-lg font-semibold mb-4">Payment History</h2>
      <div className="card p-8 text-center">
        <CreditCard className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
        <p className="text-sm text-zinc-400">No payments yet. Your payment history will appear here after your first transaction.</p>
      </div>
    </div>
  );
}
