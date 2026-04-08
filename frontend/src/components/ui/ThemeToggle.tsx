"use client";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark"|"light">("dark");
  useEffect(() => {
    const saved = localStorage.getItem("omnirank-theme") as "dark"|"light"|null;
    if (saved) { setTheme(saved); document.documentElement.setAttribute("data-theme", saved); }
  }, []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("omnirank-theme", next);
  };
  return (
    <button onClick={toggle} className="flex items-center gap-2 px-3 py-2 rounded-xl text-[13px] font-sans w-full transition-all duration-200" style={{ color: "var(--text-muted)" }}>
      {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      {theme === "dark" ? "Light mode" : "Dark mode"}
    </button>
  );
}
