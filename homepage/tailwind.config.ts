import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Ventriloc design tokens (homepage)
        graphite: "#202020",
        "canvas-white": "#ffffff",
        ash: "#efefef",
        fog: "#f5f5f5",
        ivory: "#ebe6dd",
        steel: "#4d4d4d",
        slate: "#828282",
        mist: "#e8e8e8",
        "ember-orange": "#ff682c",
        brass: "#816729",
        // Legacy tokens (simulator pages)
        ink: "#0B0D12",
        paper: "#FAFAF8",
        muted: "#6B7280",
        accent: "#E85D04",
        accentHover: "#D44A03",
        success: "#0D7A33",
        warning: "#B85C00",
        danger: "#C01C28",
        border: "#E5E7EB",
        card: "#FFFFFF",
        code: "#1E293B",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      fontSize: {
        caption: ["14px", "1.43"],
        subheading: ["18px", "1.25"],
        heading: ["32px", "1.19"],
        "heading-lg": ["40px", "1.2"],
        display: ["66px", "0.91"],
      },
      letterSpacing: {
        heading: "-0.64px",
        "heading-lg": "-0.8px",
        display: "-1.32px",
        tight: "-0.02em",
      },
      borderRadius: {
        tags: "20px",
        cards: "8px",
        buttons: "0px",
        "nav-pills": "200px",
        asymmetric: "6px 0px 0px",
      },
      maxWidth: {
        page: "1200px",
      },
      animation: {
        "fade-in": "fadeIn 0.6s ease-out forwards",
        "slide-up": "slideUp 0.7s ease-out forwards",
        "slide-right": "slideRight 0.5s ease-out forwards",
        "scale-in": "scaleIn 0.4s ease-out forwards",
        "pulse-slow": "pulseSlow 3s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideRight: {
          "0%": { opacity: "0", transform: "translateX(-20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        pulseSlow: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
