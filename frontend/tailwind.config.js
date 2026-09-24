/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Institutional base — a restrained navy/slate scale rather than a
        // brand palette. The interface should read as official, not marketed.
        ink: {
          DEFAULT: '#0f172a',
          50: '#f6f7f9',
          100: '#eceef2',
          200: '#d5dae2',
          300: '#b0b9c7',
          400: '#8492a6',
          500: '#64748b',
          600: '#4a5568',
          700: '#33405a',
          800: '#1e2a45',
          900: '#0f172a',
        },
        // Risk colours are semantic: each band has exactly one colour and that
        // colour is never used for anything else in the interface.
        risk: {
          low: '#15803d',
          lowBg: '#f0fdf4',
          lowBorder: '#bbf7d0',
          medium: '#b45309',
          mediumBg: '#fffbeb',
          mediumBorder: '#fde68a',
          high: '#c2410c',
          highBg: '#fff7ed',
          highBorder: '#fed7aa',
          critical: '#b91c1c',
          criticalBg: '#fef2f2',
          criticalBorder: '#fecaca',
        },
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"SFMono-Regular"', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        panel: '0 1px 2px 0 rgb(15 23 42 / 0.06), 0 1px 3px 0 rgb(15 23 42 / 0.04)',
      },
    },
  },
  plugins: [],
}
