import type { AccuseResult } from '../../api'
import Overlay from './Overlay'

interface Props {
  result: AccuseResult
  onReplay: () => void
  onExit: () => void
}

export default function RevealOverlay({ result, onReplay, onExit }: Props) {
  return (
    <Overlay>
      <div className="reveal-overlay">
        <p className="intro-title">真相揭晓</p>
        <div className="verdict-row">
          <span className={result.outcome.killer_correct ? 'ok' : 'bad'}>
            凶手判定 {result.outcome.killer_correct ? '✓ 正确' : '✗ 错误'}
          </span>
          <span className={result.outcome.motive_correct ? 'ok' : 'bad'}>
            动机判定 {result.outcome.motive_correct ? '✓ 正确' : '✗ 错误'}
          </span>
        </div>
        <p className="reveal-text">{result.reveal}</p>
        <div className="modal-actions">
          <button onClick={onExit}>回到大厅</button>
          <button className="primary" onClick={onReplay}>查看复盘报告 →</button>
        </div>
      </div>
    </Overlay>
  )
}
