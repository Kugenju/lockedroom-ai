import { useState } from 'react'
import type { ClueSummary, NoteItem } from '../../api'
import ClueBoard from '../ClueBoard'
import NotesPanel from './NotesPanel'

interface Props {
  brief: string
  gameId: string
  clues: ClueSummary[]
  onClues: (clues: ClueSummary[]) => void
  notes: NoteItem[]
  onNotes: (notes: NoteItem[]) => void
  charName: (id: string | null) => string
  collapsed: boolean
  onToggle: () => void
}

export default function CaseFile(p: Props) {
  const [briefOpen, setBriefOpen] = useState(true)
  const [tab, setTab] = useState<'clues' | 'notes'>('clues')

  if (p.collapsed) {
    return (
      <button className="casefile-rail" onClick={p.onToggle} title="展开案件档案">
        案件档案 ▸
      </button>
    )
  }

  return (
    <aside className="casefile">
      <div className="casefile-head">
        <h3>案件档案</h3>
        <button className="link" onClick={p.onToggle} title="收起">◂ 收起</button>
      </div>
      <section className="case-brief">
        <button className="brief-toggle" onClick={() => setBriefOpen(!briefOpen)}>
          <h4>案情简介</h4>
          <span>{briefOpen ? '▾' : '▸'}</span>
        </button>
        {briefOpen && <p>{p.brief}</p>}
      </section>
      <div className="casefile-tabs">
        <button className={tab === 'clues' ? 'active' : ''} onClick={() => setTab('clues')}>
          线索
        </button>
        <button className={tab === 'notes' ? 'active' : ''} onClick={() => setTab('notes')}>
          笔记
        </button>
      </div>
      {tab === 'clues' ? (
        <ClueBoard gameId={p.gameId} clues={p.clues} onClues={p.onClues} compact />
      ) : (
        <NotesPanel gameId={p.gameId} notes={p.notes} charName={p.charName} onChange={p.onNotes} />
      )}
    </aside>
  )
}
