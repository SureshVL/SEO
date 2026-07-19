"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Bot, Braces, Calendar, ClipboardList, Coins, Eye, FileText, GitPullRequest, Grid3x3, Home, LayoutDashboard, Lightbulb, Link2, LogOut, MousePointerClick, Palette, RefreshCw, Rocket, Search, Settings, Share2, Shield, Smartphone, ShoppingCart, Sparkles, Zap } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";
import { ProjectPicker } from "./ProjectPicker";

const navSections = [
  { label: "Command", items: [
    { href: "/dashboard", label: "Overview", icon: Home, color: "#8B5CF6" },
    { href: "/dashboard/projects", label: "Projects", icon: LayoutDashboard, color: "#EC4899" },
    { href: "/dashboard/workflow", label: "Workflow", icon: Calendar, color: "#FACC15" },
  ]},
  { label: "Intelligence", items: [
    { href: "/dashboard/research", label: "AI Research", icon: Bot, color: "#8B5CF6" },
    { href: "/dashboard/keywords", label: "Keywords", icon: Search, color: "#22D3EE" },
    { href: "/dashboard/budget-keywords", label: "Budget Keywords", icon: Coins, color: "#FACC15" },
    { href: "/dashboard/rank-tracker", label: "Rank Tracker", icon: BarChart3, color: "#EC4899" },
    { href: "/dashboard/ai-visibility", label: "AI Visibility", icon: Sparkles, color: "#A3E635" },
    { href: "/dashboard/attribution", label: "Attribution", icon: Coins, color: "#F97316" },
    { href: "/dashboard/competitors", label: "Competitors", icon: Eye, color: "#22D3EE" },
  ]},
  { label: "Execute", items: [
    { href: "/dashboard/audit", label: "Technical Audit", icon: Shield, color: "#A3E635" },
    { href: "/dashboard/cro", label: "CRO Audit", icon: MousePointerClick, color: "#F43F5E" },
    { href: "/dashboard/aso", label: "App Store (ASO)", icon: Smartphone, color: "#2DD4BF" },
    { href: "/dashboard/schema", label: "Schema Markup", icon: Braces, color: "#8B5CF6" },
    { href: "/dashboard/brief", label: "Content Brief", icon: Lightbulb, color: "#F97316" },
    { href: "/dashboard/content", label: "Content Studio", icon: FileText, color: "#818CF8" },
    { href: "/dashboard/refresh", label: "Content Refresh", icon: RefreshCw, color: "#34D399" },
    { href: "/dashboard/social", label: "Social Studio", icon: Share2, color: "#E1306C" },
    { href: "/dashboard/programmatic", label: "Programmatic", icon: Grid3x3, color: "#FACC15" },
    { href: "/dashboard/links", label: "Link Building", icon: Link2, color: "#2DD4BF" },
    { href: "/dashboard/edge", label: "Edge Deploy", icon: Rocket, color: "#14B8A6" },
    { href: "/dashboard/git", label: "Git Write-back", icon: GitPullRequest, color: "#6366F1" },
    { href: "/dashboard/feeds", label: "Product Feeds", icon: ShoppingCart, color: "#F97316" },
    { href: "/dashboard/reports", label: "Reports", icon: ClipboardList, color: "#EC4899" },
  ]},
  { label: "Account", items: [
    { href: "/dashboard/branding", label: "White-label", icon: Palette, color: "#F43F5E" },
    { href: "/dashboard/settings", label: "Settings", icon: Settings, color: "#8B5CF6" },
    { href: "/dashboard/billing", label: "Billing", icon: Zap, color: "#FACC15" },
  ]},
];

export function Sidebar() {
  const pathname = usePathname();

  async function handleLogout() {
    try {
      const { createClient } = await import("@/lib/supabase");
      await createClient().auth.signOut();
    } catch {
      /* proceed to login regardless */
    }
    // Clear persisted UI state so the next login doesn't inherit this
    // session's project selection.
    try { localStorage.removeItem("omnirank-store"); } catch { /* ignore */ }
    window.location.href = "/auth/login";
  }
  return (
    <aside
      className="w-64 h-screen fixed left-0 top-0 z-40 flex flex-col"
      style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
    >
      <div className="px-6 py-6" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
        <Link href="/dashboard" className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-serif text-base font-bold shadow-lg"
            style={{ background: "linear-gradient(135deg, #8B5CF6, #EC4899)", color: "#ffffff", boxShadow: "0 4px 14px rgba(139,92,246,0.4)" }}
          >OR</div>
          <div>
            <div className="font-serif text-lg tracking-tight" style={{ color: "var(--sidebar-text)" }}>Omni-Rank</div>
            <div className="text-[10px] font-sans uppercase tracking-[0.15em]" style={{ color: "var(--sidebar-muted)" }}>SEO Intelligence</div>
          </div>
        </Link>
      </div>

      <ProjectPicker />

      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-5">
        {navSections.map((section) => (
          <div key={section.label}>
            <div
              className="px-3 mb-2 text-[10px] font-sans font-semibold uppercase tracking-[0.18em]"
              style={{ color: "var(--sidebar-section)" }}
            >
              {section.label}
            </div>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-sans font-medium transition-all duration-150"
                    style={{
                      color: active ? "var(--sidebar-text)" : "var(--sidebar-item)",
                      background: active ? "var(--sidebar-active-bg)" : "transparent",
                    }}
                  >
                    <span
                      className="w-7 h-7 rounded-lg flex items-center justify-center transition-all"
                      style={{
                        background: active ? item.color : "var(--sidebar-icon-bg)",
                        color: active ? "#ffffff" : item.color,
                      }}
                    >
                      <item.icon className="w-[15px] h-[15px]" />
                    </span>
                    {item.label}
                    {active && (
                      <span
                        className="ml-auto w-1.5 h-1.5 rounded-full"
                        style={{ background: item.color, boxShadow: `0 0 8px ${item.color}` }}
                      />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-3 py-3 space-y-1" style={{ borderTop: "1px solid var(--sidebar-border)" }}>
        <ThemeToggle />
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-sans font-medium w-full transition-colors hover:bg-[var(--sidebar-active-bg)]"
          style={{ color: "var(--sidebar-item)" }}
        >
          <span className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "var(--sidebar-icon-bg)", color: "#F43F5E" }}>
            <LogOut className="w-[15px] h-[15px]" />
          </span>
          Log out
        </button>
      </div>
    </aside>
  );
}
