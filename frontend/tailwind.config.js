/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "rgb(var(--color-page) / <alpha-value>)",
        panel: "rgb(var(--color-panel) / <alpha-value>)",
        panelSoft: "rgb(var(--color-panel-soft) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        accent: "#ec4899",
        danger: "#ef4444",
        warning: "#f59e0b",
      },
      boxShadow: {
        glow: "0 0 0 1px rgb(var(--color-glow-line) / 0.4), 0 20px 60px rgb(var(--color-glow-shadow) / 0.22)",
      },
    },
  },
  plugins: [],
};
