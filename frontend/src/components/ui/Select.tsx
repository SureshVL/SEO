"use client";
import { SelectHTMLAttributes, forwardRef } from "react";
import { LucideIcon } from "lucide-react";

interface Option {
  value: string;
  label: string;
}

interface Props extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  options: Option[];
  icon?: LucideIcon;
  placeholder?: string;
  /** accent color for the icon badge (hex). Defaults to violet. */
  accent?: string;
  /** width utility class, defaults to min-w-[220px] */
  widthClass?: string;
}

/**
 * Polished pill-style select that replaces raw <select className="input-field">.
 * Uses the same underlying native <select> (a11y + form compatibility intact),
 * but wraps it in a colored icon badge + chevron.
 */
export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { options, icon: Icon, placeholder, accent = "#8B5CF6", widthClass = "min-w-[220px]", className = "", ...rest },
  ref,
) {
  return (
    <div className={`relative inline-flex items-center ${widthClass}`}>
      {Icon && (
        <span
          className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-lg flex items-center justify-center z-10"
          style={{ background: `${accent}22`, color: accent }}
        >
          <Icon className="w-[14px] h-[14px]" strokeWidth={2.2} />
        </span>
      )}
      <select
        ref={ref}
        {...rest}
        className={`select-field w-full rounded-xl py-2.5 text-sm font-medium transition-all duration-150 ${Icon ? "pl-11" : "pl-4"} pr-10 ${className}`}
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border-strong)",
          color: "var(--text-primary)",
        }}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
});
