/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Design tokens จาก Design/DESIGN.md
      colors: {
        sidebar: {
          bg: '#0F172A',
          text: '#94A3B8',
          active: '#1E293B',
          hover: '#1E293B',
        },
        accent: {
          DEFAULT: '#2563EB',
          soft: '#DBEAFE',
        },
        cyan: {
          DEFAULT: '#0891B2',
          soft: '#CFFAFE',
        },
        status: {
          green: '#16A34A',
          red: '#DC2626',
          amber: '#D97706',
          gray: '#64748B',
        },
        terminal: {
          bg: '#0B1120',
          text: '#E2E8F0',
          border: '#1E293B',
        },
      },
      fontFamily: {
        // Typography จาก Design/DESIGN.md
        sans: ['Noto Sans Thai', 'IBM Plex Sans Thai', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        // Type scale จาก Design/DESIGN.md
        xs: '12px',
        sm: '13px',
        base: '14px',
        md: '15px',
        lg: '16px',
        xl: '18px',
        '2xl': '22px',
      },
    },
  },
  plugins: [],
}
