import { useEffect, useRef, useState } from 'react'
import { api, type AccuseResult, type ClueSummary, type GameInfo } from '../api'
import { getLayout } from '../game/layout'
import { streamTalk } from '../sse'
import AccuseDialog from './game/AccuseDialog'
import ActionBar from './game/ActionBar'
import CaseFile from './game/CaseFile'
import ChatView, { type Msg } from './game/ChatView'
import IntroOverlay from './game/IntroOverlay'
import PhaseProgress from './game/PhaseProgress'
import RevealOverlay from './game/RevealOverlay'
import Roster from './game/Roster'

type Buckets = Record<string, Msg[]>

interface Props {
  game: GameInfo
  onExit: () => void
  onReplay: (gameId: string, title: string) => void
}

const INTRO_PROMPT = '请用第一人称做一段简短的自我介绍。'

export default function GameView({ game, onExit, onReplay }: Props) {
  const characters = game.characters
  const [phase, setPhase] = useState(game.phase)
  const [buckets, setBuckets] = useState<Buckets>({})
  const [clues, setClues] = useState<ClueSummary[]>([])
  const [activeChar, setActiveChar] = useState(characters[0]?.id ?? '')
  const [input, setInput] = useState('')
  const [streamText, setStreamText] = useState('')
  const [streamCharId, setStreamCharId] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [introIdx, setIntroIdx] = useState<number | null>(null)
  const [introSpeech, setIntroSpeech] = useState('')
  const [reveal, setReveal] = useState<AccuseResult | null>(null)
  const [accuseOpen, setAccuseOpen] = useState(false)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const skipIntros = useRef(false)
  const advanceIntro = useRef<() => void>(() => {})

  const layout = getLayout(game.mode, phase)
  const activeCharacter = characters.find((c) => c.id === activeChar) ?? characters[0]

  useEffect(() => {
    api.getClues(game.game_id).then((r) => setClues(r.clues)).catch(() => {})
  }, [game.game_id])

  const appendMsg = (charId: string, msg: Msg) =>
    setBuckets((b) => ({ ...b, [charId]: [...(b[charId] ?? []), msg] }))

  const runPhase = async (target: string) => {
    await api.advancePhase(game.game_id, target)
    setPhase(target)
  }

  /** Stream a character's reply token-by-token, then commit it to that character's bucket. */
  const streamCharacter = async (charId: string, text: string): Promise<string> => {
    setStreaming(true)
    setStreamCharId(charId)
    setStreamText('')
    try {
      let full = ''
      let rewritten = false
      let fellBack = false
      for await (const ev of streamTalk(game.game_id, charId, text)) {
        if (ev.type === 'token') {
          full += ev.chunk
          setStreamText(full)
        } else {
          rewritten = ev.result.rewritten
          fellBack = ev.result.fell_back
          full = ev.result.reply
        }
      }
      appendMsg(charId, { from: 'character', text: full, rewritten, fellBack })
      return full
    } finally {
      setStreaming(false)
      setStreamText('')
      setStreamCharId('')
    }
  }

  /** Pacing is click-driven (no timers) so hidden/occluded tabs never stall the sequence. */
  const waitForClick = () =>
    new Promise<void>((resolve) => {
      advanceIntro.current = resolve
    })

  const startSelfIntros = async () => {
    setError(null)
    skipIntros.current = false
    try {
      await runPhase('self_intro')
      for (let i = 0; i < characters.length; i++) {
        if (skipIntros.current) break
        setIntroIdx(i)
        setIntroSpeech('')
        const spoken = await streamCharacter(characters[i].id, INTRO_PROMPT)
        setIntroSpeech(spoken)
        if (skipIntros.current) break
        await waitForClick()
      }
    } catch (e) {
      setError(`登场失败：${(e as Error).message}`)
    } finally {
      advanceIntro.current = () => {}
      setIntroIdx(null)
      await runPhase('evidence').catch((e) => setError(String(e)))
    }
  }

  const nextIntro = () => {
    advanceIntro.current()
    advanceIntro.current = () => {}
  }

  const skipIntroSequence = () => {
    skipIntros.current = true
    advanceIntro.current()
    advanceIntro.current = () => {}
  }

  const send = async () => {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')
    setError(null)
    appendMsg(activeChar, { from: 'player', text })
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
      setReveal(r)
      setPhase('ended')
    } catch (e) {
      setError(`指认失败：${(e as Error).message}`)
    }
  }

  return (
    <div className="game-shell">
      <header className="shell-topbar">
        <button className="link" onClick={onExit}>← 大厅</button>
        <h2>{game.title}</h2>
        <PhaseProgress phase={phase} />
        <span className="shell-spacer" />
      </header>

      <div
        className={
          leftCollapsed
            ? 'shell-body left-collapsed'
            : 'shell-body'
        }
      >
        {layout.casefile ? (
          <CaseFile
            brief={game.brief}
            gameId={game.game_id}
            clues={clues}
            onClues={setClues}
            collapsed={leftCollapsed}
            onToggle={() => setLeftCollapsed((v) => !v)}
          />
        ) : (
          <span />
        )}

        <main className="shell-center">
          {layout.center === 'brief' && phase === 'intro' && (
            <section className="brief-stage">
              <h1>{game.title}</h1>
              <p>{game.brief}</p>
              <p className="hint">
                在场可问询：{characters.map((c) => c.name).join('、')}（共 {characters.length} 人）
              </p>
            </section>
          )}
          {layout.center === 'chat' && activeCharacter && (
            <ChatView
              character={activeCharacter}
              messages={buckets[activeChar] ?? []}
              composer={layout.composer}
              input={input}
              onInput={setInput}
              onSend={send}
              sending={streaming && streamCharId === activeChar}
              streamText={streamCharId === activeChar ? streamText : ''}
            />
          )}
          {error && <p className="error floating">{error}</p>}
        </main>

        {layout.roster && (
          <Roster characters={characters} activeChar={activeChar} onSelect={setActiveChar} />
        )}
      </div>

      <ActionBar
        layout={layout}
        clueCount={clues.length}
        onStart={startSelfIntros}
        onToInvestigation={() => runPhase('investigation').catch((e) => setError(String(e)))}
        onAccuse={() => setAccuseOpen(true)}
      />

      {introIdx !== null && (
        <IntroOverlay
          characters={characters}
          idx={introIdx}
          streamText={streamText}
          speech={introSpeech}
          ready={!streaming}
          onNext={nextIntro}
          onSkip={skipIntroSequence}
        />
      )}
      {accuseOpen && (
        <AccuseDialog
          gameId={game.game_id}
          characters={characters}
          onCancel={() => setAccuseOpen(false)}
          onConfirm={doAccuse}
        />
      )}
      {reveal && (
        <RevealOverlay
          result={reveal}
          onReplay={() => onReplay(game.game_id, game.title)}
          onExit={onExit}
        />
      )}
    </div>
  )
}
