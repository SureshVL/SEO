import Link from "next/link";

export const metadata = { title: "Privacy Policy — OMNI-RANK" };

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center">
          <Link href="/" className="font-bold text-lg">OR OMNI-RANK</Link>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-16 prose prose-slate">
        <h1>Privacy Policy</h1>
        <p className="text-sm text-slate-500">Last updated: July 2026</p>

        <h2>What we collect</h2>
        <ul>
          <li><strong>Account data</strong> — name, email address, and password hash when you create an account.</li>
          <li><strong>Email subscriptions</strong> — your email address and industry vertical when you subscribe to research reports or request a guide.</li>
          <li><strong>Project data</strong> — website URLs, keywords, and analytics you connect to run SEO and AI-visibility analysis.</li>
          <li><strong>Usage data</strong> — pages visited and features used, to improve the product.</li>
        </ul>

        <h2>How we use it</h2>
        <ul>
          <li>To provide the OMNI-RANK platform: rankings, audits, reports, and AI visibility tracking.</li>
          <li>To send you the emails you asked for: research reports, guides, and product updates. Every email includes a one-click unsubscribe link.</li>
          <li>We do <strong>not</strong> sell your personal data to third parties.</li>
        </ul>

        <h2>Third-party processors</h2>
        <p>
          We use trusted processors to run the service: Supabase (database and authentication),
          payment providers (Stripe / Razorpay) for billing, an email delivery provider for
          the emails you subscribe to, and AI providers to generate analysis. Each receives
          only the data required for its function.
        </p>

        <h2>Data retention &amp; your rights</h2>
        <p>
          You can unsubscribe from emails at any time via the link in any email. You can request
          a copy or deletion of your personal data by contacting us — we respond within 30 days.
        </p>

        <h2>Contact</h2>
        <p>
          Questions about this policy: <a href="mailto:privacy@omni-rank.com">privacy@omni-rank.com</a>
        </p>

        <p className="text-sm text-slate-500">
          See also our <Link href="/terms">Terms of Service</Link>.
        </p>
      </main>
    </div>
  );
}
