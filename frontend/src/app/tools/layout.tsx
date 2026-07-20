import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Free SEO & Marketing Calculators",
  description:
    "20+ free SEO and paid-search tools — keyword density, SERP snippet, word counter, CPC, ROAS, CTR, page speed and more. No signup, everything runs right in your browser.",
  alternates: { canonical: "/tools" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
