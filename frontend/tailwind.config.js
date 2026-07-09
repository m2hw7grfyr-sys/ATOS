/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        canvas: "#f5f7f8",
        line: "#dfe5e7",
        teal: "#087f73",
        cyan: "#0b7285",
        amber: "#b26a00",
      },
    },
  },
  plugins: [],
};
