/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
        "./src/**/*.{js,jsx,ts,tsx}",
        "./public/index.html"
    ],
    theme: {
        extend: {
            colors: {
                border: 'hsl(var(--border))',
                input: 'hsl(var(--input))',
                ring: 'hsl(var(--ring))',
                background: 'hsl(var(--background))',
                foreground: 'hsl(var(--foreground))',
                primary: {
                    DEFAULT: '#0F5C5E',
                    hover: '#0c4a4c',
                    foreground: 'hsl(var(--primary-foreground))'
                },
                secondary: {
                    DEFAULT: '#163A70',
                    foreground: 'hsl(var(--secondary-foreground))'
                },
                accent: {
                    DEFAULT: '#D9F1F4',
                    foreground: 'hsl(var(--accent-foreground))'
                },
                'support-accent': '#D8E6D5',
                surface: '#FFFFFF',
                'text-primary': '#17324D',
                'text-muted': '#5F6E7A',
                success: '#1F8F5F',
                warning: '#C78A12',
                error: '#C54B4B',
                info: '#2F6FED',
                destructive: {
                    DEFAULT: 'hsl(var(--destructive))',
                    foreground: 'hsl(var(--destructive-foreground))'
                },
                muted: {
                    DEFAULT: 'hsl(var(--muted))',
                    foreground: 'hsl(var(--muted-foreground))'
                },
                popover: {
                    DEFAULT: 'hsl(var(--popover))',
                    foreground: 'hsl(var(--popover-foreground))'
                },
                card: {
                    DEFAULT: 'hsl(var(--card))',
                    foreground: 'hsl(var(--card-foreground))'
                },
                chart: {
                    '1': 'hsl(var(--chart-1))',
                    '2': 'hsl(var(--chart-2))',
                    '3': 'hsl(var(--chart-3))',
                    '4': 'hsl(var(--chart-4))',
                    '5': 'hsl(var(--chart-5))'
                }
            },
            fontFamily: {
                sans: ['Manrope', 'sans-serif'],
                heading: ['Outfit', 'sans-serif'],
            },
            borderRadius: {
                lg: 'var(--radius)',
                md: 'calc(var(--radius) - 2px)',
                sm: 'calc(var(--radius) - 4px)'
            },
            boxShadow: {
                'sm': '0 2px 8px rgba(23, 50, 77, 0.04)',
                'md': '0 8px 24px rgba(23, 50, 77, 0.06)',
                'lg': '0 16px 48px rgba(23, 50, 77, 0.08)',
            }
        }
    },
    plugins: [require("tailwindcss-animate")],
}
