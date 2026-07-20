import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Industry-Specific SEO Playbooks",
  description:
    "Deep-dive SEO playbooks by industry — from feature clustering to E-E-A-T optimization to comparison-keyword dominance. Practical tactics for what actually works in each vertical.",
  alternates: { canonical: "/blog" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
