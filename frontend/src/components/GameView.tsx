import { useEffect, useRef, useState } from 'react'
import {
  api,
  type AccuseResult,
  type ClueSummary,
  type GameInfo,
  type NoteItem,
  type RoleCard,
} from '../api'
import { getLayout } from '../game/layout'
import { streamTalk } from '../sse'
import AccuseDialog from './game/AccuseDialog'
import ActionBar from './game/ActionBar'
import CaseFile from './game/CaseFile'
import ChatView, { type Msg } from './game/ChatView'
import DiscussionView from './game/DiscussionView'
import IntroOverlay from './game/IntroOverlay'
import PhaseProgress from './game/PhaseProgress'
import RevealOverlay from './game/RevealOverlay'
import RoleCardOverlay from './game/RoleCardOverlay'
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
  const [notes, setNotes] = useState<NoteItem[]>([])
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
  const roleplay = game.player_seat != null
  const [roleCard, setRoleCard] = useState<RoleCard | null>(null)
  const [showRoleCard, setShowRoleCard] = useState(roleplay)
  const [centerView, setCenterView] = useState<'chat' | 'discussion'>(roleplay ? 'discussion' : 'chat')

  const layout = getLayout(game.mode, phase)
  const activeCharacter = characters.find((c) => c.id === activeChar) ?? characters[0]

  useEffect(() => {
    api.getClues(game.game_id).then((r) => setClues(r.clues)).catch(() => {})
    api.getNotes(game.game_id).then((r) => setNotes(r.notes)).catch(() => {})
    if (roleplay) {
      api.getRoleCard(game.game_id).then(setRoleCard).catch(() => {})
    }
  }, [game.game_id, roleplay])

  const charName = (id: string | null) =>
    characters.find((c) => c.id === id)?.name ?? id ?? '?'

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

  // AI-only cast for the entrance sequence: the player's own seat introduces itself
  // (via the discussion channel) and has no agent to generate an intro.
  const introCast = characters.filter((c) => c.id !== game.player_seat)

  const startSelfIntros = async () => {
    setError(null)
    skipIntros.current = false
    try {
      await runPhase('self_intro')
      for (let i = 0; i < introCast.length; i++) {
        if (skipIntros.current) break
        setIntroIdx(i)
        setIntroSpeech('')
        const spoken = await streamCharacter(introCast[i].id, INTRO_PROMPT)
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
      api.getNotes(game.game_id).then((r) => setNotes(r.notes)).catch(() => {})
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
        {roleplay && roleCard && (
          <button className="link" onClick={() => setShowRoleCard(true)}>🎭 角色卡</button>
        )}
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
            notes={notes}
            onNotes={setNotes}
            charName={charName}
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
          {roleplay && layout.center === 'chat' && ['investigation', 'accusation', 'reveal', 'ended'].includes(phase) && (
            <div className="center-tabs">
              <button className={centerView === 'discussion' ? 'active' : ''} onClick={() => setCenterView('discussion')}>
                公开讨论
              </button>
              <button className={centerView === 'chat' ? 'active' : ''} onClick={() => setCenterView('chat')}>
                私聊 · {activeCharacter?.name ?? ''}
              </button>
            </div>
          )}
          {layout.center === 'chat' && activeCharacter && centerView === 'discussion' && roleplay ? (
            <DiscussionView
              gameId={game.game_id}
              characters={characters}
              playerSeat={game.player_seat!}
              onError={setError}
            />
          ) : layout.center === 'chat' && activeCharacter ? (
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
          ) : null}
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
          characters={introCast}
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
          characters={characters.filter((c) => c.id !== game.player_seat)}
          onCancel={() => setAccuseOpen(false)}
          onConfirm={doAccuse}
        />
      )}
      {reveal && (
        <RevealOverlay
          result={reveal}
          playerIsKiller={game.player_is_killer}
          onReplay={() => onReplay(game.game_id, game.title)}
          onExit={onExit}
        />
      )}
      {showRoleCard && roleCard && (
        <RoleCardOverlay card={roleCard} firstTime={phase === 'intro'} onClose={() => setShowRoleCard(false)} />
      )}
    </div>
  )
}
