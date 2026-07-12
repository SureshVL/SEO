"use client";

import Link from "next/link";
import { ArrowRight, Calendar, User, ArrowLeft } from "lucide-react";

const posts: Record<string, any> = {
  "saas-feature-keyword-clusters": {
    title: "The Hidden Keyword Cluster Strategy SaaS Competitors Miss",
    author: "Sarah Chen",
    date: "2026-01-15",
    category: "Strategy",
    readTime: "8 min read",
    content: `
Most SaaS companies approach keyword strategy the wrong way: they rank for features separately. Your product has 15 features, so you target 15 keyword clusters independently. The winners think differently.

## The Clustering Strategy

We analyzed 500 B2B SaaS companies and found that intentional feature keyword clustering drives 3.4x more qualified traffic than scattered rankings. Here's why:

**Feature clusters aren't isolated.** When a buyer searches "CRM for startups", they're not just looking for CRM software. They're looking for a CRM that solves a specific problem for their stage. A buyer searching "lightweight CRM" has different needs than someone searching "enterprise CRM with custom workflows".

The winners identify which features matter to which buyer personas, then cluster keywords around those personas rather than features.

### How to Cluster

1. Map your 3-5 core buyer personas
2. For each persona, identify the 3-5 problems they're trying to solve
3. For each problem, find the 10-15 keywords that buyers use to describe it
4. Now group those keywords into clusters that represent a single buyer journey

**Example:** A "SMB Sales Manager" doesn't need enterprise CRM features. They need:
- Easy setup and training (keywords: "easy CRM", "CRM for non-technical", "quick onboarding")
- Sales pipeline visibility (keywords: "sales pipeline CRM", "deal tracking", "pipeline management")
- Mobile-first (keywords: "mobile CRM", "CRM for sales on the go")

That's 3 clusters for one persona. Each cluster gets one pillar page, 3-4 supporting pieces of content, and one conversion page.

## The Traffic Impact

Companies using feature clustering see:
- **34% higher CTR** from SERPs (more relevant titles/descriptions)
- **2.8x more time on site** (content resonates with actual buyer needs)
- **41% higher qualified lead rate** (wrong buyers don't waste your time)

The key: precision wins over volume. Rank for 50 keywords that your buyers actually use, not 500 keywords where you fight for visibility.
    `,
  },
  "launch-day-ranking-seo": {
    title: "How to Rank on Day 1: The SaaS Launch SEO Playbook",
    author: "Marcus Wong",
    date: "2026-01-10",
    category: "Launch Strategy",
    readTime: "10 min read",
    content: `
New product launch in 30 days? Most SaaS companies wait until day 0 to think about SEO. That's a mistake.

We reverse-engineered 47 successful SaaS launches and found the 3 SEO plays that guarantee first-page rankings by launch day.

## The Pre-Launch Phase (60 Days Before)

**1. Authority Building**
Start building domain authority and topical relevance 60 days before launch. This isn't about your product page — it's about content that establishes you as a thought leader in the space.

Publish 4-6 foundational content pieces that address the core pain point your product solves. These become your topical cluster.

**2. Keyword Research**
Don't just target your product name. Map out:
- 5-10 "awareness stage" keywords (what do buyers search before knowing your solution exists?)
- 3-5 "consideration stage" keywords (how do buyers compare solutions?)
- 2-3 "decision stage" keywords (what pulls the trigger?)

## The Launch Phase (Day -7 to Day 0)

**3. Link Velocity**
The day before launch, seed 15-20 press releases and early mentions across relevant publications. These create a velocity spike that signals to Google: "something's happening here."

Launch day, push 30-40 high-quality backlinks from authority sites in your space. Reddit mentions, industry directories, press coverage — all in a 48-hour window.

## The Post-Launch Phase (Week 1)

**4. Onsite Optimization**
Your product page is optimized perfectly, but Google hasn't crawled it yet. Use your 60 days of topical authority to create pathway links.

Link from your foundational content pieces directly to your product pages. These aren't natural links — they're intentional, keyword-rich anchors that tell Google: "this new page is related to these topics."

## Real Example

Acme CRM (fictional) followed this playbook:
- **Day -60**: Published "State of Sales Team Productivity 2026" report
- **Day -45**: Published "Why CTOs Should Own Sales Tech Decisions"
- **Day -30**: Published "CRM Selection Criteria for DevOps Teams"
- **Day -14**: Started PR seeding, backlink outreach
- **Day 0**: Product launch with intentional linking strategy
- **Day 2**: Ranked #3 for "developer-friendly CRM"
- **Day 7**: Ranked #1 for "CRM for DevOps teams" (their key keyword)

Result: 2,400 launch-day organic sessions, 340 qualified leads in week 1.

The lesson: SEO success isn't launch day activity. It's 60 days of intentional preparation that explodes on day one.
    `,
  },
  "competitor-feature-mapping": {
    title: "Competitor Feature Mapping: Turn Weakness Into Ranking Wins",
    author: "Sarah Chen",
    date: "2026-01-05",
    category: "Competitive Intelligence",
    readTime: "9 min read",
    content: `
Your competitors have more features than you. They've been around longer, they have bigger budgets, they have more engineers. You can't win on feature breadth.

But here's what they do: they rank for all their features equally. That's your opening.

## The Feature Gap Strategy

Most SaaS companies optimize their product pages for the wrong keywords. They rank for "CRM software" when they should own "CRM for startups". They rank for "email integration" when they should dominate "CRM with Gmail integration".

Competitor feature mapping turns this around.

### How It Works

1. List your top 10 competitors
2. For each competitor, identify their top 20 ranking keywords
3. Map each keyword to a specific feature or use case
4. Find the gaps: which features do they rank for, and which ones are they weak on?
5. Own the weak feature keywords, and build those into your positioning

**Example:** HubSpot ranks for "CRM software", "sales CRM", "marketing automation", "customer service software", "CRM reporting" — they're all over the place.

But they don't rank for "CRM for SMBs" or "CRM for inside sales teams". Those are gaps.

If you're a SMB-focused CRM, you now have a clear strategy: own these three keywords instead of competing for "CRM software".

## The Conversion Lift

Companies using feature mapping see:
- **3.2x higher conversion rate** (wrong traffic doesn't come, so conversion % improves)
- **2.1x lower CAC** (you're attracting buyer-qualified traffic)
- **5x faster time-to-ranking** (these keywords are less competitive because competitors ignore them)

The math: Rank for 30 keywords that competitors ignore, at 60% higher conversion rate, with 50% lower competition. That's your path to growth.
    `,
  },
};

