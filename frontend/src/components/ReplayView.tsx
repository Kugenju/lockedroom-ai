import { useEffect, useState } from 'react'
import { api, type ChainData, type GameEvent, type ReplayData } from '../api'

export default function ReplayView({ gameId, title, onBack }: { gameId: string; title: string; onBack: () => void }) {
  const [data, setData] = useState<ReplayData | null>(null)
  const [chain, setChain] = useState<ChainData | null>(null)
  const [report, setReport] = useState<string | null>(null)
  const [tab, setTab] = useState<'timeline' | 'metrics'>('timeline')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getReplay(gameId).then(setData).catch((e) => setError(e.message))
  }, [gameId])

  const loadChain = async () => {
    setError(null)
    try {
      setChain(await api.getChain(gameId))
    } catch (e) {
      setError(`推理链生成失败：${(e as Error).message}`)
    }
  }

  const loadReport = async () => {
    setError(null)
    try {
      setReport(await api.getReport(gameId))
    } catch (e) {
      setError(`报告生成失败：${(e as Error).message}`)
    }
  }

  return (
    <main className="replay">
      <div className="game-topbar">
        <h2>复盘 · {title}</h2>
        <button className="link" onClick={onBack}>← 返回大厅</button>
      </div>
      {error && <p className="error">{error}</p>}
      {!data && <p className="hint">加载中…</p>}
      {data && (
        <>
          <div className="replay-actions">
            <button className={tab === 'timeline' ? 'primary' : ''} onClick={() => setTab('timeline')}>时间线</button>
            <button className={tab === 'metrics' ? 'primary' : ''} onClick={() => setTab('metrics')}>指标</button>
            <button onClick={loadChain}>生成推理链</button>
            <button onClick={loadReport}>生成报告</button>
          </div>

          {tab === 'timeline' && (
            <ul className="timeline">
              {data.events.map((e) => {
                const line = eventLine(e)
                return line ? (
                  <li key={e.seq} className={`tl-${e.type}`}>
                    <span className="tl-icon">{line.icon}</span>
                    <span className="tl-text">{line.text}</span>
                  </li>
                ) : null
              })}
            </ul>
          )}

          {tab === 'metrics' && <MetricsPanel data={data} />}

          {chain && (
            <section className="panel">
              <h3>推理链</h3>
              {chain.suspect_trajectory.length > 0 && (
                <>
                  <h4>怀疑轨迹</h4>
                  <ol>{chain.suspect_trajectory.map((s, i) => <li key={i}>{s}</li>)}</ol>
                </>
              )}
              {chain.key_insights.length > 0 && (
                <>
                  <h4>关键洞察</h4>
                  <ul>{chain.key_insights.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
              {chain.missed_clues.length > 0 && (
                <>
                  <h4>遗漏线索</h4>
                  <ul>{chain.missed_clues.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </>
              )}
              <blockquote>{chain.summary}</blockquote>
            </section>
          )}

          {report && <pre className="report">{report}</pre>}
        </>
      )}
    </main>
  )
}

function MetricsPanel({ data }: { data: ReplayData }) {
  const m = data.metrics
  const pct = (v: number) => `${Math.round(v * 100)}%`
  return (
    <section className="panel">
      <h3>
        综合评分：<span className="grade">{m.grade}</span>（{m.score} 分 / 剧本难度 {m.difficulty}）
      </h3>
      <table className="metrics-table">
        <tbody>
          <tr><td>关键线索覆盖率</td><td><Bar value={m.clue_coverage} /> {pct(m.clue_coverage)}（{m.clues_unlocked} 条线索）</td></tr>
          <tr><td>加权泄露率</td><td><Bar value={Math.min(m.leak_rate, 1)} warn={m.leak_rate > 0.3} /> {m.leak_rate}（硬 {m.hard_leaks} / 软 {m.soft_leaks}）</td></tr>
          <tr><td>凶手判定</td><td>{m.killer_correct ? '✓ 正确' : '✗ 错误'}</td></tr>
          <tr><td>动机判定</td><td>{m.motive_correct ? '✓ 正确' : '✗ 错误'}</td></tr>
          <tr><td>提问 / 回复</td><td>{m.player_questions} / {m.character_replies}</td></tr>
        </tbody>
      </table>
    </section>
  )
}

function Bar({ value, warn }: { value: number; warn?: boolean }) {
  return (
    <span className={warn ? 'bar warn' : 'bar'}>
      <span style={{ width: `${Math.round(value * 100)}%` }} />
    </span>
  )
}

function eventLine(e: GameEvent): { icon: string; text: string } | null {
  const p = e.payload as Record<string, any>
  switch (e.type) {
    case 'phase_change':
      return { icon: '⏩', text: `阶段推进：${p.from} → ${p.to}` }
    case 'message': {
      const content = String(p.content ?? '').slice(0, 80)
      if (p.sender === 'player') return { icon: '❓', text: `玩家 → ${p.recipient}：${content}` }
      if (p.sender === 'narrator') return { icon: '📜', text: '主持人发言' }
      return { icon: '💬', text: `${p.sender}：${content}` }
    }
    case 'clue_unlocked':
      return { icon: '🔍', text: `搜获线索：${p.title ?? p.clue_id}` }
    case 'leak_detected':
      return { icon: '⚠️', text: `泄露（${p.severity}）：${p.character_id} 触及 ${p.fact_id}，已${p.action}` }
    case 'player_action':
      if (p.action === 'accuse') return { icon: '🎯', text: `玩家指认：${p.detail?.suspect_id}` }
      return null
    case 'system':
      return p.kind === 'reveal' ? { icon: '📖', text: '真相揭晓' } : null
    default:
      return null
  }
}
