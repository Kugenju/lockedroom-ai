import type { RoleCard } from '../../api'
import Avatar from './Avatar'
import Overlay from './Overlay'

interface Props {
  card: RoleCard
  firstTime?: boolean
  onClose: () => void
}

export default function RoleCardOverlay({ card, firstTime, onClose }: Props) {
  return (
    <Overlay>
      <div className="rolecard">
        <p className="intro-title">{firstTime ? '你的身份' : '角色卡'}</p>
        <div className="rolecard-head">
          <Avatar id={card.character.id} name={card.character.name} size={64} />
          <div>
            <h2>{card.character.name}</h2>
            <small>{card.character.role}</small>
            <p className="rolecard-profile">{card.public_profile}</p>
          </div>
        </div>
        <section className="rolecard-secrets">
          <h4>只有你知道的事</h4>
          {card.secrets.length === 0 && <p className="hint">你没有不可告人的秘密。</p>}
          <ul>
            {card.secrets.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </section>
        <p className="hint">说话风格建议：{card.speaking_style || '自由发挥'}</p>
        <div className="modal-actions">
          <button className="primary" onClick={onClose}>
            {firstTime ? '记住身份，开始游戏 →' : '收起'}
          </button>
        </div>
      </div>
    </Overlay>
  )
}
