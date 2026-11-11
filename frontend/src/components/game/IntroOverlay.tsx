import type { CharacterSummary } from '../../api'
import Avatar from './Avatar'
import Overlay from './Overlay'

interface Props {
  characters: CharacterSummary[]
  idx: number
  streamText: string
  ready: boolean
  onNext: () => void
  onSkip: () => void
}

/** Cinematic character entrance sequence, paced by player clicks. */
export default function IntroOverlay({ characters, idx, streamText, ready, onNext, onSkip }: Props) {
  const c = characters[idx]
  const last = idx === characters.length - 1
  return (
    <Overlay>
      <div className="intro-overlay">
        <p className="intro-title">角色登场 · {idx + 1} / {characters.length}</p>
        <div className="intro-card">
          <Avatar id={c.id} name={c.name} size={72} />
          <h2>{c.name}</h2>
          <small>{c.role} · {c.personality}</small>
          <p className="intro-speech">{streamText || '……'}</p>
        </div>
        <div className="intro-dots">
          {characters.map((ch, i) => (
            <span key={ch.id} className={i === idx ? 'dot active' : i < idx ? 'dot done' : 'dot'} />
          ))}
        </div>
        <div className="intro-actions">
          <button className="link" onClick={onSkip}>跳过登场 ›</button>
          <button className="primary" disabled={!ready} onClick={onNext}>
            {last ? '完成登场，开始搜证 →' : '下一位 →'}
          </button>
        </div>
      </div>
    </Overlay>
  )
}
