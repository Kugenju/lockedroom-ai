import type { ReactNode } from 'react'

/** Full-screen overlay — the cinematic layer for phase transitions. */
export default function Overlay({ children }: { children: ReactNode }) {
  return (
    <div className="overlay-mask">
      <div className="overlay-card">{children}</div>
    </div>
  )
}
