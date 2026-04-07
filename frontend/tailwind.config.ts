import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#faf5ee", 100: "#f0e4d0", 200: "#e0c8a0", 300: "#d0a870",
          400: "#c87941", 500: "#b06830", 600: "#8b5a2b", 700: "#6b4420",
          800: "#4b3018", 900: "#2e1e10", 950: "#1a110a",
        },
        sage: {
          400: "#8fb896", 500: "#6b8f71", 600: "#537a5a",
        },
        surface: { 1: "#110f0d", 2: "#1c1917", 3: "#2c2723", 4: "#3d3530" },
      },
      fontFamily: {
        serif: ['"Instrument Serif"', "Georgia", "serif"],
        sans: ['"Outfit"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
