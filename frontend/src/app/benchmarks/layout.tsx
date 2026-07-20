import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Search Benchmarks by Industry",
  description:
    "Real-time AI citation benchmarks for every industry. See which brands win in ChatGPT, Perplexity, Gemini and Google AI Overviews, and how visibility shifts month over month.",
  alternates: { canonical: "/benchmarks" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
