import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Free Instant Technical SEO Audit",
  description:
    "Run a free instant technical SEO audit. We crawl your site live for broken links, page speed, missing schema, thin content, orphan pages and more — full report in about a minute.",
  alternates: { canonical: "/audit" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
