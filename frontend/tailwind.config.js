/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          orange: '#FF5A1F',
          dark: '#0A0A0A',
          card: '#141414',
          gray: '#8E8E93',
          border: '#262626',
        }
      }
    },
  },
  plugins: [],
}
