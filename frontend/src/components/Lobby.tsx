import { useEffect, useState } from 'react'
import { api, type GameInfo } from '../api'

export default function Lobby({ onStart }: { onStart: (game: GameInfo) => void }) {
  const [scripts, setScripts] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .listScripts()
      .then((r) => setScripts(r.scripts))
      .catch((e) => setError(`无法连接后端：${e.message}`))
  }, [])

  const start = async (scriptId: string) => {
    setBusy(true)
    setError(null)
    try {
      onStart(await api.createGame(scriptId))
    } catch (e) {
      setError(`创建对局失败：${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="lobby">
      <h2>选择剧本</h2>
      {error && <p className="error">{error}</p>}
      <div className="script-list">
        {scripts.map((s) => (
          <button key={s} className="script-card" disabled={busy} onClick={() => start(s)}>
            <span className="script-name">{s}</span>
            <span className="script-cta">{busy ? '创建中…' : '开局 →'}</span>
          </button>
        ))}
        {scripts.length === 0 && !error && <p>加载中…</p>}
      </div>
    </main>
  )
}
