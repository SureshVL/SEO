import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Ranking Guides for Every Industry",
  description:
    "52 industry-specific guides to ranking in ChatGPT, Perplexity, Gemini and Google AI Overviews. Practical playbooks for winning citations and organic visibility in AI search.",
  alternates: { canonical: "/guides" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
