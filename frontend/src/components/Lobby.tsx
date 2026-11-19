import { useEffect, useState } from 'react'
import { api, type GameInfo, type ScriptDetail } from '../api'
import Avatar from './game/Avatar'

interface SeatInfo {
  id: string
  name: string
  role: string
  personality: string
}

export default function Lobby({ onStart }: { onStart: (game: GameInfo) => void }) {
  const [details, setDetails] = useState<ScriptDetail[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // two-step flow for roleplay scripts: pick script → pick seat → create
  const [pending, setPending] = useState<ScriptDetail | null>(null)
  const [seat, setSeat] = useState('')

  useEffect(() => {
    api
      .listScripts()
      .then((r) => setDetails(r.details))
      .catch((e) => setError(`无法连接后端：${e.message}`))
  }, [])

  const start = async (script: ScriptDetail, playerSeat: string | null) => {
    setBusy(true)
    setError(null)
    try {
      onStart(await api.createGame(script.id, playerSeat))
    } catch (e) {
      setError(`创建对局失败：${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  const clickScript = (s: ScriptDetail) => {
    if (s.player_selectable.length > 0) {
      setSeat('')
      setPending(s)
    } else {
      start(s, null)
    }
  }

  const seats: SeatInfo[] = pending?.characters ?? []

  return (
    <main className="lobby">
      <h2>选择剧本</h2>
      {error && <p className="error">{error}</p>}
      {!pending && (
        <div className="script-list">
          {details.map((s) => (
            <button key={s.id} className="script-card" disabled={busy} onClick={() => clickScript(s)}>
              <span className="script-name">{s.title}</span>
              <span className="script-cta">
                {s.player_selectable.length > 0 ? '选座开局 →' : busy ? '创建中…' : '开局 →'}
              </span>
            </button>
          ))}
          {details.length === 0 && !error && <p>加载中…</p>}
        </div>
      )}

      {pending && (
        <section className="panel seat-picker">
          <h3>《{pending.title}》· 选择你的座位</h3>
          <p className="hint">你将亲自扮演所选角色——你的秘密只有你自己知道。</p>
          <div className="seat-grid">
            {seats.map((c) => (
              <button
                key={c.id}
                className={seat === c.id ? 'seat-card selected' : 'seat-card'}
                disabled={!pending.player_selectable.includes(c.id)}
                onClick={() => setSeat(c.id)}
              >
                <Avatar id={c.id} name={c.name} size={44} />
                <strong>{c.name}</strong>
                <small>{c.role}</small>
                <em>{c.personality}</em>
                {!pending.player_selectable.includes(c.id) && <span className="seat-locked">不可选</span>}
              </button>
            ))}
          </div>
          <div className="modal-actions">
            <button onClick={() => setPending(null)}>← 返回</button>
            <button className="primary" disabled={!seat || busy} onClick={() => start(pending, seat)}>
              以 {seat ? seats.find((c) => c.id === seat)?.name : '…'} 的身份开局
            </button>
          </div>
        </section>
      )}
    </main>
  )
}
