import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

// ── Metric Card ──
export function MetricCard({
  label, value, icon: Icon, color = "text-zinc-200", note,
}: {
  label: string; value: string | number; icon?: LucideIcon; color?: string; note?: string;
}) {
  return (
    <div className="metric-card">
      <div className="flex items-center justify-between mb-3">
        <span className="metric-label">{label}</span>
        {Icon && <Icon className={cn("w-4 h-4", color)} />}
      </div>
      <div className={cn("metric-value", color)}>{value}</div>
      {note && <div className="text-xs text-zinc-500 mt-1">{note}</div>}
    </div>
  );
}

// ── Score Ring ──
export function ScoreRing({ score, size = 80, label }: { score: number; size?: number; label?: string }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "#22c55e" : score >= 50 ? "#f59e0b" : "#ef4444";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgb(39,39,42)" strokeWidth={4} />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" className="transition-all duration-1000"
        />
      </svg>
      <span className="text-lg font-bold" style={{ color, marginTop: -size / 2 - 10, position: "relative" }}>
        {Math.round(score)}
      </span>
      {label && <span className="text-xs text-zinc-500 mt-1">{label}</span>}
    </div>
  );
}

// ── Badge ──
export function Badge({ children, variant = "info" }: { children: React.ReactNode; variant?: "success" | "warning" | "error" | "info" }) {
  const styles = {
    success: "badge-success",
    warning: "badge-warning",
    error: "badge-error",
    info: "badge-info",
  };
  return <span className={styles[variant]}>{children}</span>;
}

// ── Empty State ──
export function EmptyState({ icon: Icon, title, description, action }: {
  icon: LucideIcon; title: string; description: string; action?: React.ReactNode;
}) {
  return (
    <div className="card p-12 text-center">
      <Icon className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <p className="text-sm text-zinc-400 max-w-sm mx-auto mb-6">{description}</p>
      {action}
    </div>
  );
}

// ── Loading Spinner ──
export function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const s = size === "sm" ? "w-4 h-4" : size === "lg" ? "w-8 h-8" : "w-6 h-6";
  return <div className={cn(s, "border-2 border-brand-500 border-t-transparent rounded-full animate-spin")} />;
}

// ── Page Header ──
export function PageHeader({ title, description, icon: Icon, color = "text-brand-400", action }: {
  title: string; description: string; icon?: LucideIcon; color?: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          {Icon && <Icon className={cn("w-6 h-6", color)} />} {title}
        </h1>
        <p className="text-sm text-zinc-400 mt-1">{description}</p>
      </div>
      {action}
    </div>
  );
}
