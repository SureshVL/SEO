"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, BarChart3, Bot, Globe, Search, Shield, Zap } from "lucide-react";

const features = [
  { icon: Bot, title: "AI Research Engine", desc: "Claude & Gemini analyze competitors, decode intent, and generate strategy — like having a senior SEO on call 24/7." },
  { icon: Search, title: "Keyword Intelligence", desc: "Real search volume, CPC, difficulty via DataForSEO. AI clusters keywords by intent and maps content plans." },
  { icon: BarChart3, title: "Daily Rank Tracking", desc: "Position monitoring with SERP feature detection. Know when competitors move before they do." },
  { icon: Globe, title: "Backlink Intelligence", desc: "Full backlink profiles, referring domains, anchor analysis. Find link opportunities your competitors missed." },
  { icon: Shield, title: "Technical Audits", desc: "PageSpeed, Core Web Vitals, schema validation, crawl errors. AI prioritizes what actually moves rankings." },
  { icon: Zap, title: "Content Studio", desc: "AI writes SEO content with entity coverage, FAQ blocks, and E-E-A-T signals — calibrated against real SERP data." },
];

type LandingPlan = {
  name: string;
  priceMonthly: number;
  agents: number;
  serpPerDay: number;
  features: string[];
  cta: string;
  popular?: boolean;
};

const plans: LandingPlan[] = [
  { name: "Free", priceMonthly: 0, agents: 2, serpPerDay: 25,
    features: ["1 project", "10 keywords", "1 AI report/mo", "Research + Keyword agents"], cta: "Start free" },
  { name: "Starter", priceMonthly: 1999, agents: 3, serpPerDay: 250,
    features: ["1 project", "50 keywords", "5 AI reports/mo", "Daily rank tracking"], cta: "Start free trial" },
  { name: "Growth", priceMonthly: 4999, agents: 6, serpPerDay: 1000,
    features: ["5 projects", "300 keywords", "Unlimited reports", "Content studio", "Competitor alerts"], cta: "Start free trial", popular: true },
  { name: "Pro", priceMonthly: 9999, agents: 9, serpPerDay: 2500,
    features: ["12 projects", "800 keywords", "Google AI Mode", "Automated audits", "Programmatic SEO"], cta: "Start free trial" },
  { name: "Agency", priceMonthly: 19999, agents: 12, serpPerDay: 5000,
    features: ["25 projects", "2,000 keywords", "White-label", "API access", "10 team seats"], cta: "Contact sales" },
];

const ANNUAL_DISCOUNT = 0.20;

function priceLabel(plan: LandingPlan, interval: "month" | "year"): { display: string; note: string } {
  if (plan.priceMonthly === 0) return { display: "Free", note: "forever" };
  if (interval === "month") return { display: `\u20B9${plan.priceMonthly.toLocaleString("en-IN")}`, note: "/mo" };
  const perMonth = Math.round(plan.priceMonthly * (1 - ANNUAL_DISCOUNT));
  return { display: `\u20B9${perMonth.toLocaleString("en-IN")}`, note: "/mo, billed yearly" };
}

