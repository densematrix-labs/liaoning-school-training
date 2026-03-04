/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Railway Industrial Blue Theme
        railway: {
          900: '#0a0f1a',
          800: '#0d1525',
          700: '#111d32',
          600: '#16263f',
          500: '#1b304d',
          400: '#234069',
          300: '#2d5280',
          200: '#3a6699',
          100: '#4a7ab3',
          50: '#5d8fcc',
        },
        accent: {
          blue: '#00d4ff',
          cyan: '#00fff2',
          electric: '#0088ff',
          glow: '#00aaff',
        },
        status: {
          success: '#00ff88',
          warning: '#ffaa00',
          danger: '#ff4455',
          info: '#00ccff',
        },
        text: {
          primary: '#e8f4ff',
          secondary: '#8eb8e5',
          muted: '#5d7a9c',
        }
      },
      fontFamily: {
        // Industrial/Tech fonts - avoiding Inter/Roboto
        display: ['"Orbitron"', '"Rajdhani"', 'system-ui', 'sans-serif'],
        body: ['"Exo 2"', '"Titillium Web"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        chinese: ['"Noto Sans SC"', '"Source Han Sans SC"', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(0, 136, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 136, 255, 0.03) 1px, transparent 1px)',
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
      backgroundSize: {
        'grid': '50px 50px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan': 'scan 4s linear infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(0, 212, 255, 0.5), 0 0 10px rgba(0, 212, 255, 0.3)' },
          '100%': { boxShadow: '0 0 10px rgba(0, 212, 255, 0.8), 0 0 20px rgba(0, 212, 255, 0.5), 0 0 30px rgba(0, 212, 255, 0.3)' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(0, 212, 255, 0.3)',
        'glow-md': '0 0 20px rgba(0, 212, 255, 0.4)',
        'glow-lg': '0 0 30px rgba(0, 212, 255, 0.5)',
        'inner-glow': 'inset 0 0 20px rgba(0, 212, 255, 0.1)',
      },
    },
  },
  plugins: [],
}
