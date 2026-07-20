import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { CopilotWidget } from "@/components/copilot/CopilotWidget";

export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg-primary)" }}>
      <Sidebar />
      <main className="ml-64 min-h-screen"><div className="p-8 max-w-[1400px]">{children}</div></main>
      <CopilotWidget />
    </div>
  );
}
