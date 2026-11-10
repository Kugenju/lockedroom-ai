import type { CharacterSummary } from '../api'

export interface Msg {
  sender: 'player' | 'character' | 'system'
  charId?: string
  text: string
  rewritten?: boolean
  fellBack?: boolean
  leakCount?: number
}

interface Props {
  characters: CharacterSummary[]
  messages: Msg[]
  activeChar: string
  onSelectChar: (id: string) => void
  input: string
  onInput: (v: string) => void
  onSend: () => void
  streaming: boolean
  streamText: string
  streamChar: string
  readOnly?: boolean
}

export default function ChatPanel(p: Props) {
  const nameOf = (id?: string) => p.characters.find((c) => c.id === id)?.name ?? ''
  return (
    <div className="chat">
      <div className="char-tabs">
        {p.characters.map((c) => (
          <button
            key={c.id}
            className={c.id === p.activeChar ? 'tab active' : 'tab'}
            title={c.personality}
            onClick={() => p.onSelectChar(c.id)}
          >
            {c.name}
            <small>{c.role}</small>
          </button>
        ))}
      </div>
      <div className="messages">
        {p.messages.map((m, i) => (
          <div key={i} className={`msg ${m.sender}`}>
            {m.sender !== 'player' && <div className="msg-name">{m.sender === 'system' ? '主持人' : nameOf(m.charId)}</div>}
            <div className="bubble">{m.text}</div>
            {m.sender === 'character' && (m.rewritten || m.fellBack) && (
              <div className="infoguard-badge">
                {m.fellBack
                  ? 'InfoGuard：多次触发泄露检测，已降级为安全回复'
                  : 'InfoGuard：原回复触发泄露检测，已现场重写'}
              </div>
            )}
          </div>
        ))}
        {p.streaming && (
          <div className="msg character">
            <div className="msg-name">{nameOf(p.streamChar)}</div>
            <div className="bubble typing">
              {p.streamText || '思考中…'}
              <span className="cursor">▍</span>
            </div>
          </div>
        )}
      </div>
      {!p.readOnly && (
        <div className="composer">
          <textarea
            value={p.input}
            onChange={(e) => p.onInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                p.onSend()
              }
            }}
            placeholder={`向 ${nameOf(p.activeChar)} 提问…（Enter 发送）`}
          />
          <button className="primary" disabled={p.streaming || !p.input.trim()} onClick={p.onSend}>
            发送
          </button>
        </div>
      )}
    </div>
  )
}
