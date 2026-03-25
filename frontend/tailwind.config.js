/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./pages/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg:      "#0f1117",
        surface: "#1a1d27",
        border:  "#2a2d3a",
      },
    },
  },
  plugins: [],
}
