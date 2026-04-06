import { useRef, useEffect, useCallback } from 'react'
import { genreColor, GENRE_COLORS } from './genreColors'

/**
 * 2D Scatter with free pan & zoom (zoom toward mouse cursor, like Google Maps).
 *
 * Coordinate pipeline:
 *   data (p.x, p.y)  →  base transform  →  world coords  →  view (pan+zoom)  →  screen
 *
 * viewRef stores { panX, panY, zoom }.
 * Screen = world * zoom + pan
 */
export default function Scatter2D({ points, highlightedId, onPointHover, onPointClick, faded }) {
  const canvasRef = useRef(null)
  const viewRef = useRef({ panX: 0, panY: 0, zoom: 1 })
  const baseTransformRef = useRef({ scale: 1, offsetX: 0, offsetY: 0 })
  const dragRef = useRef({ dragging: false, startX: 0, startY: 0, startPanX: 0, startPanY: 0 })
  const initedRef = useRef(false)

  // Compute a base transform that maps data coords into [pad, canvasSize-pad]
  const getBaseTransform = useCallback((w, h, pts) => {
    if (!pts.length) return { scale: 1, offsetX: 0, offsetY: 0 }
    const pad = 60
    const xs = pts.map(p => p.x)
    const ys = pts.map(p => p.y)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const rangeX = maxX - minX || 1
    const rangeY = maxY - minY || 1
    const usableW = w - pad * 2
    const usableH = h - pad * 2
    const scale = Math.min(usableW / rangeX, usableH / rangeY)
    const offsetX = pad + (usableW - rangeX * scale) / 2 - minX * scale
    const offsetY = pad + (usableH - rangeY * scale) / 2 - minY * scale
    return { scale, offsetX, offsetY }
  }, [])

  // Convert data point to "world" coords (before pan/zoom)
  function toWorld(p, bt) {
    return {
      x: p.x * bt.scale + bt.offsetX,
      y: p.y * bt.scale + bt.offsetY,
    }
  }

  // Convert world coords to screen coords
  function worldToScreen(wx, wy) {
    const { panX, panY, zoom } = viewRef.current
    return {
      x: wx * zoom + panX,
      y: wy * zoom + panY,
    }
  }

  // Convert data point all the way to screen
  function pointToScreen(p, bt) {
    const w = toWorld(p, bt)
    return worldToScreen(w.x, w.y)
  }

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    const ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, rect.width, rect.height)

    const bt = getBaseTransform(rect.width, rect.height, points)
    baseTransformRef.current = bt

    // On first draw (or after points change), set pan so that identity view = centered
    if (!initedRef.current) {
      viewRef.current = { panX: 0, panY: 0, zoom: 1 }
      initedRef.current = true
    }

    const { zoom } = viewRef.current
    const RADIUS = 7
    const HIGHLIGHT_RADIUS = 12

    // Draw non-highlighted
    for (const p of points) {
      if (p.id === highlightedId) continue
      const { x: px, y: py } = pointToScreen(p, bt)
      ctx.beginPath()
      ctx.arc(px, py, RADIUS * zoom, 0, Math.PI * 2)
      ctx.fillStyle = genreColor(p.genre)
      ctx.globalAlpha = faded ? 0.25 : 0.85
      ctx.fill()
      ctx.globalAlpha = 1
    }

    // Draw highlighted on top
    if (highlightedId != null) {
      const hp = points.find(p => p.id === highlightedId)
      if (hp) {
        const { x: px, y: py } = pointToScreen(hp, bt)

        ctx.beginPath()
        ctx.arc(px, py, (HIGHLIGHT_RADIUS + 4) * zoom, 0, Math.PI * 2)
        ctx.fillStyle = genreColor(hp.genre)
        ctx.globalAlpha = 0.3
        ctx.fill()
        ctx.globalAlpha = 1

        ctx.beginPath()
        ctx.arc(px, py, HIGHLIGHT_RADIUS * zoom, 0, Math.PI * 2)
        ctx.fillStyle = genreColor(hp.genre)
        ctx.fill()
        ctx.strokeStyle = '#fff'
        ctx.lineWidth = 2.5
        ctx.stroke()

        ctx.font = `bold ${Math.round(13 * zoom)}px system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-primary').trim() || '#333'
        ctx.fillText(`${hp.title} — ${hp.artist}`, px, py - HIGHLIGHT_RADIUS * zoom - 8)
      }
    }
  }, [points, highlightedId, faded, getBaseTransform])

  useEffect(() => {
    initedRef.current = false // reset view on new points
    draw()
    const onResize = () => draw()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [draw])

  function getScreenPos(p) {
    return pointToScreen(p, baseTransformRef.current)
  }

  function handleMouseMove(e) {
    const canvas = canvasRef.current
    if (!canvas) return

    if (dragRef.current.dragging) {
      const dx = e.clientX - dragRef.current.startX
      const dy = e.clientY - dragRef.current.startY
      viewRef.current.panX = dragRef.current.startPanX + dx
      viewRef.current.panY = dragRef.current.startPanY + dy
      draw()
      return
    }

    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top

    let closest = null
    let closestDist = 20 * viewRef.current.zoom

    for (const p of points) {
      const sp = getScreenPos(p)
      const dist = Math.hypot(mx - sp.x, my - sp.y)
      if (dist < closestDist) {
        closestDist = dist
        closest = p
      }
    }
    onPointHover(closest ? closest.id : null)
  }

  function handleMouseDown(e) {
    dragRef.current = {
      dragging: true,
      startX: e.clientX,
      startY: e.clientY,
      startPanX: viewRef.current.panX,
      startPanY: viewRef.current.panY,
    }
  }

  function handleMouseUp(e) {
    const wasDragging = dragRef.current.dragging
    const dx = Math.abs(e.clientX - dragRef.current.startX)
    const dy = Math.abs(e.clientY - dragRef.current.startY)
    dragRef.current.dragging = false

    if (wasDragging && dx < 4 && dy < 4) {
      const canvas = canvasRef.current
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top

      for (const p of points) {
        const sp = getScreenPos(p)
        if (Math.hypot(mx - sp.x, my - sp.y) < 15 * viewRef.current.zoom) {
          onPointClick(p.id)
          return
        }
      }
    }
  }

  function handleWheel(e) {
    e.preventDefault()
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()

    // Mouse position in screen coords
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top

    const oldZoom = viewRef.current.zoom
    const factor = e.deltaY > 0 ? 0.9 : 1.1
    const newZoom = Math.max(0.2, Math.min(15, oldZoom * factor))

    // Adjust pan so the point under the cursor stays fixed:
    // Before: screenPos = worldPos * oldZoom + oldPan  →  worldPos = (mx - oldPan) / oldZoom
    // After:  screenPos = worldPos * newZoom + newPan  →  newPan = mx - worldPos * newZoom
    const worldX = (mx - viewRef.current.panX) / oldZoom
    const worldY = (my - viewRef.current.panY) / oldZoom

    viewRef.current.zoom = newZoom
    viewRef.current.panX = mx - worldX * newZoom
    viewRef.current.panY = my - worldY * newZoom

    draw()
  }

  return (
    <div className="viz-container">
      <canvas
        ref={canvasRef}
        className="viz-canvas"
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => { dragRef.current.dragging = false; onPointHover(null) }}
        onWheel={handleWheel}
        style={{ cursor: dragRef.current?.dragging ? 'grabbing' : 'grab' }}
      />
      <div className="viz-legend">
        {Object.entries(GENRE_COLORS).map(([g, c]) => (
          <span key={g} className="legend-item">
            <span className="legend-dot" style={{ background: c }} />
            {g}
          </span>
        ))}
      </div>
    </div>
  )
}
