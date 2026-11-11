import { useState } from 'react'
import type { ClueSummary } from '../../api'
import ClueBoard from '../ClueBoard'

interface Props {
  brief: string
  gameId: string
  clues: ClueSummary[]
  onClues: (clues: ClueSummary[]) => void
  collapsed: boolean
  onToggle: () => void
}

export default function CaseFile({ brief, gameId, clues, onClues, collapsed, onToggle }: Props) {
  const [briefOpen, setBriefOpen] = useState(true)

  if (collapsed) {
    return (
      <button className="casefile-rail" onClick={onToggle} title="展开案件档案">
        案件档案 ▸
      </button>
    )
  }

  return (
    <aside className="casefile">
      <div className="casefile-head">
        <h3>案件档案</h3>
        <button className="link" onClick={onToggle} title="收起">◂ 收起</button>
      </div>
      <section className="case-brief">
        <button className="brief-toggle" onClick={() => setBriefOpen(!briefOpen)}>
          <h4>案情简介</h4>
          <span>{briefOpen ? '▾' : '▸'}</span>
        </button>
        {briefOpen && <p>{brief}</p>}
      </section>
      <ClueBoard gameId={gameId} clues={clues} onClues={onClues} compact />
    </aside>
  )
}
