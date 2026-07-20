import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://omni-rank.com";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "OMNI-RANK — AI SEO & AI Search Visibility Platform",
    template: "%s — OMNI-RANK",
  },
  description:
    "Track rankings, AI citations (ChatGPT, Perplexity, Gemini, Google AI Overviews), run audits, and generate content — for businesses in every country.",
  // English serves all regions today; hreflang alternates get added per
  // locale when translated versions of the site ship (app/[locale] phase).
  alternates: {
    canonical: "/",
    languages: { "x-default": "/", en: "/" },
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "OMNI-RANK",
    title: "OMNI-RANK — AI SEO & AI Search Visibility Platform",
    description:
      "AI-powered SEO and AI-search visibility for businesses worldwide. Pricing in USD and INR.",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "OMNI-RANK — AI SEO & AI Search Visibility Platform",
  },
  robots: { index: true, follow: true },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: "OMNI-RANK",
      url: SITE_URL,
      description:
        "AI-powered SEO and AI-search visibility platform for businesses worldwide.",
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: "OMNI-RANK",
      url: SITE_URL,
      publisher: { "@id": `${SITE_URL}/#organization` },
      inLanguage: "en",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${SITE_URL}/#software`,
      name: "OMNI-RANK",
      url: SITE_URL,
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      publisher: { "@id": `${SITE_URL}/#organization` },
      offers: {
        "@type": "AggregateOffer",
        priceCurrency: "USD",
        lowPrice: "0",
        highPrice: "249",
        offerCount: "5",
      },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {children}
        <Toaster theme="dark" position="top-right" richColors closeButton />
      </body>
    </html>
  );
}
