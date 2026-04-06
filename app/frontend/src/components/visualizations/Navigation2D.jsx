import { useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import * as THREE from 'three'
import { genreColor, GENRE_COLORS } from './genreColors'

/**
 * Grid-snapping: normalize t-SNE coords to grid, spiral-resolve collisions.
 */
function snapToGrid(points, gridSize) {
  if (!points.length) return []

  const xs = points.map(p => p.x)
  const ys = points.map(p => p.y)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const rangeX = maxX - minX || 1
  const rangeY = maxY - minY || 1

  const padding = 2
  const usable = gridSize - padding * 2
  const normalized = points.map(p => ({
    ...p,
    gx: Math.round(((p.x - minX) / rangeX) * usable + padding),
    gy: Math.round(((p.y - minY) / rangeY) * usable + padding),
  }))

  const occupied = new Set()
  const key = (x, y) => `${x},${y}`

  function findFreeCell(cx, cy) {
    if (!occupied.has(key(cx, cy))) return [cx, cy]
    for (let r = 1; r < gridSize; r++) {
      for (let dx = -r; dx <= r; dx++) {
        for (let dy = -r; dy <= r; dy++) {
          if (Math.abs(dx) !== r && Math.abs(dy) !== r) continue
          const nx = cx + dx, ny = cy + dy
          if (nx >= 0 && ny >= 0 && nx < gridSize && ny < gridSize && !occupied.has(key(nx, ny))) {
            return [nx, ny]
          }
        }
      }
    }
    return [cx, cy]
  }

  return normalized.map(p => {
    const [fx, fy] = findFreeCell(p.gx, p.gy)
    occupied.add(key(fx, fy))
    return { ...p, gridX: fx, gridY: fy }
  })
}

const CELL_SIZE = 6 // much more spacing between buildings

function Building({ point, score, maxScore, isHighlighted, onHover, onClick, faded }) {
  const [hovered, setHovered] = useState(false)
  const color = genreColor(point.genre)

  // Height: before search use deterministic pseudo-random based on id, after search proportional to score
  const normalizedScore = maxScore > 0 ? score / maxScore : 0
  const hasSearched = maxScore > 0.6
  const idHash = ((point.id * 2654435761) >>> 0) / 4294967296 // deterministic 0-1 from id
  const height = hasSearched ? Math.max(3, normalizedScore * 40) : 3 + idHash * 6
  const width = CELL_SIZE * 0.55
  const opacity = faded ? 0.3 : (isHighlighted ? 1 : 0.85)

  const worldX = point.gridX * CELL_SIZE
  const worldZ = point.gridY * CELL_SIZE

  return (
    <group position={[worldX, 0, worldZ]}>
      {/* Building body */}
      <mesh
        position={[0, height / 2, 0]}
        onPointerOver={e => { e.stopPropagation(); setHovered(true); onHover(point.id) }}
        onPointerOut={e => { e.stopPropagation(); setHovered(false); onHover(null) }}
        onClick={e => { e.stopPropagation(); onClick(point.id) }}
      >
        <boxGeometry args={[width, height, width]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isHighlighted ? 0.5 : 0.1}
          opacity={opacity}
          transparent={opacity < 1}
          roughness={0.5}
          metalness={0.1}
        />
      </mesh>

      {/* Roof — same width as building */}
      <mesh position={[0, height + 0.15, 0]}>
        <boxGeometry args={[width, 0.3, width]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
      </mesh>

      {/* Highlight ring */}
      {isHighlighted && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
          <ringGeometry args={[width * 0.8, width * 1.2, 32]} />
          <meshBasicMaterial color="#fff" opacity={0.5} transparent />
        </mesh>
      )}

      {/* Label */}
      {(hovered || isHighlighted) && (
        <Html center position={[0, height + 3, 0]} style={{ pointerEvents: 'none' }}>
          <div className="viz-tooltip-3d">
            <strong>{point.title}</strong><br />
            {point.artist}
            {hasSearched && <><br />{(score * 100).toFixed(0)}%</>}
          </div>
        </Html>
      )}
    </group>
  )
}

function Ground({ size, center }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[center, -0.1, center]} receiveShadow>
      <planeGeometry args={[size * 2, size * 2]} />
      <meshStandardMaterial color="#1a1a2e" opacity={0.6} transparent roughness={0.9} />
    </mesh>
  )
}

function GridLines({ size, center }) {
  const gridHelper = useMemo(() => {
    const divisions = Math.ceil(size / CELL_SIZE)
    const grid = new THREE.GridHelper(size * 2, divisions, '#333355', '#222244')
    grid.position.set(center, 0, center)
    grid.material.opacity = 0.25
    grid.material.transparent = true
    return grid
  }, [size, center])

  return <primitive object={gridHelper} />
}

export default function Navigation2D({ points, highlightedId, onPointHover, onPointClick, faded, scores }) {
  const gridSize = useMemo(() => {
    const minGrid = Math.ceil(Math.sqrt(points.length)) + 6
    return Math.max(minGrid, 14)
  }, [points])

  const data = useMemo(() => {
    const scoreMap = {}
    if (scores) scores.forEach(s => { scoreMap[s.id] = s.score })
    return points.map(p => ({
      ...p,
      score: scoreMap[p.id] ?? 0.5,
    }))
  }, [points, scores])

  const gridData = useMemo(() => snapToGrid(data, gridSize), [data, gridSize])

  const maxScore = useMemo(() => Math.max(...gridData.map(d => d.score), 0.01), [gridData])

  const worldSize = gridSize * CELL_SIZE
  const center = worldSize / 2

  // Camera: positioned at street level, looking toward the center of the city
  const cameraPos = useMemo(
    () => [center + worldSize * 0.3, worldSize * 0.25, center + worldSize * 0.5],
    [worldSize, center]
  )

  return (
    <div className="viz-container">
      <Canvas camera={{ position: cameraPos, fov: 60, near: 0.5, far: worldSize * 5 }} shadows>
        <ambientLight intensity={0.5} />
        <directionalLight position={[worldSize, worldSize, worldSize * 0.5]} intensity={0.8} castShadow />
        <pointLight position={[center, worldSize * 0.8, center]} intensity={0.4} color="#FFB74D" />
        <hemisphereLight args={['#87CEEB', '#1a1a2e', 0.3]} />

        <Ground size={worldSize} center={center} />
        <GridLines size={worldSize} center={center} />

        {gridData.map(p => (
          <Building
            key={p.id}
            point={p}
            score={p.score}
            maxScore={maxScore}
            isHighlighted={p.id === highlightedId}
            onHover={onPointHover}
            onClick={onPointClick}
            faded={faded}
          />
        ))}

        <OrbitControls
          enableDamping
          dampingFactor={0.1}
          maxPolarAngle={Math.PI * 0.85}
          minPolarAngle={0.1}
          minDistance={3}
          maxDistance={worldSize * 2.5}
          target={[center, 5, center]}
          enablePan
          panSpeed={1.5}
          rotateSpeed={0.8}
        />
      </Canvas>

      <div className="viz-legend">
        {Object.entries(GENRE_COLORS).map(([g, c]) => (
          <span key={g} className="legend-item">
            <span className="legend-dot" style={{ background: c }} />
            {g}
          </span>
        ))}
        <span className="legend-item legend-hint">Alçada = similaritat</span>
      </div>
    </div>
  )
}
