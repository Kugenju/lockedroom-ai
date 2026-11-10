import { useEffect, useState } from 'react'
import { api, type ClueSummary, type LocationInfo } from '../api'

interface Props {
  gameId: string
  clues: ClueSummary[]
  onClues: (clues: ClueSummary[]) => void
  compact?: boolean
}

export default function ClueBoard({ gameId, clues, onClues, compact }: Props) {
  const [locations, setLocations] = useState<LocationInfo[]>([])
  const [note, setNote] = useState<string | null>(null)

  useEffect(() => {
    api
      .getLocations(gameId)
      .then((r) => {
        // tolerate older backends returning plain string locations
        const list = (r.locations as unknown[]).map((l) =>
          typeof l === 'string' ? { location: l, total: 1, unlocked: 0 } : (l as LocationInfo),
        )
        setLocations(list)
      })
      .catch(() => {})
  }, [gameId])

  const search = async (location: string) => {
    setNote(null)
    try {
      const r = await api.search(gameId, location)
      onClues((await api.getClues(gameId)).clues)
      setLocations((await api.getLocations(gameId)).locations)
      setNote(r.unlocked.length ? `搜获：${r.unlocked.map((c) => c.title).join('、')}` : '这里没有新发现了。')
    } catch (e) {
      setNote(`搜证失败：${(e as Error).message}`)
    }
  }

  return (
    <div className={compact ? 'clueboard compact' : 'clueboard'}>
      <h3>线索板（{clues.length}）</h3>
      <p className="hint">点击地点搜证（数字=已搜/总数），与对话互不前置，随时可搜。</p>
      <div className="loc-chips">
        {locations.map((loc) => {
          const done = loc.unlocked >= loc.total
          return (
            <button
              key={loc.location}
              className={done ? 'chip done' : 'chip'}
              disabled={done}
              onClick={() => search(loc.location)}
            >
              {loc.location} {done ? '✓' : `${loc.unlocked}/${loc.total}`}
            </button>
          )
        })}
      </div>
      {note && <p className="hint">{note}</p>}
      <ul className="clue-list">
        {clues.map((c) => (
          <li key={c.id}>
            <strong>{c.title}</strong>
            <span className="clue-loc">{c.location}</span>
            <p>{c.description}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
