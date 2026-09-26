/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Gearbox-inspired industrial control-room theme
        railway: {
          900: '#032d69',
          800: '#063d82',
          700: '#0a4d98',
          600: '#105dac',
          500: '#176dc0',
          400: '#2780d3',
          300: '#4a98e2',
          200: '#79b6ec',
          100: '#acd5f5',
          50: '#d8efff',
        },
        accent: {
          blue: '#00c8ff',
          cyan: '#64ecff',
          electric: '#008cff',
          glow: '#00b8ff',
        },
        status: {
          success: '#39e58c',
          warning: '#ffc04a',
          danger: '#ff6674',
          info: '#5ad9ff',
        },
        text: {
          primary: '#f5fbff',
          secondary: '#bedfff',
          muted: '#86aed2',
        }
      },
      fontFamily: {
        // Industrial/Tech fonts - avoiding Inter/Roboto
        display: ['"Rajdhani"', '"Orbitron"', '"Noto Sans SC"', 'system-ui', 'sans-serif'],
        body: ['"Rajdhani"', '"Noto Sans SC"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        chinese: ['"Noto Sans SC"', '"Source Han Sans SC"', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'grid-pattern': 'linear-gradient(rgba(100, 236, 255, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(100, 236, 255, 0.08) 1px, transparent 1px)',
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
