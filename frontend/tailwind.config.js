/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // A warm, twilight concert-hall palette.
        ink: "#0b0d17",
        panel: "#141726",
        haze: "#1e2236",
        gold: "#d9b26a",
        rose: "#c97b84",
        sky: "#7aa2d1",
        mist: "#a7adc4",
      },
      fontFamily: {
        serif: ["'Cormorant Garamond'", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
