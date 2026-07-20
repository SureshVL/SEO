import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Search Research Reports",
  description:
    "Monthly AI visibility research across ChatGPT, Perplexity, Gemini and Google AI Overviews. Data-driven analysis of citation trends, winners and ranking factors in AI search.",
  alternates: { canonical: "/research" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
