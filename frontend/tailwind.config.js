/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          DEFAULT: '#F5F3EE',
          dark: '#ECE9E2',
        },
        ink: {
          primary: '#161616',
          secondary: '#5C5C5C',
          light: '#8A8780',
        },
        accent: {
          DEFAULT: '#23403B',
          light: '#2D524C',
          dark: '#1A302C',
        },
        stone: {
          DEFAULT: '#B8B5AE',
          light: '#D8D5CE',
        },
        sand: '#D8CBB8',
        sage: {
          DEFAULT: '#6E8B74',
          light: '#8BA890',
          muted: '#A8BFB0',
        },
        amber: {
          DEFAULT: '#B98B4D',
          light: '#C9A068',
          muted: '#D4B896',
        },
        border: {
          DEFAULT: 'rgba(0,0,0,0.08)',
          strong: 'rgba(0,0,0,0.12)',
        },
      },
      fontFamily: {
        serif: ['Instrument Serif', 'DM Serif Display', 'Georgia', 'serif'],
        sans: ['Inter', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(0,0,0,0.03), 0 8px 24px rgba(0,0,0,0.04)',
        subtle: '0 1px 3px rgba(0,0,0,0.04)',
        elevated: '0 2px 4px rgba(0,0,0,0.04), 0 12px 32px rgba(0,0,0,0.06)',
      },
      borderRadius: {
        card: '8px',
        button: '6px',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'line-reveal': 'lineReveal 0.6s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        lineReveal: {
          '0%': { width: '0' },
          '100%': { width: '100%' },
        },
      },
    },
  },
  plugins: [],
}
