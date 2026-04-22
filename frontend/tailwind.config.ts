import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#F5F3FF", 100: "#EDE9FE", 200: "#DDD6FE", 300: "#C4B5FD",
          400: "#A78BFA", 500: "#8B5CF6", 600: "#7C3AED", 700: "#6D28D9",
          800: "#5B21B6", 900: "#4C1D95", 950: "#2E1065",
        },
        accent: {
          magenta: "#EC4899", cyan: "#22D3EE", lime: "#A3E635",
          sun: "#FACC15", orange: "#F97316", teal: "#2DD4BF",
        },
        sage: { 400: "#8fb896", 500: "#6b8f71", 600: "#537a5a" },
        surface: { 1: "#0b0c10", 2: "#17191F", 3: "#23262F", 4: "#2E323D" },
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
