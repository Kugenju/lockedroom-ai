import { useEffect, useRef, useState } from 'react'
import { api, type AccuseResult, type ClueSummary, type GameInfo } from '../api'
import { streamTalk } from '../sse'
import ChatPanel, { type Msg } from './ChatPanel'
import ClueBoard from './ClueBoard'
import AccuseDialog from './AccuseDialog'

interface Props {
  game: GameInfo
  onExit: () => void
  onReplay: (gameId: string, title: string) => void
}

export default function GameView({ game, onExit, onReplay }: Props) {
  const [phase, setPhase] = useState(game.phase)
  const [messages, setMessages] = useState<Msg[]>([])
  const [clues, setClues] = useState<ClueSummary[]>([])
  const [activeChar, setActiveChar] = useState(game.characters[0]?.id ?? '')
  const [input, setInput] = useState('')
  const [streamText, setStreamText] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamCharId, setStreamCharId] = useState('')
  const [introRunning, setIntroRunning] = useState(false)
  const [accuseOpen, setAccuseOpen] = useState(false)
  const [result, setResult] = useState<AccuseResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.getClues(game.game_id).then((r) => setClues(r.clues)).catch(() => {})
  }, [game.game_id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamText])

  const runPhase = async (target: string) => {
    await api.advancePhase(game.game_id, target)
    setPhase(target)
  }

  const startSelfIntros = async () => {
    setIntroRunning(true)
    setError(null)
    try {
      await runPhase('self_intro')
      for (const c of game.characters) {
        await streamCharacter(c.id, '请用第一人称做一段简短的自我介绍。')
      }
      await runPhase('evidence')
    } catch (e) {
      setError(`自我介绍失败：${(e as Error).message}`)
    } finally {
      setIntroRunning(false)
    }
  }

  /** Stream a character's reply token-by-token, then commit it to the message log. */
  const streamCharacter = async (charId: string, text: string) => {
    setStreaming(true)
    setStreamCharId(charId)
    setStreamText('')
    try {
      let full = ''
      let rewritten = false
      let fellBack = false
      let leakCount = 0
      for await (const ev of streamTalk(game.game_id, charId, text)) {
        if (ev.type === 'token') {
          full += ev.chunk
          setStreamText(full)
        } else {
          rewritten = ev.result.rewritten
          fellBack = ev.result.fell_back
          leakCount = ev.result.leak_count
          full = ev.result.reply
        }
      }
      setMessages((ms) => [
        ...ms,
        { sender: 'character', charId, text: full, rewritten, fellBack, leakCount },
      ])
    } finally {
      setStreaming(false)
      setStreamText('')
      setStreamCharId('')
    }
  }

  const send = async () => {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    setError(null)
    setMessages((ms) => [...ms, { sender: 'player', charId: activeChar, text }])
    try {
      await streamCharacter(activeChar, text)
    } catch (e) {
      setError(`对话失败：${(e as Error).message}`)
    }
  }

  const doAccuse = async (suspectId: string, motiveFactId: string | null) => {
    setAccuseOpen(false)
    setError(null)
    try {
      const r = await api.accuse(game.game_id, suspectId, motiveFactId)
      setResult(r)
      setPhase('ended')
      setMessages((ms) => [...ms, { sender: 'system', text: r.reveal }])
    } catch (e) {
      setError(`指认失败：${(e as Error).message}`)
    }
  }

  return (
    <main className="game">
      <div className="game-topbar">
        <h2>{game.title}</h2>
        <span className={`phase-badge phase-${phase}`}>{phaseLabel(phase)}</span>
        <button className="link" onClick={onExit}>← 离开</button>
      </div>

      {phase === 'intro' && (
        <section className="panel intro-panel">
          <h3>案件背景</h3>
          <p className="brief">{game.brief}</p>
          <button className="primary" disabled={introRunning} onClick={startSelfIntros}>
            {introRunning ? '角色入场中…' : '开始游戏 · 角色自我介绍'}
          </button>
        </section>
      )}

      {(phase === 'self_intro' || introRunning) && (
        <section className="investigation">
          <ChatPanel
            characters={game.characters}
            messages={messages}
            activeChar={activeChar}
            onSelectChar={setActiveChar}
            input=""
            onInput={() => {}}
            onSend={() => {}}
            streaming={false}
            streamText=""
            streamChar={streamCharId || activeChar}
            readOnly
          />
          <div className="side">
            <p className="hint">角色正在依次自我介绍，请稍候…</p>
          </div>
        </section>
      )}

      {phase === 'evidence' && !introRunning && (
        <section className="investigation">
          <ChatPanel
            characters={game.characters}
            messages={messages}
            activeChar={activeChar}
            onSelectChar={setActiveChar}
            input=""
            onInput={() => {}}
            onSend={() => {}}
            streaming={false}
            streamText=""
            streamChar={streamCharId || activeChar}
            readOnly
          />
          <div className="side">
            <ClueBoard gameId={game.game_id} clues={clues} onClues={setClues} compact />
            <button
              className="primary"
              disabled={clues.length === 0}
              onClick={() => runPhase('investigation')}
            >
              进入自由调查 {clues.length === 0 && '（建议先搜证）'}
            </button>
          </div>
        </section>
      )}

      {phase === 'investigation' && (
        <section className="investigation">
          <ChatPanel
            characters={game.characters}
            messages={messages}
            activeChar={activeChar}
            onSelectChar={setActiveChar}
            input={input}
            onInput={setInput}
            onSend={send}
            streaming={streaming}
            streamText={streamText}
            streamChar={streamCharId || activeChar}
          />
          <div className="side">
            <ClueBoard gameId={game.game_id} clues={clues} onClues={setClues} compact />
            <button className="danger" onClick={() => setAccuseOpen(true)}>
              指认真凶
            </button>
          </div>
        </section>
      )}

      {phase === 'ended' && result && (
        <section className="panel result-panel">
          <h3>对局结束</h3>
          <p className={result.outcome.killer_correct ? 'ok' : 'bad'}>
            凶手判定：{result.outcome.killer_correct ? '✓ 正确' : '✗ 错误'}
          </p>
          <p className={result.outcome.motive_correct ? 'ok' : 'bad'}>
            动机判定：{result.outcome.motive_correct ? '✓ 正确' : '✗ 错误'}
          </p>
          <div className="reveal">
            <h4>真相揭晓</h4>
            <p>{result.reveal}</p>
          </div>
          <button className="primary" onClick={() => onReplay(game.game_id, game.title)}>
            查看复盘报告 →
          </button>
        </section>
      )}

      {error && <p className="error">{error}</p>}
      {accuseOpen && (
        <AccuseDialog
          gameId={game.game_id}
          characters={game.characters}
          onCancel={() => setAccuseOpen(false)}
          onConfirm={doAccuse}
        />
      )}
      <div ref={bottomRef} />
    </main>
  )
}

function phaseLabel(phase: string): string {
  const map: Record<string, string> = {
    intro: '背景介绍',
    self_intro: '自我介绍',
    evidence: '搜证',
    investigation: '自由调查',
    accusation: '指认',
    reveal: '真相揭示',
    ended: '已结束',
  }
  return map[phase] ?? phase
}
