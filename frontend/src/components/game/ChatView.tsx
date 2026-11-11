import { useEffect, useRef, useState } from 'react'
import type { CharacterSummary } from '../../api'
import Avatar from './Avatar'

export interface Msg {
  from: 'player' | 'character'
  text: string
  rewritten?: boolean
  fellBack?: boolean
}

interface Props {
  character: CharacterSummary
  messages: Msg[]
  composer: boolean
  input: string
  onInput: (v: string) => void
  onSend: () => void
  sending: boolean
  streamText: string
}

export default function ChatView(p: Props) {
  const boxRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)

  const handleScroll = () => {
    const el = boxRef.current
    if (!el) return
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80)
  }

  // auto-follow only when the user is already near the bottom
  useEffect(() => {
    const el = boxRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
  }, [p.messages, p.streamText, atBottom])

  const historyHint =
    p.messages.length === 0
      ? p.composer
        ? `开始询问${p.character.name}吧。`
        : '尚无对话。'
      : null

  return (
    <section className="chatview">
      <header className="chatview-head">
        <Avatar id={p.character.id} name={p.character.name} size={44} />
        <div>
          <h3>{p.character.name}</h3>
          <small>
            {p.character.role} · {p.character.personality}
          </small>
        </div>
      </header>
      <div className="chatview-body" ref={boxRef} onScroll={handleScroll}>
        {historyHint && <p className="hint center">{historyHint}</p>}
        {p.messages.map((m, i) => (
          <div key={i} className={`msg ${m.from}`}>
            <div className="bubble">{m.text}</div>
            {m.from === 'character' && (m.rewritten || m.fellBack) && (
              <div className="infoguard-badge">
                {m.fellBack
                  ? 'InfoGuard：多次触发泄露检测，已降级为安全回复'
                  : 'InfoGuard：原回复触发泄露检测，已现场重写'}
              </div>
            )}
          </div>
        ))}
        {p.streamText && (
          <div className="msg character">
            <div className="bubble typing">
              {p.streamText}
              <span className="cursor">▍</span>
            </div>
          </div>
        )}
      </div>
      {p.composer && (
        <footer className="composer">
          <textarea
            value={p.input}
            onChange={(e) => p.onInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                p.onSend()
              }
            }}
            placeholder={`向 ${p.character.name} 提问…（Enter 发送）`}
          />
          <button className="primary" disabled={p.sending || !p.input.trim()} onClick={p.onSend}>
            发送
          </button>
        </footer>
      )}
    </section>
  )
}
