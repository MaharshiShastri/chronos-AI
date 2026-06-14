/** @type {import('tailwindcss').Config} */
export default {
  // CRITICAL: This tells Tailwind to scan your React components
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Adding your project's specific neon blue
        'chronos-blue': '#38bdf8',
        'chronos-bg': '#0f172a',
        'chronos-card': '#1e293b',
      },
    },
  },
  plugins: [],
}