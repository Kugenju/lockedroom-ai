import type { RoleCard } from '../../api'
import Avatar from './Avatar'
import Overlay from './Overlay'

interface Props {
  card: RoleCard
  firstTime?: boolean
  onClose: () => void
}

/** 我的剧本 — the player's private script: backstory, timeline, goals, secrets. */
export default function RoleCardOverlay({ card, firstTime, onClose }: Props) {
  return (
    <Overlay>
      <div className="rolecard">
        <p className="intro-title">{firstTime ? '你的剧本' : '我的剧本'}</p>
        <div className="rolecard-head">
          <Avatar id={card.character.id} name={card.character.name} size={64} />
          <div>
            <h2>{card.character.name}</h2>
            <small>{card.character.role}</small>
            <p className="rolecard-profile">{card.public_profile}</p>
          </div>
        </div>

        {card.backstory && (
          <section className="rolecard-section">
            <h4>背景故事</h4>
            <p className="rolecard-story">{card.backstory}</p>
          </section>
        )}

        {card.timeline.length > 0 && (
          <section className="rolecard-section">
            <h4>你的昨晚（时间线）</h4>
            <ul className="rolecard-timeline">
              {card.timeline.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </section>
        )}

        {card.goals.length > 0 && (
          <section className="rolecard-section goals">
            <h4>你的本局目标</h4>
            <ol className="rolecard-goals">
              {card.goals.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ol>
          </section>
        )}

        <section className="rolecard-secrets">
          <h4>只有你知道的事</h4>
          {card.secrets.length === 0 && <p className="hint">你没有不可告人的秘密。</p>}
          <ul>
            {card.secrets.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>

        {card.speaking_style && <p className="hint">说话风格建议：{card.speaking_style}</p>}
        <div className="modal-actions">
          <button className="primary" onClick={onClose}>
            {firstTime ? '读完剧本，开始游戏 →' : '收起'}
          </button>
        </div>
      </div>
    </Overlay>
  )
}
