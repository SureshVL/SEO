import Link from "next/link";

export const metadata = { title: "Terms of Service — OMNI-RANK" };

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center">
          <Link href="/" className="font-bold text-lg">OR OMNI-RANK</Link>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-16 prose prose-slate">
        <h1>Terms of Service</h1>
        <p className="text-sm text-slate-500">Last updated: July 2026</p>

        <h2>The service</h2>
        <p>
          OMNI-RANK provides SEO and AI-search visibility software: keyword research, rank
          tracking, technical audits, content tooling, and reporting. Paid plans are billed
          in advance on a monthly or annual basis and renew automatically until cancelled.
        </p>

        <h2>Your responsibilities</h2>
        <ul>
          <li>Only connect websites and accounts you own or are authorised to manage.</li>
          <li>Keep your account credentials secure; you are responsible for activity under your account.</li>
          <li>Do not use the service to send spam, scrape third parties unlawfully, or violate any platform&apos;s terms.</li>
        </ul>

        <h2>No ranking guarantees</h2>
        <p>
          Search engines and AI answer engines change constantly. Metrics, projections, and
          illustrative scenarios shown in the product or on this site are not a promise of
          specific rankings, traffic, or revenue outcomes.
        </p>

        <h2>Billing &amp; cancellation</h2>
        <p>
          You can cancel anytime from Billing settings; access continues to the end of the paid
          period. Fees already paid are non-refundable except where required by law.
        </p>

        <h2>Liability</h2>
        <p>
          The service is provided &quot;as is&quot;. To the maximum extent permitted by law, our
          total liability is limited to the fees you paid in the twelve months before the claim.
        </p>

        <h2>Contact</h2>
        <p>
          Questions about these terms: <a href="mailto:legal@omni-rank.com">legal@omni-rank.com</a>
        </p>

        <p className="text-sm text-slate-500">
          See also our <Link href="/privacy">Privacy Policy</Link>.
        </p>
      </main>
    </div>
  );
}
