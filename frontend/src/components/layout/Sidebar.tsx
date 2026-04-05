"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Bot, Eye, FileText, Globe, Home, LayoutDashboard,
  LogOut, Search, Settings, Shield, Zap, ClipboardList,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: Home },
  { href: "/dashboard/projects", label: "Projects", icon: LayoutDashboard },
  { href: "/dashboard/research", label: "AI Research", icon: Bot },
  { href: "/dashboard/keywords", label: "Keyword Research", icon: Search },
  { href: "/dashboard/rank-tracker", label: "Rank Tracker", icon: BarChart3 },
  { href: "/dashboard/audit", label: "Technical Audit", icon: Shield },
  { href: "/dashboard/content", label: "Content", icon: FileText },
  { href: "/dashboard/competitors", label: "Competitors", icon: Eye },
  { href: "/dashboard/reports", label: "Reports", icon: ClipboardList },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
  { href: "/dashboard/billing", label: "Billing", icon: Zap },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 h-screen bg-surface-2 border-r border-zinc-800 flex flex-col fixed left-0 top-0 z-40">
      <div className="px-5 py-5 border-b border-zinc-800/50">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center font-bold text-sm">OR</div>
          <span className="font-semibold">OMNI-RANK</span>
        </Link>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href} className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150",
              active ? "bg-brand-600/10 text-brand-400 border border-brand-500/20" : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
            )}>
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="px-3 py-4 border-t border-zinc-800/50">
        <button className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-500 hover:text-red-400 hover:bg-red-500/5 w-full transition-colors">
          <LogOut className="w-4 h-4" /> Log out
        </button>
      </div>
    </aside>
  );
}
