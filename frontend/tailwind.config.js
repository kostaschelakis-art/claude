/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#FF6600',
        dark: '#1A1A2E',
        accent: '#FFD700',
        surface: '#16213E',
      },
    },
  },
  plugins: [],
};
