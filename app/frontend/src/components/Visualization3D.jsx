import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { useMemo } from 'react'

const GENRE_COLORS = {
  pop: '#FF6B6B',
  rock: '#4ECDC4',
  folk: '#45B7D1',
  electronica: '#96CEB4',
  'hip-hop': '#FFEAA7',
  rumba: '#DDA0DD',
}

function SongPoint({ point, isTop, isHighlighted, onHover }) {
  const color = GENRE_COLORS[point.genre] || '#999'
  const size = isHighlighted ? 0.35 : isTop ? 0.2 : 0.08

  return (
    <mesh
      position={[point.x, point.y, point.z]}
      onPointerOver={() => onHover(point.id)}
      onPointerOut={() => onHover(null)}
    >
      <sphereGeometry args={[size, 16, 16]} />
      <meshStandardMaterial
        color={color}
        opacity={isTop ? 1 : 0.3}
        transparent={!isTop}
        emissive={isHighlighted ? color : '#000'}
        emissiveIntensity={isHighlighted ? 0.5 : 0}
      />
    </mesh>
  )
}

export default function Visualization3D({ points, highlightedId, onPointHover, topIds }) {
  const topIdSet = useMemo(() => new Set(topIds || []), [topIds])

  return (
    <div className="viz-container">
      <Canvas camera={{ position: [15, 15, 15], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <pointLight position={[20, 20, 20]} intensity={1} />
        <OrbitControls enableDamping dampingFactor={0.1} />
        {points.map(p => (
          <SongPoint
            key={p.id}
            point={p}
            isTop={topIdSet.has(p.id)}
            isHighlighted={p.id === highlightedId}
            onHover={onPointHover}
          />
        ))}
      </Canvas>
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
