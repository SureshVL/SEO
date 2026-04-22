"use client";
import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

interface Props {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  /** accent color for the icon tile + strip (hex). Defaults to violet. */
  accent?: string;
  /** right-side action area (buttons, selects, etc.) */
  actions?: ReactNode;
  /** optional chips / badges shown next to the title */
  chips?: ReactNode;
}

/**
 * Unified dashboard page header.
 *   ┌────────────────────────────────────────────┐
 *   │ ▓ [icon]  Title                 [actions] │
 *   │           subtitle                          │
 *   └────────────────────────────────────────────┘
 *   • a thin colored accent strip hints at the page identity
 */
export function PageHeader({ title, subtitle, icon: Icon, accent = "#8B5CF6", actions, chips }: Props) {
  return (
    <div className="mb-8 animate-fade-in">
      <div
        className="h-[3px] w-20 rounded-full mb-5"
        style={{ background: `linear-gradient(90deg, ${accent}, ${accent}55)` }}
      />
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-4 min-w-0">
          {Icon && (
            <div
              className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg"
              style={{
                background: `linear-gradient(135deg, ${accent}, ${accent}cc)`,
                boxShadow: `0 6px 18px ${accent}44`,
              }}
            >
              <Icon className="w-5 h-5 text-white" strokeWidth={2.2} />
            </div>
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="page-title">{title}</h1>
              {chips}
            </div>
            {subtitle && <p className="page-subtitle">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
      </div>
    </div>
  );
}
