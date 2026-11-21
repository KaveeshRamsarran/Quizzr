import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

/** A two-sided card that turns over in 3D. Reduced motion swaps faces with a crossfade. */
export default function FlipCard({
  flipped, front, back, onFlip, label = 'Flashcard',
}: { flipped: boolean; front: ReactNode; back: ReactNode; onFlip?: () => void; label?: string }) {
  return (
    <div className="flip">
      <motion.div
        className="flip__inner"
        initial={false}
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ type: 'spring', stiffness: 220, damping: 26, mass: 0.9 }}
      >
        <button
          type="button"
          className="flip__face"
          onClick={onFlip}
          aria-label={`${label}: show the answer`}
          aria-hidden={flipped}
          tabIndex={flipped ? -1 : 0}
          style={{ border: 0, textAlign: 'inherit', cursor: onFlip ? 'pointer' : 'default', font: 'inherit' }}
        >
          {front}
        </button>
        <div className="flip__face flip__face--back" aria-hidden={!flipped} onClick={onFlip} style={{ cursor: onFlip ? 'pointer' : 'default' }}>
          {back}
        </div>
      </motion.div>
    </div>
  )
}
