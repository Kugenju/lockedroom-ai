// API client + types, mirroring backend/app/api/schemas.py

export interface CharacterSummary {
  id: string
  name: string
  role: string
  personality: string
}

export interface GameInfo {
  game_id: string
  script_id: string
  title: string
  phase: string
  brief: string
  characters: CharacterSummary[]
}

export interface ClueSummary {
  id: string
  title: string
  location: string
  description: string
}

export interface TalkResult {
  character_id: string
  reply: string
  rewritten: boolean
  fell_back: boolean
  leak_count: number
}

export interface MotiveOption {
  fact_id: string | null
  statement: string
}

export interface AccuseResult {
  outcome: { killer_correct: boolean; motive_correct: boolean }
  reveal: string
}

export interface SearchResult {
  location: string
  unlocked: ClueSummary[]
  total_unlocked: number
}

export interface LocationInfo {
  location: string
  total: number
  unlocked: number
}

export interface GameEvent {
  seq: number
  type: string
  ts: string
  payload: Record<string, unknown>
}

export interface Metrics {
  leak_rate: number
  clue_coverage: number
  killer_correct: boolean
  motive_correct: boolean
  score: number
  grade: string
  difficulty: number
  player_questions: number
  character_replies: number
  clues_unlocked: number
  leak_events: number
  hard_leaks: number
  soft_leaks: number
}

export interface ReplayData {
  game_id: string
  script_id: string
  title: string
  phase: string
  metrics: Metrics
  clues: ClueSummary[]
  events: GameEvent[]
}

export interface ChainData {
  suspect_trajectory: string[]
  key_insights: string[]
  missed_clues: string[]
  summary: string
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!resp.ok) {
    let detail: unknown = `${resp.status}`
    try {
      detail = (await resp.json()).detail ?? detail
    } catch {
      /* keep status code */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return (await resp.json()) as T
}

export const api = {
  listScripts: () => req<{ scripts: string[] }>('/scripts'),
  createGame: (scriptId: string) =>
    req<GameInfo>('/games', { method: 'POST', body: JSON.stringify({ script_id: scriptId }) }),
  getGame: (gameId: string) => req<GameInfo>(`/games/${gameId}`),
  advancePhase: (gameId: string, target: string) =>
    req<{ phase: string }>(`/games/${gameId}/phase`, {
      method: 'POST',
      body: JSON.stringify({ target }),
    }),
  getLocations: (gameId: string) => req<{ locations: LocationInfo[] }>(`/games/${gameId}/locations`),
  search: (gameId: string, location: string) =>
    req<SearchResult>(`/games/${gameId}/search`, {
      method: 'POST',
      body: JSON.stringify({ location }),
    }),
  getClues: (gameId: string) => req<{ clues: ClueSummary[] }>(`/games/${gameId}/clues`),
  talk: (gameId: string, characterId: string, message: string) =>
    req<TalkResult>(`/games/${gameId}/talk`, {
      method: 'POST',
      body: JSON.stringify({ character_id: characterId, message }),
    }),
  getMotiveOptions: (gameId: string) =>
    req<{ options: MotiveOption[] }>(`/games/${gameId}/motive-options`),
  accuse: (gameId: string, suspectId: string, motiveFactId: string | null) =>
    req<AccuseResult>(`/games/${gameId}/accuse`, {
      method: 'POST',
      body: JSON.stringify({ suspect_id: suspectId, motive_fact_id: motiveFactId }),
    }),
  getReplay: (gameId: string) => req<ReplayData>(`/games/${gameId}/replay`),
  getChain: (gameId: string) => req<ChainData>(`/games/${gameId}/chain`),
  getReport: async (gameId: string): Promise<string> => {
    const resp = await fetch(`/api/games/${gameId}/report`)
    if (!resp.ok) throw new Error(`${resp.status}`)
    return resp.text()
  },
}
