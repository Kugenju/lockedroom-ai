import { PHASE_STEPS, stepIndex } from '../../game/layout'

export default function PhaseProgress({ phase }: { phase: string }) {
  const current = stepIndex(phase)
  return (
    <ol className="phase-progress">
      {PHASE_STEPS.map((s, i) => (
        <li
          key={s.phase}
          className={i < current ? 'done' : i === current ? 'current' : 'todo'}
        >
          <span className="dot">{i < current ? '✓' : i + 1}</span>
          <span className="label">{s.label}</span>
        </li>
      ))}
    </ol>
  )
}
