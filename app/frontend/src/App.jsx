import { useState, useEffect, useCallback } from 'react'
import SearchBar from './components/SearchBar'
import TopResults from './components/TopResults'
import Visualization2D from './components/Visualization2D'
import Visualization3D from './components/Visualization3D'
import { fetchAllSongs, searchSongs } from './api/client'
import './App.css'

export default function App() {
  const [songs, setSongs] = useState([])
  const [points2d, setPoints2d] = useState([])
  const [points3d, setPoints3d] = useState([])
  const [query, setQuery] = useState('')
  const [message, setMessage] = useState(null)
  const [viewMode, setViewMode] = useState('2D')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [highlightedId, setHighlightedId] = useState(null)

  const topIds = songs.slice(0, 10).map(s => s.id)

  const loadAllSongs = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchAllSongs()
      setSongs(data.songs)
      setPoints2d(data.points_2d)
      setPoints3d(data.points_3d)
      setQuery('')
      setMessage(null)
    } catch (err) {
      setError("No s'ha pogut connectar amb el servidor. Assegura't que el backend està corrent.")
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAllSongs()
  }, [loadAllSongs])

  async function handleSearch(q) {
    setIsLoading(true)
    setError(null)
    try {
      const data = await searchSongs(q)
      setSongs(data.songs)
      setPoints2d(data.points_2d)
      setPoints3d(data.points_3d)
      setQuery(data.query)
      setMessage(data.message)
    } catch (err) {
      setError('Error en la cerca. Torna-ho a provar.')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  function handleReset() {
    loadAllSongs()
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Descobridor de Cançons</h1>
        <SearchBar onSearch={handleSearch} onReset={handleReset} isLoading={isLoading} />
      </header>

      {error && <div className="error-banner">{error}</div>}

      <main className="app-main">
        <section className="panel-left">
          <TopResults
            songs={songs}
            message={message}
            query={query}
            onSongHover={setHighlightedId}
            highlightedId={highlightedId}
          />
        </section>

        <section className="panel-right">
          <div className="viz-header">
            <div className="viz-toggle">
              <button
                className={viewMode === '2D' ? 'active' : ''}
                onClick={() => setViewMode('2D')}
              >
                2D
              </button>
              <button
                className={viewMode === '3D' ? 'active' : ''}
                onClick={() => setViewMode('3D')}
              >
                3D
              </button>
            </div>
            <span className="viz-count">
              {query
                ? `${topIds.length} destacades de ${songs.length}`
                : `${songs.length} cançons`}
            </span>
          </div>

          {viewMode === '2D' ? (
            <Visualization2D
              points={points2d}
              highlightedId={highlightedId}
              onPointHover={setHighlightedId}
              topIds={topIds}
            />
          ) : (
            <Visualization3D
              points={points3d}
              highlightedId={highlightedId}
              onPointHover={setHighlightedId}
              topIds={topIds}
            />
          )}
        </section>
      </main>
    </div>
  )
}
