"use client";

import Link from "next/link";
import { ArrowRight, ArrowLeft, TrendingUp, Calendar, Users, Target } from "lucide-react";

export default function CaseStudyPage() {
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
          <p className="text-sm text-indigo-600 font-semibold uppercase tracking-wider mb-4">
            SaaS Case Study
          </p>
          <h1 className="text-4xl font-bold text-slate-900 mb-4">
            SaaS Feature Clustering: From 47 to 207 Keywords Ranking
          </h1>
          <p className="text-lg text-slate-600 mb-8">
            How Acme CRM used intentional feature clustering to drive 340% keyword growth and establish market leadership.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200">
              <div className="text-xs text-indigo-600 uppercase tracking-wider font-semibold mb-1">Keywords Ranking</div>
              <div className="text-3xl font-bold text-slate-900">47 → 207</div>
              <div className="text-xs text-slate-600 mt-1">340% growth</div>
            </div>
            <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
              <div className="text-xs text-emerald-600 uppercase tracking-wider font-semibold mb-1">Timeline</div>
              <div className="text-3xl font-bold text-slate-900">6</div>
              <div className="text-xs text-slate-600 mt-1">months</div>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="text-xs text-blue-600 uppercase tracking-wider font-semibold mb-1">Organic Traffic</div>
              <div className="text-3xl font-bold text-slate-900">+186%</div>
              <div className="text-xs text-slate-600 mt-1">qualified visitors</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="text-xs text-purple-600 uppercase tracking-wider font-semibold mb-1">MQL Growth</div>
              <div className="text-3xl font-bold text-slate-900">+124%</div>
              <div className="text-xs text-slate-600 mt-1">monthly leads</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 mb-8">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Users className="w-4 h-4 text-indigo-600" />
              <span>Founded 2019 • San Francisco</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Target className="w-4 h-4 text-indigo-600" />
              <span>B2B SaaS • CRM Platform</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Calendar className="w-4 h-4 text-indigo-600" />
              <span>Started: January 2026</span>
            </div>
          </div>
        </div>

        <div className="prose prose-slate max-w-none">
          <h2>The Challenge</h2>
          <p>
            Acme CRM was a well-funded Series B startup competing against established players like HubSpot and Salesforce. Their product had powerful features, but their organic visibility was scattered. They ranked for "CRM software" (competitive, low conversion) but missed niche opportunities where buyer intent was clearer.
          </p>

          <p>
            The problem: they were creating content around features independently. 15 features meant 15 keyword clusters, each competing against each other. Worse, they couldn't see which keywords actually converted.
          </p>

          <h2>The OMNI-RANK Strategy</h2>
          <p>
            We started with competitive analysis and realized their competitors ranked for feature keywords scattered across multiple domains and page types. Acme was trying to own "CRM software" nationally when they should own "lightweight CRM for startups" regionally.
          </p>

          <h3>Phase 1: Buyer Persona Mapping (Weeks 1-2)</h3>
          <p>
            We identified 5 core buyer personas:
          </p>
          <ul>
            <li>Startup founders (technical, budget-conscious)</li>
            <li>SMB sales managers (non-technical, need training)</li>
            <li>Enterprise CTOs (compliance-focused, scalability priority)</li>
            <li>Implementation consultants (resellers, integration-focused)</li>
            <li>Freelancers (solo users, cost-sensitive)</li>
          </ul>

          <h3>Phase 2: Cluster Keyword Mapping (Weeks 3-4)</h3>
          <p>
            For each persona, we mapped feature needs to keywords:
          </p>
          <ul>
            <li><strong>Startup Founders</strong>: "Easy CRM setup", "CRM without training", "Affordable CRM startup", "CRM free tier"</li>
            <li><strong>SMB Sales Managers</strong>: "Sales pipeline CRM", "Deal tracking software", "Mobile sales CRM", "CRM reporting"</li>
            <li><strong>Enterprise CTOs</strong>: "Enterprise CRM API", "CRM security certifications", "Custom CRM workflow", "CRM scalability"</li>
            <li><strong>Implementation Partners</strong>: "CRM integration API", "CRM embedding tools", "CRM white label", "CRM partner program"</li>
            <li><strong>Freelancers</strong>: "CRM for solo users", "Free CRM lifetime", "Simple CRM lightweight", "CRM mobile only"</li>
          </ul>

          <h3>Phase 3: Pillar + Cluster Content Creation (Weeks 5-12)</h3>
          <p>
            We created 5 pillar pages (one per persona) and 3-4 cluster pages per pillar:
          </p>
          <ul>
            <li><strong>Pillar Page</strong>: "CRM for Startups" (internal linking to all cluster pages)</li>
            <li><strong>Cluster Pages</strong>: "Easy CRM Setup in 30 Minutes", "CRM Without Training", "Affordable CRM Under $50/mo", "Free CRM for Startups"</li>
          </ul>

          <p>
            Each cluster page had keyword-rich titles, FAQ schema for question-based keywords, and comparison sections.
          </p>

          <h3>Phase 4: Backlink Velocity & Authority Signaling (Weeks 8-20)</h3>
          <p>
            Simultaneously, we built topical authority through:
          </p>
          <ul>
            <li>Thought leadership content ("State of Startup Sales 2026 Report")</li>
            <li>Backlinks from startup-focused publications and directories</li>
            <li>Podcast appearances and expert positioning</li>
            <li>Internal linking strategy reinforcing persona clusters</li>
          </ul>

          <h2>The Results</h2>
          <p>
            Over 6 months:
          </p>
          <ul>
            <li><strong>Keywords ranking: 47 → 207 (+340%)</strong></li>
            <li>Keywords in top 3: 23 → 67 (+191%)</li>
            <li>Organic traffic: 2,400 monthly → 6,500 monthly (+186%)</li>
            <li>Qualified leads (MQL): 40 → 90 per month (+125%)</li>
            <li>Average lead quality (by sales): 58% increase</li>
            <li>Customer acquisition cost: -31% (better lead quality)</li>
          </ul>

          <h2>Why This Worked</h2>
          <p>
            The breakthrough wasn't creating more content. It was organizing content by actual buyer needs, not feature lists. By clustering keywords around personas, Acme:
          </p>
          <ol>
            <li><strong>Reduced competition</strong>: Niche persona keywords had 40-60% lower search volume but 8x higher conversion</li>
            <li><strong>Improved relevance</strong>: Each page matched one buyer's exact pain point</li>
            <li><strong>Built topical authority</strong>: Google recognized Acme's expertise in "startup CRM" specifically</li>
            <li><strong>Enabled measurement</strong>: Could finally see which features drove leads</li>
          </ol>

          <h2>Next Steps</h2>
          <p>
            Acme is now expanding this framework to:
          </p>
          <ul>
            <li>Geographic segmentation (startup CRM in NYC vs. San Francisco vs. Austin)</li>
            <li>Vertical expansion (startup CRM for SaaS founders, startup CRM for agencies, etc.)</li>
            <li>Competitor positioning (Acme vs. HubSpot, Acme vs. Pipedrive for startups)</li>
            <li>Integration-specific keywords (Acme + Stripe, Acme + Zapier, etc.)</li>
          </ul>

          <p>
            Their next goal: own "best CRM for [10 vertical + region combinations]" by month 12.
          </p>

          <h2>Key Takeaway</h2>
          <p>
            Feature-based keyword strategy is a trap. Persona-based clustering wins because it aligns content with buyer reality, not your feature list. The companies that win aren't the ones with the most features. They're the ones that own the keywords where their perfect customer is searching.
          </p>
        </div>

        <div className="mt-16 p-8 bg-indigo-50 border border-indigo-200 rounded-lg text-center">
          <h3 className="text-xl font-bold text-slate-900 mb-3">Want to replicate this for your SaaS?</h3>
          <p className="text-slate-600 mb-6">
            OMNI-RANK's competitive mapping and persona clustering tools make this strategy repeatable and measurable.
          </p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-indigo-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-indigo-700 transition">
            Start Your Cluster Strategy <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </article>
    </div>
  );
}
