"use client";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("omnirank-theme") as "dark" | "light" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.setAttribute("data-theme", saved);
    }
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("omnirank-theme", next);
  };

  const Icon = theme === "dark" ? Sun : Moon;
  const iconColor = theme === "dark" ? "#FACC15" : "#8B5CF6";

  return (
    <button
      onClick={toggle}
      className="flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-sans font-medium w-full transition-colors hover:bg-[var(--sidebar-active-bg)]"
      style={{ color: "var(--sidebar-item)" }}
    >
      <span
        className="w-7 h-7 rounded-lg flex items-center justify-center"
        style={{ background: "var(--sidebar-icon-bg)", color: iconColor }}
      >
        <Icon className="w-[15px] h-[15px]" />
      </span>
      {theme === "dark" ? "Light mode" : "Dark mode"}
    </button>
  );
}
