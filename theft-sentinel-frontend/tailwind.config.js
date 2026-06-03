/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Dark Theme Primary Colors
        dark: {
          bg: '#0B0F14',        // Deep black background
          surface: '#111827',    // Charcoal surface
          card: '#1F2933',       // Graphite card
          border: '#374151',      // Dark gray border
          text: {
            primary: '#F9FAFB',  // Almost white
            secondary: '#D1D5DB', // Light gray
            muted: '#9CA3AF',    // Soft gray
            disabled: '#6B7280', // Disabled gray
          }
        },
        // AI/Cyber Accent Colors
        ai: {
          blue: '#00D9FF',       // Cyber teal
          blueDark: '#0099CC',   // Darker teal
          purple: '#8B5CF6',     // AI purple
          cyan: '#06B6D4',       // Cyan accent
        },
        // Status Colors
        status: {
          success: '#10B981',    // Green
          warning: '#F59E0B',    // Amber
          error: '#EF4444',      // Red
          info: '#3B82F6',       // Blue
        },
        // Legacy support (for gradual migration)
        primary: {
          DEFAULT: '#00D9FF',   // AI blue
          dark: '#0B0F14',
        },
        secondary: {
          DEFAULT: '#111827',
          blue: '#234C6A',
        },
        accent: {
          DEFAULT: '#1F2933',
          gray: '#456882',
        },
        sand: {
          DEFAULT: '#9CA3AF',
          light: '#D1D5DB',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        display: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(0, 217, 255, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 217, 255, 0.8), 0 0 30px rgba(0, 217, 255, 0.4)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(0, 217, 255, 0.3)',
        'glow-lg': '0 0 40px rgba(0, 217, 255, 0.4)',
        'dark': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
        'dark-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
      },
    },
  },
  plugins: [],
}
