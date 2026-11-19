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
  mode: string
  phase: string
  brief: string
  player_seat: string | null
  player_is_killer: boolean
  characters: CharacterSummary[]
}

export interface ScriptDetail {
  id: string
  title: string
  mode: string
  player_selectable: string[]
  characters: CharacterSummary[]
}

export interface RoleCard {
  character: CharacterSummary
  speaking_style: string
  public_profile: string
  secrets: string[]
}

export interface DiscussionMessage {
  sender: string
  sender_name: string
  content: string
  ts: string
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

export interface NoteItem {
  note_id: string
  source: string // "auto" | "player"
  content: string
  char_id: string | null
  importance: number | null
  ts: string
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
  listScripts: () =>
    req<{ scripts: string[]; details: ScriptDetail[] }>('/scripts'),
  createGame: (scriptId: string, playerSeat?: string | null) =>
    req<GameInfo>('/games', {
      method: 'POST',
      body: JSON.stringify({ script_id: scriptId, player_seat: playerSeat ?? null }),
    }),
  getGame: (gameId: string) => req<GameInfo>(`/games/${gameId}`),
  getRoleCard: (gameId: string) => req<RoleCard>(`/games/${gameId}/role-card`),
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
  getNotes: (gameId: string) => req<{ notes: NoteItem[] }>(`/games/${gameId}/notes`),
  addNote: (gameId: string, content: string) =>
    req<NoteItem>(`/games/${gameId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  deleteNote: (gameId: string, noteId: string) =>
    req<{ ok: boolean }>(`/games/${gameId}/notes/${noteId}`, { method: 'DELETE' }),
  getDiscussion: (gameId: string) =>
    req<{ messages: DiscussionMessage[] }>(`/games/${gameId}/discussion`),
  sayDiscussion: (gameId: string, message: string) =>
    req<{ messages: DiscussionMessage[] }>(`/games/${gameId}/discussion/say`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
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

// SSE stream of one AI character's public discussion speech
export async function* streamDiscussionSpeak(
  gameId: string,
  characterId: string,
): AsyncGenerator<
  | { type: 'token'; chunk: string }
  | { type: 'done'; character_id: string; reply: string; rewritten: boolean; fell_back: boolean }
> {
  const resp = await fetch(`/api/games/${gameId}/discussion/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId }),
  })
  if (!resp.ok || !resp.body) throw new Error(`${resp.status}`)
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const frame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      let event = 'message'
      const dataLines: string[] = []
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      if (dataLines.length === 0) continue
      const data = JSON.parse(dataLines.join('\n'))
      if (event === 'token') {
        yield { type: 'token', chunk: data.chunk as string }
      } else if (event === 'done') {
        yield {
          type: 'done',
          character_id: data.character_id,
          reply: data.reply,
          rewritten: data.rewritten,
          fell_back: data.fell_back,
        }
      }
    }
  }
}