export default function LandingPage() {
  const [interval, setInterval] = useState<"month" | "year">("month");
  return (
    <div className="min-h-screen grain" style={{ background: "#110f0d" }}>
      {/* Nav */}
      <nav style={{ borderBottom: "1px solid rgba(200, 180, 150, 0.06)", background: "rgba(17, 15, 13, 0.9)", backdropFilter: "blur(12px)" }} className="sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-serif font-bold text-sm" style={{ background: "linear-gradient(135deg, #8B5CF6, #EC4899)", color: "#ffffff" }}>OR</div>
            <span className="font-serif text-lg" style={{ color: "#e8e0d4" }}>Omni-Rank</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-sans" style={{ color: "rgba(200, 180, 150, 0.5)" }}>
            <a href="#features" className="hover:text-amber-200 transition-colors">Features</a>
            <a href="#pricing" className="hover:text-amber-200 transition-colors">Pricing</a>
            <Link href="/compare" className="hover:text-amber-200 transition-colors">Compare</Link>
            <Link href="/tools" className="hover:text-amber-200 transition-colors">Free Tools</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="btn-ghost text-sm">Log in</Link>
            <Link href="/auth/signup" className="btn-primary text-sm flex items-center gap-1.5">
              Get started <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero — editorial, asymmetric */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 30% 20%, rgba(200, 121, 65, 0.06), transparent 60%)" }} />
        <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 80% 80%, rgba(107, 143, 113, 0.04), transparent 50%)" }} />
        <div className="max-w-5xl mx-auto px-6 pt-28 pb-24 relative">
          <div className="max-w-3xl">
            <p className="font-sans text-xs uppercase tracking-[0.2em] mb-6" style={{ color: "var(--copper)" }}>AI-Powered SEO Intelligence Platform</p>
            <h1 className="font-serif text-6xl md:text-7xl leading-[1.05] mb-8" style={{ color: "#e8e0d4" }}>
              The SEO analyst<br />
              <span className="italic" style={{ color: "var(--copper-light)" }}>that never sleeps</span>
            </h1>
            <p className="text-lg font-sans leading-relaxed mb-12 max-w-xl" style={{ color: "rgba(200, 180, 150, 0.55)" }}>
              Omni-Rank combines DataForSEO&apos;s data depth with AI reasoning to analyze competitors, 
              generate content, track rankings, and execute technical fixes — autonomously.
            </p>
            <div className="flex items-center gap-4">
              <Link href="/audit" className="btn-primary text-base px-8 py-3.5 flex items-center gap-2">
                Free instant SEO audit <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/auth/signup" className="btn-secondary text-base px-6 py-3.5">Start free trial</Link>
            </div>
            <p className="text-xs font-sans mt-5" style={{ color: "rgba(200, 180, 150, 0.25)" }}>No credit card required &middot; Cancel anytime</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-28">
        <p className="font-sans text-xs uppercase tracking-[0.2em] mb-4" style={{ color: "var(--copper)" }}>Capabilities</p>
        <h2 className="font-serif text-4xl mb-4" style={{ color: "#e8e0d4" }}>Six agents. One mission.</h2>
        <p className="font-sans mb-16 max-w-lg" style={{ color: "rgba(200, 180, 150, 0.45)" }}>
          Each agent specializes in one dimension of SEO, working together like a senior strategy team.
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px" style={{ background: "rgba(200, 180, 150, 0.06)" }}>
          {features.map((f) => (
            <div key={f.title} className="p-8 group transition-all duration-300" style={{ background: "#110f0d" }}>
              <f.icon className="w-5 h-5 mb-5" style={{ color: "var(--copper)" }} />
              <h3 className="font-serif text-xl mb-3" style={{ color: "#e8e0d4" }}>{f.title}</h3>
              <p className="text-sm font-sans leading-relaxed" style={{ color: "rgba(200, 180, 150, 0.45)" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-6xl mx-auto px-6 py-28">
        <p className="font-sans text-xs uppercase tracking-[0.2em] mb-4 text-center" style={{ color: "var(--copper)" }}>Pricing</p>
        <h2 className="font-serif text-4xl text-center mb-4" style={{ color: "#e8e0d4" }}>Transparent. Simple.</h2>
        <p className="font-sans text-center mb-8" style={{ color: "rgba(200, 180, 150, 0.45)" }}>Start free, scale as you grow. Save 20% with annual billing.</p>

        <div className="flex justify-center mb-12">
          <div className="inline-flex items-center gap-1 rounded-full p-1 text-xs font-sans" style={{ background: "rgba(200, 180, 150, 0.06)", border: "1px solid rgba(200, 180, 150, 0.1)" }}>
            <button
              onClick={() => setInterval("month")}
              className="px-4 py-1.5 rounded-full transition-colors"
              style={interval === "month"
                ? { background: "var(--copper)", color: "#110f0d", fontWeight: 600 }
                : { color: "rgba(200, 180, 150, 0.5)" }}
            >
              Monthly
            </button>
            <button
              onClick={() => setInterval("year")}
              className="px-4 py-1.5 rounded-full transition-colors flex items-center gap-1.5"
              style={interval === "year"
                ? { background: "var(--copper)", color: "#110f0d", fontWeight: 600 }
                : { color: "rgba(200, 180, 150, 0.5)" }}
            >
              Annual
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: "rgba(107, 143, 113, 0.25)", color: "var(--sage)" }}>-20%</span>
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
          {plans.map((plan) => {
            const { display, note } = priceLabel(plan, interval);
            return (
              <div
                key={plan.name}
                className="card p-5 relative flex flex-col"
                style={plan.popular ? { borderColor: "rgba(200, 121, 65, 0.3)" } : {}}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] px-3 py-0.5 rounded-full font-sans font-medium whitespace-nowrap" style={{ background: "rgba(200, 121, 65, 0.15)", color: "var(--copper-light)", border: "1px solid rgba(200, 121, 65, 0.2)" }}>
                    Most popular
                  </div>
                )}
                <h3 className="font-serif text-xl mb-1" style={{ color: "#e8e0d4" }}>{plan.name}</h3>
                <div className="flex items-baseline gap-1 min-h-[36px]">
                  <span className="font-serif text-2xl" style={{ color: plan.popular ? "var(--copper-light)" : "#e8e0d4" }}>{display}</span>
                </div>
                <div className="text-[11px] font-sans mb-4 min-h-[16px]" style={{ color: "rgba(200, 180, 150, 0.35)" }}>{note}</div>

                <div className="mb-4 p-2.5 rounded-lg flex items-center gap-2" style={{ background: "rgba(200, 180, 150, 0.04)", border: "1px solid rgba(200, 180, 150, 0.06)" }}>
                  <Bot className="w-3.5 h-3.5" style={{ color: "var(--copper)" }} />
                  <div className="text-[11px] font-sans leading-tight">
                    <div style={{ color: "#e8e0d4", fontWeight: 600 }}>{plan.agents} AI Agents</div>
                    <div style={{ color: "rgba(200, 180, 150, 0.45)" }}>{plan.serpPerDay.toLocaleString()} SERP/day</div>
                  </div>
                </div>

                <ul className="space-y-2 flex-1 mb-5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs font-sans" style={{ color: "rgba(200, 180, 150, 0.6)" }}>
                      <span style={{ color: "var(--sage)" }}>&#10003;</span> <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <Link href="/auth/signup" className={plan.popular ? "btn-primary w-full text-center block text-xs py-2" : "btn-secondary w-full text-center block text-xs py-2"}>
                  {plan.cta}
                </Link>
              </div>
            );
          })}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="max-w-4xl mx-auto px-6 py-28">
        <p className="font-sans text-xs uppercase tracking-[0.2em] mb-4 text-center" style={{ color: "var(--copper)" }}>FAQ</p>
        <h2 className="font-serif text-4xl text-center mb-16" style={{ color: "#e8e0d4" }}>Frequently asked questions</h2>
        <div className="space-y-3">
          <FaqItem
            q="What's the difference between AI Agents and SERP/day limit?"
            a="AI Agents are specialized bots: Research, Keyword Strategy, Competitor Analysis, Content Writer, Technical Auditor, and Ranking Agent. SERP/day is how many times per day you can check search rankings. Both scale with your tier."
          />
          <FaqItem
            q="Can I upgrade mid-month?"
            a="Yes. Upgrades are prorated. If you're on Starter (₹1,999) and upgrade to Growth (₹4,999) on day 15, you'll pay the difference for the remaining days, then renew at the Growth price next month."
          />
          <FaqItem
            q="Do you offer annual discounts?"
            a="Yes, 20% off all paid tiers when you commit to annual billing. Growth goes from ₹4,999/mo to ₹3,999/mo when billed yearly."
          />
          <FaqItem
            q="Is there a free trial?"
            a="Yes. All paid plans include a 14-day free trial. Free tier users get 25 SERP checks/day forever, no trial needed."
          />
          <FaqItem
            q="What if I hit my SERP/day limit?"
            a="Your SERP quota resets daily at midnight IST. You can track up to your tier's limit each day. To do more, upgrade to the next tier."
          />
          <FaqItem
            q="Can I use Omni-Rank for multiple websites?"
            a="Yes, depending on your tier. Free: 1 project, Starter: 1, Growth: 5, Pro: 12, Agency: 25 projects. Each project tracks its own keywords, competitors, and audits."
          />
          <FaqItem
            q="Do you have an API?"
            a="Yes, available on Growth tier and above. Use our REST API to build custom integrations with your CRM, dashboard, or internal tools."
          />
          <FaqItem
            q="Is there a white-label option?"
            a="Yes, on Growth tier and above. Rebrand reports, dashboards, and emails with your company colors and logo."
          />
          <FaqItem
            q="How often is ranking data updated?"
            a="Daily (or up to your SERP/day budget). We check rankings overnight IST and display results by morning. Set frequency per keyword."
          />
          <FaqItem
            q="Do I need Google Search Console or GA4 to start?"
            a="No. Omni-Rank works standalone. But connecting GSC and GA4 unlocks query insights and click data, making strategy more accurate."
          />
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid rgba(200, 180, 150, 0.06)" }} className="py-12">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded flex items-center justify-center font-serif font-bold text-xs" style={{ background: "var(--copper-dark)", color: "#faf8f5" }}>OR</div>
            <span className="text-sm font-sans" style={{ color: "rgba(200, 180, 150, 0.3)" }}>Omni-Rank &copy; 2026</span>
          </div>
          <div className="flex items-center gap-6 text-xs font-sans" style={{ color: "rgba(200, 180, 150, 0.2)" }}>
            <a href="#" className="hover:text-amber-200 transition-colors">Privacy</a>
            <a href="#" className="hover:text-amber-200 transition-colors">Terms</a>
            <a href="#" className="hover:text-amber-200 transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className="w-full text-left p-4 rounded-lg border transition"
      style={{
        borderColor: open ? "rgba(200, 121, 65, 0.3)" : "rgba(200, 180, 150, 0.06)",
        background: open ? "rgba(200, 121, 65, 0.05)" : "rgba(200, 180, 150, 0.02)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold" style={{ color: "#e8e0d4" }}>{q}</h3>
        <span style={{ color: "var(--copper)", marginTop: "2px" }}>
          {open ? "−" : "+"}
        </span>
      </div>
      {open && (
        <p className="mt-3 text-sm" style={{ color: "rgba(200, 180, 150, 0.65)" }}>
          {a}
        </p>
      )}
    </button>
  );
}
