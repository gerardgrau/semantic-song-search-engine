import { useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import { genreColor, GENRE_COLORS } from './genreColors'

function SongSphere({ point, isHighlighted, onHover, onClick, faded }) {
  const [hovered, setHovered] = useState(false)
  const color = genreColor(point.genre)
  const radius = isHighlighted ? 3.0 : 1.8
  const opacity = faded ? 0.25 : 0.9

  return (
    <mesh
      position={[point.x, point.y, point.z || 0]}
      onPointerOver={e => { e.stopPropagation(); setHovered(true); onHover(point.id) }}
      onPointerOut={e => { e.stopPropagation(); setHovered(false); onHover(null) }}
      onClick={e => { e.stopPropagation(); onClick(point.id) }}
    >
      <sphereGeometry args={[radius, 24, 24]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={isHighlighted ? 0.6 : 0.15}
        opacity={isHighlighted ? 1 : opacity}
        transparent={!isHighlighted}
        roughness={0.3}
        metalness={0.2}
      />
      {(hovered || isHighlighted) && (
        <Html center distanceFactor={30} style={{ pointerEvents: 'none' }}>
          <div className="viz-tooltip-3d">
            <strong>{point.title}</strong><br />{point.artist}
          </div>
        </Html>
      )}
    </mesh>
  )
}

export default function Scatter3D({ points, highlightedId, onPointHover, onPointClick, faded }) {
  // Compute camera position based on point spread
  const cameraPos = useMemo(() => {
    if (!points.length) return [30, 30, 30]
    const maxRange = Math.max(
      ...points.map(p => Math.abs(p.x)),
      ...points.map(p => Math.abs(p.y)),
      ...points.map(p => Math.abs(p.z || 0)),
      10
    )
    const d = maxRange * 2.5
    return [d, d, d]
  }, [points])

  return (
    <div className="viz-container">
      <Canvas camera={{ position: cameraPos, fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[50, 50, 50]} intensity={1.2} />
        <pointLight position={[-30, -30, 20]} intensity={0.4} color="#22B8CF" />
        <OrbitControls enableDamping dampingFactor={0.1} reverseOrbit reverseHorizontalOrbit reverseVerticalOrbit />
        {points.map(p => (
          <SongSphere
            key={p.id}
            point={p}
            isHighlighted={p.id === highlightedId}
            onHover={onPointHover}
            onClick={onPointClick}
            faded={faded}
          />
        ))}
      </Canvas>
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
