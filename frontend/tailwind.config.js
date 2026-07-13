/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#111827",
        panelSoft: "#162033",
        line: "#263143",
        ink: "#e5edf6",
        muted: "#91a0b5",
        accent: "#14b8a6",
        danger: "#ef4444",
        warning: "#f59e0b",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(20, 184, 166, 0.18), 0 20px 60px rgba(0, 0, 0, 0.28)",
      },
    },
  },
  plugins: [],
};
