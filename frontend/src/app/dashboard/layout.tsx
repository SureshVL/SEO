import { Sidebar } from "@/components/layout/Sidebar";
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen" style={{ background: "var(--bg-primary)" }}>
      <Sidebar />
      <main className="ml-64 min-h-screen"><div className="p-8 max-w-[1400px]">{children}</div></main>
    </div>
  );
}
