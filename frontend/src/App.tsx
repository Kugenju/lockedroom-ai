import { useState } from 'react'
import type { GameInfo } from './api'
import Lobby from './components/Lobby'
import GameView from './components/GameView'
import ReplayView from './components/ReplayView'

type View =
  | { name: 'lobby' }
  | { name: 'game'; game: GameInfo }
  | { name: 'replay'; gameId: string; title: string }

export default function App() {
  const [view, setView] = useState<View>({ name: 'lobby' })

  return (
    <div className="app">
      <header className="app-header">
        <h1 onClick={() => setView({ name: 'lobby' })} style={{ cursor: 'pointer' }}>
          LockedRoom <span className="accent">AI</span>
        </h1>
        <p className="tagline">多智能体剧本杀 · 每个角色都被锁进自己的信息密室</p>
      </header>
      {view.name === 'lobby' && (
        <Lobby
          onStart={(game) => setView({ name: 'game', game })}
        />
      )}
      {view.name === 'game' && (
        <GameView
          game={view.game}
          onExit={() => setView({ name: 'lobby' })}
          onReplay={(gameId, title) => setView({ name: 'replay', gameId, title })}
        />
      )}
      {view.name === 'replay' && (
        <ReplayView
          gameId={view.gameId}
          title={view.title}
          onBack={() => setView({ name: 'lobby' })}
        />
      )}
    </div>
  )
}
