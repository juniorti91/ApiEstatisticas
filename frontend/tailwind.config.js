/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#12141c",
        panel2: "#171a24",
        base: "#0b0d13",
        border: "#232733",
        accent: "#22c55e",
        accentdim: "#16321f",
        muted: "#8a90a2",
      },
    },
  },
  plugins: [],
};
