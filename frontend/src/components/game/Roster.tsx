import type { CharacterSummary } from '../../api'
import Avatar from './Avatar'

interface Props {
  characters: CharacterSummary[]
  activeChar: string
  onSelect: (id: string) => void
}

export default function Roster({ characters, activeChar, onSelect }: Props) {
  return (
    <aside className="roster">
      <h3>角色名册</h3>
      <ul>
        {characters.map((c) => (
          <li key={c.id}>
            <button
              className={c.id === activeChar ? 'roster-card active' : 'roster-card'}
              onClick={() => onSelect(c.id)}
            >
              <Avatar id={c.id} name={c.name} size={38} dim={c.id !== activeChar} />
              <span className="roster-meta">
                <strong>{c.name}</strong>
                <small>{c.role}</small>
              </span>
              {c.id === activeChar && <span className="roster-flag">询问中</span>}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
