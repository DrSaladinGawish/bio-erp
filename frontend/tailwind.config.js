/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brain: {
          slate: '#0F172A',
          dark: '#020617',
          green: '#22C55E',
          'green-glow': 'rgba(34, 197, 94, 0.15)',
          blue: '#3B82F6',
          purple: '#8B5CF6',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-in',
        heartbeat: 'heartbeat 3s ease-in-out infinite',
        'neural-pulse': 'neuralPulse 2s ease-in-out infinite',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        heartbeat: {
          '0%, 100%': { transform: 'scaleY(1)' },
          '15%': { transform: 'scaleY(1.3)' },
          '30%': { transform: 'scaleY(0.8)' },
          '45%': { transform: 'scaleY(1.1)' },
          '60%': { transform: 'scaleY(1)' },
        },
        neuralPulse: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.05)' },
        },
      },
    },
  },
  plugins: [],
}
