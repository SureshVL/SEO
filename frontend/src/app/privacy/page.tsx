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

        <p>
          OMNI-RANK (&quot;the Service&quot;) is a product of <strong>Surrvik E-Mobility</strong>
          (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;). This policy explains what personal data we
          collect when you use omni-rank.com and the OMNI-RANK platform, why we collect it, and
          the choices you have. By using the Service you agree to this policy.
        </p>

        <h2>1. Data we collect</h2>
        <ul>
          <li><strong>Account data</strong> — your name, email address, and hashed password (or your identity from a sign-in provider) when you create an account.</li>
          <li><strong>Subscription and lead data</strong> — your email address and industry vertical when you subscribe to our research reports, request a guide, or use a free tool.</li>
          <li><strong>Project data</strong> — website URLs, keywords, competitor domains, content, and analytics connections (e.g. Google Analytics, Search Console) that you add in order to run SEO and AI-visibility analysis.</li>
          <li><strong>Billing data</strong> — your plan, billing history, and payment status. Card and payment details are collected and stored by our payment processors (Stripe / Razorpay), not by us.</li>
          <li><strong>Usage and device data</strong> — pages visited, features used, browser type, and approximate location derived from IP, used for security and to improve the product.</li>
        </ul>

        <h2>2. How we use your data</h2>
        <ul>
          <li>To operate the Service: run analyses, track rankings, generate reports, and show them to you.</li>
          <li>To send the emails you asked for — research reports, guides, and product updates. Every marketing email contains a one-click unsubscribe link, and we honour unsubscribes immediately.</li>
          <li>To process payments, prevent abuse, and comply with legal obligations.</li>
          <li>To improve the product using aggregated, de-identified usage patterns.</li>
        </ul>
        <p>We do <strong>not</strong> sell your personal data, and we do not share it with third parties for their own marketing.</p>

        <h2>3. Third-party processors</h2>
        <p>We rely on a small set of processors, each receiving only what its function requires:</p>
        <ul>
          <li><strong>Supabase</strong> — database, authentication, and file storage.</li>
          <li><strong>Stripe and Razorpay</strong> — payment processing and subscription billing.</li>
          <li><strong>Email delivery provider</strong> — sending transactional and subscription emails.</li>
          <li><strong>AI providers</strong> (e.g. Google Gemini, Anthropic) — generating analyses and content from the inputs you provide. We do not send them your account credentials or payment data.</li>
          <li><strong>SEO data providers</strong> (e.g. search results and crawling APIs) — fetching public web and ranking data about the domains and keywords you track.</li>
        </ul>

        <h2>4. Cookies</h2>
        <p>
          We use essential cookies to keep you signed in and to secure the Service. We do not use
          third-party advertising cookies.
        </p>

        <h2>5. Data retention</h2>
        <p>
          Account and project data are retained while your account is active and deleted or
          anonymised within 90 days of account deletion, except where law requires longer
          retention (e.g. tax records for billing). Email subscribers who unsubscribe are kept on
          a suppression list solely to make sure we do not email them again.
        </p>

        <h2>6. Your rights</h2>
        <p>
          Subject to applicable law — including India&apos;s Digital Personal Data Protection Act
          and, where it applies, the GDPR — you may request access to, correction of, or deletion
          of your personal data, withdraw consent, or object to processing. Write to us at the
          address below; we respond within 30 days. You can unsubscribe from any marketing email
          instantly via its unsubscribe link.
        </p>

        <h2>7. Security</h2>
        <p>
          Data is encrypted in transit (TLS) and at rest by our infrastructure providers. Access
          to production data is restricted and authenticated. Stored third-party credentials you
          connect (such as CMS tokens) are encrypted at rest. No system is perfectly secure — if
          we become aware of a breach affecting your personal data, we will notify you as required
          by law.
        </p>

        <h2>8. Children</h2>
        <p>The Service is a business tool and is not directed at children under 18.</p>

        <h2>9. Changes</h2>
        <p>
          We may update this policy as the Service evolves. Material changes will be announced by
          email or an in-product notice, and the &quot;last updated&quot; date above always reflects
          the current version.
        </p>

        <h2>10. Contact</h2>
        <p>
          Surrvik E-Mobility — Data Protection<br />
          Email: <a href="mailto:privacy@surrvik.com">privacy@surrvik.com</a>
        </p>

        <p className="text-sm text-slate-500">
          See also our <Link href="/terms">Terms of Service</Link>.
        </p>
      </main>
    </div>
  );
}
