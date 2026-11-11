// Deterministic color avatar: same character id always maps to the same color.

const PALETTE_HUES = [8, 28, 45, 95, 150, 175, 200, 225, 260, 300, 330, 355]

export function hueOf(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) {
    h = (h * 31 + id.charCodeAt(i)) >>> 0
  }
  return PALETTE_HUES[h % PALETTE_HUES.length]
}

interface Props {
  id: string
  name: string
  size?: number
  dim?: boolean
}

export default function Avatar({ id, name, size = 40, dim }: Props) {
  const hue = hueOf(id)
  return (
    <div
      className={dim ? 'avatar dim' : 'avatar'}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.42,
        background: `linear-gradient(135deg, hsl(${hue} 40% 34%), hsl(${hue} 45% 22%))`,
      }}
    >
      {name.slice(0, 1)}
    </div>
  )
}