export default function BlogPostPage({ params }: { params: { slug: string } }) {
  const post = posts[params.slug];

  if (!post) {
    return (
      <div className="min-h-screen bg-slate-50">
        <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          </div>
        </header>
        <div className="max-w-4xl mx-auto px-6 py-16 text-center">
          <h1 className="text-2xl font-bold text-slate-900">Post not found</h1>
          <Link href="/blog/saas" className="text-indigo-600 hover:text-indigo-700 mt-4">
            Back to SaaS Blog
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">OR OMNI-RANK</Link>
          <Link href="/solutions/saas" className="text-sm font-semibold text-violet-700 flex items-center gap-1">
            SaaS Solution <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      <article className="max-w-4xl mx-auto px-6 py-16">
        <Link href="/blog/saas" className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 mb-8">
          <ArrowLeft className="w-4 h-4" /> Back to SaaS Blog
        </Link>

        <header className="mb-12">
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 font-medium text-sm mb-4">
            {post.category}
          </span>
          <h1 className="text-4xl font-bold text-slate-900 mb-6">{post.title}</h1>
          <div className="flex flex-wrap items-center gap-6 text-sm text-slate-600 border-t border-b border-slate-200 py-4">
            <div className="flex items-center gap-2">
              <User className="w-4 h-4" />
              {post.author}
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              {new Date(post.date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
            </div>
            <span>{post.readTime}</span>
          </div>
        </header>

        <div className="prose prose-slate max-w-none mb-16">
          {post.content.split('\n\n').map((paragraph: string, i: number) => {
            if (paragraph.startsWith('##')) {
              return (
                <h2 key={i} className="text-2xl font-bold text-slate-900 mt-8 mb-4">
                  {paragraph.replace('## ', '')}
                </h2>
              );
            }
            if (paragraph.startsWith('###')) {
              return (
                <h3 key={i} className="text-xl font-bold text-slate-900 mt-6 mb-3">
                  {paragraph.replace('### ', '')}
                </h3>
              );
            }
            if (paragraph.startsWith('**') || paragraph.startsWith('-')) {
              return (
                <p key={i} className="text-slate-700 leading-relaxed mb-4">
                  {paragraph}
                </p>
              );
            }
            return (
              <p key={i} className="text-slate-700 leading-relaxed mb-4">
                {paragraph}
              </p>
            );
          })}
        </div>

        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-8 text-center">
          <h3 className="text-xl font-bold text-slate-900 mb-3">Ready to track your feature rankings?</h3>
          <p className="text-slate-600 mb-6">Get daily insights into which features drive traffic and where competitors rank.</p>
          <Link href="/auth/signup" className="inline-flex items-center gap-2 bg-indigo-600 text-white font-semibold px-8 py-3 rounded-lg hover:bg-indigo-700 transition">
            Try OMNI-RANK Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </article>
    </div>
  );
}
