/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          900: "#0b1020",
          700: "#1f2540",
          500: "#5a6280",
        },
      },
    },
  },
  plugins: [],
};
