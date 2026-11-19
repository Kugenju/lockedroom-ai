import { useEffect, useRef, useState } from 'react'
import { api, streamDiscussionSpeak, type CharacterSummary, type DiscussionMessage } from '../../api'
import Avatar from './Avatar'

interface Props {
  gameId: string
  characters: CharacterSummary[] // includes the player's seat
  playerSeat: string
  onError: (msg: string | null) => void
}

export default function DiscussionView({ gameId, characters, playerSeat, onError }: Props) {
  const [thread, setThread] = useState<DiscussionMessage[]>([])
  const [input, setInput] = useState('')
  const [speaking, setSpeaking] = useState<{ id: string; text: string } | null>(null)
  const [roundRunning, setRoundRunning] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)

  const aiSeats = characters.filter((c) => c.id !== playerSeat)
  const nameOf = (id: string) => characters.find((c) => c.id === id)?.name ?? id

  useEffect(() => {
    api.getDiscussion(gameId).then((r) => setThread(r.messages)).catch(() => {})
  }, [gameId])

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight })
  }, [thread, speaking])

  const say = async () => {
    const text = input.trim()
    if (!text) return
    setInput('')
    onError(null)
    try {
      const r = await api.sayDiscussion(gameId, text)
      setThread(r.messages)
    } catch (e) {
      onError(`发言失败：${(e as Error).message}`)
    }
  }

  const advanceRound = async () => {
    if (roundRunning) return
    setRoundRunning(true)
    onError(null)
    try {
      for (const seat of aiSeats) {
        setSpeaking({ id: seat.id, text: '' })
        let final = ''
        for await (const ev of streamDiscussionSpeak(gameId, seat.id)) {
          if (ev.type === 'token') {
            final += ev.chunk
            setSpeaking({ id: seat.id, text: final })
          } else {
            final = ev.reply
          }
        }
        setThread(await api.getDiscussion(gameId).then((r) => r.messages))
        setSpeaking(null)
      }
    } catch (e) {
      onError(`讨论失败：${(e as Error).message}`)
    } finally {
      setSpeaking(null)
      setRoundRunning(false)
    }
  }

  return (
    <section className="chatview discussion">
      <header className="chatview-head">
        <h3>公开讨论</h3>
        <small>全员在场 · 你的发言和 AI 的发言彼此可见</small>
        <span className="shell-spacer" />
        <button className="primary" disabled={roundRunning} onClick={advanceRound}>
          {roundRunning ? '讨论进行中…' : '推进一轮讨论'}
        </button>
      </header>
      <div className="chatview-body" ref={bodyRef}>
        {thread.length === 0 && !speaking && (
          <p className="hint center">还没有人发言。点击"推进一轮讨论"开始，或直接发言。</p>
        )}
        {thread.map((m, i) => (
          <div key={i} className={`msg ${m.sender === 'player' ? 'player' : 'character'}`}>
            {m.sender !== 'player' && (
              <div className="msg-sender">
                <Avatar id={m.sender} name={m.sender_name} size={24} />
                <span>{m.sender_name}</span>
              </div>
            )}
            <div className="bubble">{m.content}</div>
          </div>
        ))}
        {speaking && (
          <div className="msg character">
            <div className="msg-sender">
              <Avatar id={speaking.id} name={nameOf(speaking.id)} size={24} />
              <span>{nameOf(speaking.id)}</span>
            </div>
            <div className="bubble typing">
              {speaking.text || '思考中…'}
              <span className="cursor">▍</span>
            </div>
          </div>
        )}
      </div>
      <footer className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              say()
            }
          }}
          placeholder="公开发言…（Enter 发送，全员可见）"
        />
        <button className="primary" disabled={!input.trim() || roundRunning} onClick={say}>
          发言
        </button>
      </footer>
    </section>
  )
}
