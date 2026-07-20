import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "OMNI-RANK vs SEMrush, Ahrefs & RankIQ",
  description:
    "Compare OMNI-RANK with SEMrush, Ahrefs and RankIQ feature by feature — AI strategy, auto-fix recommendations, GitHub integration, a free tier and India-first pricing in ₹.",
  alternates: { canonical: "/compare" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
