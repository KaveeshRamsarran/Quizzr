/** @type {import('tailwindcss').Config} */
// Layout utilities only; every colour and face comes from the Ultraviolet tokens in src/styles/tokens.css.
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // Component classes whose modifier is built at runtime (btn--${variant}, rating--${value}).
  safelist: [{ pattern: /^(btn|rating|badge|notice|card|icon-tile|progress)--/ }],
  theme: {
    extend: {
      colors: {
        paper: 'var(--color-paper)',
        'paper-2': 'var(--color-paper-2)',
        'paper-3': 'var(--color-paper-3)',
        ink: 'var(--color-ink)',
        'ink-2': 'var(--color-ink-2)',
        muted: 'var(--color-muted)',
        rule: 'var(--color-rule)',
        'rule-2': 'var(--color-rule-2)',
        accent: 'var(--color-accent)',
        error: 'var(--color-error)',
        success: 'var(--color-success)',
      },
      fontFamily: {
        display: 'var(--font-display)',
        body: 'var(--font-body)',
        mono: 'var(--font-outlier)',
      },
    },
  },
  plugins: [],
}
