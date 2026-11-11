import { useEffect, useState } from 'react'
import { api, type CharacterSummary, type MotiveOption } from '../../api'
import Avatar from './Avatar'
import Overlay from './Overlay'

interface Props {
  gameId: string
  characters: CharacterSummary[]
  onCancel: () => void
  onConfirm: (suspectId: string, motiveFactId: string | null) => void
}

export default function AccuseDialog({ gameId, characters, onCancel, onConfirm }: Props) {
  const [suspect, setSuspect] = useState('')
  const [motive, setMotive] = useState<string | null>(null)
  const [options, setOptions] = useState<MotiveOption[]>([])

  useEffect(() => {
    api
      .getMotiveOptions(gameId)
      .then((r) => {
        setOptions(r.options)
        setMotive(r.options[0]?.fact_id ?? null)
      })
      .catch(() => {})
  }, [gameId])

  return (
    <Overlay>
      <div className="accuse-dialog">
        <h3>最终指认</h3>
        <p className="hint">指认后将对局结算，无法撤回。</p>
        <h4>谁是凶手？</h4>
        <div className="options">
          {characters.map((c) => (
            <label key={c.id} className={suspect === c.id ? 'option selected' : 'option'}>
              <input
                type="radio"
                name="suspect"
                checked={suspect === c.id}
                onChange={() => setSuspect(c.id)}
              />
              <Avatar id={c.id} name={c.name} size={30} />
              <span>
                {c.name} <small>{c.role}</small>
              </span>
            </label>
          ))}
        </div>
        <h4>动机是什么？</h4>
        <p className="hint">动机选项仅来自你已搜获的线索——找到动机证据才能指认动机。</p>
        <div className="options">
          {options.map((o, i) => (
            <label
              key={o.fact_id ?? `unsure-${i}`}
              className={motive === o.fact_id ? 'option selected' : 'option'}
            >
              <input
                type="radio"
                name="motive"
                checked={motive === o.fact_id}
                onChange={() => setMotive(o.fact_id)}
              />
              {o.statement}
            </label>
          ))}
        </div>
        <div className="modal-actions">
          <button onClick={onCancel}>再想想</button>
          <button className="danger" disabled={!suspect} onClick={() => onConfirm(suspect, motive)}>
            提交指认
          </button>
        </div>
      </div>
    </Overlay>
  )
}
