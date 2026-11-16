import { useState } from 'react'
import { api, type NoteItem } from '../../api'

interface Props {
  gameId: string
  notes: NoteItem[]
  charName: (id: string | null) => string
  onChange: (notes: NoteItem[]) => void
}

export default function NotesPanel({ gameId, notes, charName, onChange }: Props) {
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)

  const add = async () => {
    const content = draft.trim()
    if (!content || busy) return
    setBusy(true)
    try {
      await api.addNote(gameId, content)
      setDraft('')
      onChange((await api.getNotes(gameId)).notes)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (noteId: string) => {
    await api.deleteNote(gameId, noteId)
    onChange((await api.getNotes(gameId)).notes)
  }

  return (
    <div className="notespanel">
      <h3>推理笔记（{notes.length}）</h3>
      <p className="hint">高价值发言会自动钉到这里，也可以自己记。</p>
      <div className="note-add">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder="记一条笔记…（Enter 保存）"
        />
        <button disabled={busy || !draft.trim()} onClick={add}>记</button>
      </div>
      <ul className="note-list">
        {notes.map((n) => (
          <li key={n.note_id} className={n.source === 'auto' ? 'note auto' : 'note'}>
            <div className="note-head">
              <span className="note-source">
                {n.source === 'auto' ? `📌 ${charName(n.char_id)}` : '✍️ 我'}
              </span>
              {n.importance != null && n.source === 'auto' && (
                <span className="note-importance">重要性 {n.importance}</span>
              )}
              <button className="link note-del" onClick={() => remove(n.note_id)}>删</button>
            </div>
            <p>{n.content}</p>
          </li>
        ))}
        {notes.length === 0 && <p className="hint">还没有笔记。</p>}
      </ul>
    </div>
  )
}
