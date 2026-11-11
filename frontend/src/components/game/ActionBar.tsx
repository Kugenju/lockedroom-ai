import type { LayoutConfig } from '../../game/layout'

interface Props {
  layout: LayoutConfig
  clueCount: number
  onStart: () => void
  onToInvestigation: () => void
  onAccuse: () => void
}

export default function ActionBar(p: Props) {
  return (
    <footer className="actionbar">
      {p.layout.action === 'start' && (
        <button className="primary big" onClick={p.onStart}>
          开始游戏 · 角色登场
        </button>
      )}
      {p.layout.action === 'to_investigation' && (
        <button
          className="primary big"
          disabled={p.clueCount === 0}
          onClick={p.onToInvestigation}
          title={p.clueCount === 0 ? '建议先搜集至少一条线索' : ''}
        >
          {p.clueCount === 0 ? '先搜集线索再开始调查' : '进入自由调查'}
        </button>
      )}
      {p.layout.action === 'accuse' && (
        <button className="danger big" onClick={p.onAccuse}>
          指认真凶
        </button>
      )}
    </footer>
  )
}
