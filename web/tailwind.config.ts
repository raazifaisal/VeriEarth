import type { Config } from 'tailwindcss';

export default {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#10201F', 2: '#1E3532', 3: '#3A5550' },
        paper: { DEFAULT: '#F3F0E8', 2: '#FBFAF6', 3: '#E8E4D8', line: '#D9D3C4' },
        hazard: { DEFAULT: '#D9622B', dark: '#B5481A', light: '#F08A4B', wash: '#FBEDE3' },
        water: { DEFAULT: '#2F6F8F', light: '#7FB8D4', wash: '#E3EEF3' },
        muted: '#43504E',
        subtle: '#5C6563',
      },
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'sans-serif'],
        sans: ['var(--font-sans)', 'Arial', 'sans-serif'],
        mono: ['var(--font-mono)', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config;
