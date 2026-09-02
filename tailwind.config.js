/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./**/templates/**/*.html", "./**/*.py", "./static/js/**/*.js"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "sans-serif"],
      },
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        sage: "#65916C",
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          900: "#1e3a8a",
        },
        // Charte graphique reprise de l'ancienne plateforme (yupaan.bsb.gov.bf) :
        // rouge vif + jaune, dégradé 135° rouge→jaune, fond crème. Les clés
        // historiques (gold/red/green/gray) sont conservées — elles sont utilisées
        // dans tout le back-office — seul `red` est réaligné sur le rouge officiel.
        bsb: {
          gold: "#ca8a04",
          red: "#e53935",       // --primary-color de l'ancienne plateforme
          green: "#16a34a",
          gray: "#6b7280",

          primary: "#e53935",   // rouge vif
          dark: "#b71c1c",      // --primary-dark
          yellow: "#fbc02d",    // --secondary-color
          accent: "#ffd600",    // --accent-color
          amber: "#fbbf24",     // chiffres des statistiques sur fond dégradé
          cream: "#fff8e1",     // --bg-secondary
          ink: "#1f2937",       // --text-primary
          muted: "#6b7280",     // --text-secondary
        },

        // =======
        slate: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
          950: "#020617",
        },
        red: {
          700: "#E30613",
          800: "#991b1b",
          burgundy: "#8B1E1E",
          burgundyDark: "#701818",
        },
        amber: {
          600: "#d97706",
          gold: "#C5A059",
        },
      },
    },
  },
  plugins: [],
};
