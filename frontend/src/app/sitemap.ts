import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://omnirank.io";

// Public, indexable marketing routes. Utility/app surfaces (dashboard, auth,
// onboarding) are intentionally excluded — they're noindex.
const STATIC_PATHS = [
  "/",
  "/compare",
  "/tools",
  "/audit",
  "/benchmarks",
  "/guides",
  "/research",
  "/blog",
  "/case-studies",
  "/privacy",
  "/terms",
];

const VERTICALS = [
  "accounting", "b2b", "consulting", "ecommerce", "education", "fintech",
  "healthcare", "insurance", "legal", "local", "nonprofit", "realestate", "saas",
];

export default function sitemap(): MetadataRoute.Sitemap {
  const base = STATIC_PATHS.map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: "weekly" as const,
    priority: path === "/" ? 1 : 0.7,
  }));

  const solutions = VERTICALS.map((v) => ({
    url: `${SITE_URL}/solutions/${v}`,
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  const blogs = VERTICALS.map((v) => ({
    url: `${SITE_URL}/blog/${v}`,
    changeFrequency: "monthly" as const,
    priority: 0.5,
  }));

  return [...base, ...solutions, ...blogs];
}
