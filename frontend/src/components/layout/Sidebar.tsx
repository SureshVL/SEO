"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Bot, Braces, ClipboardList, Eye, FileText, Home, LayoutDashboard, Lightbulb, LogOut, Search, Settings, Shield, Sparkles, Zap } from "lucide-react";
import { ThemeToggle } from "../ui/ThemeToggle";
const navSections = [
  { label: "Command", items: [{ href: "/dashboard", label: "Overview", icon: Home },{ href: "/dashboard/projects", label: "Projects", icon: LayoutDashboard }]},
  { label: "Intelligence", items: [{ href: "/dashboard/research", label: "AI Research", icon: Bot },{ href: "/dashboard/keywords", label: "Keywords", icon: Search },{ href: "/dashboard/rank-tracker", label: "Rank Tracker", icon: BarChart3 },{ href: "/dashboard/ai-visibility", label: "AI Visibility", icon: Sparkles },{ href: "/dashboard/competitors", label: "Competitors", icon: Eye }]},
  { label: "Execute", items: [{ href: "/dashboard/audit", label: "Technical Audit", icon: Shield },{ href: "/dashboard/schema", label: "Schema Markup", icon: Braces },{ href: "/dashboard/brief", label: "Content Brief", icon: Lightbulb },{ href: "/dashboard/content", label: "Content Studio", icon: FileText },{ href: "/dashboard/reports", label: "Reports", icon: ClipboardList }]},
  { label: "Account", items: [{ href: "/dashboard/settings", label: "Settings", icon: Settings },{ href: "/dashboard/billing", label: "Billing", icon: Zap }]},
];
export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-64 h-screen fixed left-0 top-0 z-40 flex flex-col" style={{ background: "var(--bg-primary)", borderRight: "1px solid var(--border)" }}>
      <div className="px-6 py-6" style={{ borderBottom: "1px solid var(--border)" }}>
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center font-serif text-base font-bold" style={{ background: "linear-gradient(135deg, var(--copper), var(--copper-dark))", color: "#faf8f5" }}>OR</div>
          <div><div className="font-serif text-lg tracking-tight" style={{ color: "var(--text-primary)" }}>Omni-Rank</div><div className="text-[10px] font-sans uppercase tracking-[0.15em]" style={{ color: "var(--text-muted)" }}>SEO Intelligence</div></div>
        </Link>
      </div>
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-5">
        {navSections.map((section) => (
          <div key={section.label}>
            <div className="px-3 mb-2 text-[10px] font-sans font-semibold uppercase tracking-[0.15em]" style={{ color: "var(--text-faint)" }}>{section.label}</div>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
                return (<Link key={item.href} href={item.href} className="flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-sans font-medium transition-all duration-200" style={{ color: active ? "var(--text-primary)" : "var(--text-muted)", background: active ? "rgba(200,121,65,0.08)" : "transparent", borderLeft: active ? "2px solid var(--copper)" : "2px solid transparent" }}>
                  <item.icon className="w-4 h-4 flex-shrink-0" style={{ opacity: active ? 1 : 0.5 }} />{item.label}
                </Link>);
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="px-3 py-3 space-y-1" style={{ borderTop: "1px solid var(--border)" }}>
        <ThemeToggle />
        <button className="flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-sans w-full" style={{ color: "var(--text-muted)" }}><LogOut className="w-4 h-4" /> Log out</button>
      </div>
    </aside>
  );
}
