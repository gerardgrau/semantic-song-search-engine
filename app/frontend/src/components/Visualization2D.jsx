import { useRef, useEffect, useCallback } from 'react'

const GENRE_COLORS = {
  pop: '#FF6B6B',
  rock: '#4ECDC4',
  folk: '#45B7D1',
  electronica: '#96CEB4',
  'hip-hop': '#FFEAA7',
  rumba: '#DDA0DD',
}

const DEFAULT_COLOR = '#999'

export default function Visualization2D({ points, highlightedId, onPointHover, topIds }) {
  const canvasRef = useRef(null)
  const tooltipRef = useRef(null)
  const transformRef = useRef({ scale: 1, offsetX: 0, offsetY: 0 })

  const topIdSet = new Set(topIds || [])

  const getTransform = useCallback((canvas, pts) => {
    if (!pts.length) return { scale: 1, offsetX: 0, offsetY: 0 }
    const pad = 40
    const xs = pts.map(p => p.x)
    const ys = pts.map(p => p.y)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const rangeX = maxX - minX || 1
    const rangeY = maxY - minY || 1
    const w = canvas.width - pad * 2
    const h = canvas.height - pad * 2
    const scale = Math.min(w / rangeX, h / rangeY)
    const offsetX = pad + (w - rangeX * scale) / 2 - minX * scale
    const offsetY = pad + (h - rangeY * scale) / 2 - minY * scale
    return { scale, offsetX, offsetY }
  }, [])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const { width, height } = canvas.getBoundingClientRect()
    canvas.width = width * window.devicePixelRatio
    canvas.height = height * window.devicePixelRatio
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    ctx.clearRect(0, 0, width, height)

    const t = getTransform({ width, height }, points)
    transformRef.current = t

    // Draw non-top points first (dimmer)
    for (const p of points) {
      if (topIdSet.has(p.id)) continue
      const px = p.x * t.scale + t.offsetX
      const py = p.y * t.scale + t.offsetY
      ctx.beginPath()
      ctx.arc(px, py, 3, 0, Math.PI * 2)
      ctx.fillStyle = GENRE_COLORS[p.genre] || DEFAULT_COLOR
      ctx.globalAlpha = 0.25
      ctx.fill()
    }

    // Draw top points (brighter, larger)
    ctx.globalAlpha = 1
    for (const p of points) {
      if (!topIdSet.has(p.id)) continue
      const px = p.x * t.scale + t.offsetX
      const py = p.y * t.scale + t.offsetY
      const isHighlighted = p.id === highlightedId
      const radius = isHighlighted ? 8 : 5

      ctx.beginPath()
      ctx.arc(px, py, radius, 0, Math.PI * 2)
      ctx.fillStyle = GENRE_COLORS[p.genre] || DEFAULT_COLOR
      ctx.fill()

      if (isHighlighted) {
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2
        ctx.stroke()
      }
    }

    // Draw highlighted label
    if (highlightedId != null) {
      const hp = points.find(p => p.id === highlightedId)
      if (hp) {
        const px = hp.x * t.scale + t.offsetX
        const py = hp.y * t.scale + t.offsetY
        ctx.font = '12px system-ui, sans-serif'
        ctx.fillStyle = '#fff'
        ctx.textAlign = 'center'
        ctx.fillText(`${hp.title} - ${hp.artist}`, px, py - 12)
      }
    }

    ctx.globalAlpha = 1
  }, [points, highlightedId, topIdSet, getTransform])

  useEffect(() => {
    draw()
    const handleResize = () => draw()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [draw])

  function handleMouseMove(e) {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const t = transformRef.current

    let closest = null
    let closestDist = 15 // pixel threshold

    for (const p of points) {
      const px = p.x * t.scale + t.offsetX
      const py = p.y * t.scale + t.offsetY
      const dist = Math.hypot(mx - px, my - py)
      if (dist < closestDist) {
        closestDist = dist
        closest = p
      }
    }

    onPointHover(closest ? closest.id : null)

    if (tooltipRef.current) {
      if (closest) {
        tooltipRef.current.style.display = 'block'
        tooltipRef.current.style.left = `${e.clientX - rect.left + 10}px`
        tooltipRef.current.style.top = `${e.clientY - rect.top - 10}px`
        tooltipRef.current.textContent = `${closest.title} - ${closest.artist}`
      } else {
        tooltipRef.current.style.display = 'none'
      }
    }
  }

  return (
    <div className="viz-container">
      <canvas
        ref={canvasRef}
        className="viz-canvas"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => {
          onPointHover(null)
          if (tooltipRef.current) tooltipRef.current.style.display = 'none'
        }}
      />
      <div ref={tooltipRef} className="viz-tooltip" />
      <div className="viz-legend">
        {Object.entries(GENRE_COLORS).map(([genre, color]) => (
          <span key={genre} className="legend-item">
            <span className="legend-dot" style={{ background: color }} />
            {genre}
          </span>
        ))}
      </div>
    </div>
  )
}
