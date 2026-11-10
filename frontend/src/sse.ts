// SSE consumption over fetch POST (EventSource only supports GET).
// Frames look like: "event: token\ndata: {...}\n\n"

import type { TalkResult } from './api'

export type StreamEvent =
  | { type: 'token'; chunk: string }
  | { type: 'done'; result: TalkResult }

function parseFrame(frame: string): StreamEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim()
    else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
  }
  if (dataLines.length === 0) return null
  const data = JSON.parse(dataLines.join('\n'))
  if (event === 'token') return { type: 'token', chunk: data.chunk as string }
  if (event === 'done') return { type: 'done', result: data as TalkResult }
  return null
}

export async function* streamTalk(
  gameId: string,
  characterId: string,
  message: string,
): AsyncGenerator<StreamEvent> {
  const resp = await fetch(`/api/games/${gameId}/talk/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId, message }),
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
      const parsed = parseFrame(frame)
      if (parsed) yield parsed
    }
  }
}
