import { useEffect, useRef, useState, type ReactNode } from 'react'
import { animate, motion, useInView, useReducedMotion, type Variants } from 'framer-motion'

export const EASE_OUT = [0.16, 1, 0.3, 1] as const

/** Fade and rise in when a page mounts. */
export function Page({ children, className = 'page' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.38, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  )
}

const listVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.045, delayChildren: 0.05 } },
}
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: EASE_OUT } },
}

/** A container whose direct <Item> children enter one after another. */
export function Stagger({ children, className, as = 'div' }: { children: ReactNode; className?: string; as?: 'div' | 'ul' | 'ol' }) {
  const Tag = motion[as]
  return (
    <Tag className={className} variants={listVariants} initial="hidden" animate="show">
      {children}
    </Tag>
  )
}

export function Item({ children, className, as = 'div', onClick }: { children: ReactNode; className?: string; as?: 'div' | 'li'; onClick?: () => void }) {
  const Tag = motion[as]
  return (
    <Tag className={className} variants={itemVariants} onClick={onClick}>
      {children}
    </Tag>
  )
}

/** Fade up once when scrolled into view (landing page sections). */
export function Reveal({ children, className, delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.55, ease: EASE_OUT, delay }}
    >
      {children}
    </motion.div>
  )
}

/** Counts from the previous value to a real figure. */
export function CountUp({ value, decimals = 0, suffix = '' }: { value: number; decimals?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const previous = useRef(0)
  const reduce = useReducedMotion()
  const inView = useInView(ref, { once: true })

  useEffect(() => {
    const node = ref.current
    if (!node || !inView) return
    const format = (v: number) => `${v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`
    if (reduce) {
      node.textContent = format(value)
      previous.current = value
      return
    }
    const controls = animate(previous.current, value, {
      duration: 0.7,
      ease: EASE_OUT,
      onUpdate: (v) => { node.textContent = format(v) },
    })
    previous.current = value
    return () => controls.stop()
  }, [value, decimals, suffix, reduce, inView])

  return <span ref={ref} aria-label={`${value}${suffix}`}>{`${(0).toFixed(decimals)}${suffix}`}</span>
}

/** A progress bar whose fill grows to its value. */
export function ProgressBar({ value, label, className = '' }: { value: number; label: string; className?: string }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className={`progress ${className}`} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(clamped)}>
      <motion.div
        className="progress__bar"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: clamped / 100 }}
        transition={{ duration: 0.6, ease: EASE_OUT }}
      />
    </div>
  )
}

/** A circular score that draws itself. */
export function Ring({ value, size = 160, stroke = 12, children }: { value: number; size?: number; stroke?: number; children?: ReactNode }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const [target, setTarget] = useState(0)
  useEffect(() => { setTarget(Math.max(0, Math.min(100, value))) }, [value])
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} aria-hidden="true">
        <circle className="ring__track" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} />
        <motion.circle
          className="ring__value"
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - target / 100) }}
          transition={{ duration: 1.1, ease: EASE_OUT, delay: 0.15 }}
        />
      </svg>
      <div className="ring__label">{children}</div>
    </div>
  )
}
