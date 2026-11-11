// Game layout configuration — the extension point for future gameplay modes.
// New modes (roleplay / faction / ...) register their own phase→layout mappings
// and panel components without touching the shell.

export interface PhaseStep {
  phase: string
  label: string
}

export const PHASE_STEPS: PhaseStep[] = [
  { phase: 'intro', label: '背景' },
  { phase: 'self_intro', label: '登场' },
  { phase: 'evidence', label: '搜证' },
  { phase: 'investigation', label: '调查' },
  { phase: 'accusation', label: '指认' },
  { phase: 'reveal', label: '真相' },
]

export function stepIndex(phase: string): number {
  const i = PHASE_STEPS.findIndex((s) => s.phase === phase)
  return i === -1 ? PHASE_STEPS.length - 1 : i
}

export type CenterView = 'brief' | 'chat'

export interface LayoutConfig {
  center: CenterView
  composer: boolean
  roster: boolean
  casefile: boolean
  /** primary action button in the bottom bar for this phase */
  action: 'start' | 'to_investigation' | 'accuse' | 'none'
}

const INVESTIGATION_LAYOUT: Record<string, LayoutConfig> = {
  intro: { center: 'brief', composer: false, roster: false, casefile: false, action: 'start' },
  self_intro: { center: 'chat', composer: false, roster: true, casefile: false, action: 'none' },
  evidence: { center: 'chat', composer: false, roster: true, casefile: true, action: 'to_investigation' },
  investigation: { center: 'chat', composer: true, roster: true, casefile: true, action: 'accuse' },
  accusation: { center: 'chat', composer: false, roster: true, casefile: true, action: 'none' },
  reveal: { center: 'chat', composer: false, roster: true, casefile: true, action: 'none' },
  ended: { center: 'chat', composer: false, roster: true, casefile: true, action: 'none' },
}

export function getLayout(mode: string, phase: string): LayoutConfig {
  // Future modes (roleplay / faction) get their own layout tables, e.g.:
  //   if (mode === 'roleplay') return ROLEPLAY_LAYOUT[phase] ?? FALLBACK
  // Until then every mode falls back to the investigation layout.
  void mode // reserved for mode-specific layouts
  return INVESTIGATION_LAYOUT[phase] ?? INVESTIGATION_LAYOUT['investigation']
}
