export default function TopResults({ songs, message, query, onSongHover, highlightedId }) {
  const top10 = songs.slice(0, 10)

  return (
    <div className="top-results">
      <h2>
        {query ? `Resultats per "${query}"` : 'Totes les cançons'}
      </h2>

      {message && <p className="results-message">{message}</p>}

      <ul className="results-list">
        {top10.map((song, idx) => (
          <li
            key={song.id}
            className={`result-item ${highlightedId === song.id ? 'highlighted' : ''}`}
            onMouseEnter={() => onSongHover(song.id)}
            onMouseLeave={() => onSongHover(null)}
          >
            <span className="result-rank">{idx + 1}</span>
            <div className="result-info">
              <strong>{song.title}</strong>
              <span className="result-artist">{song.artist}</span>
              <span className="result-meta">
                {song.album} &middot; {song.genre} &middot; {song.year}
              </span>
              <span className="result-lyrics">{song.lyrics_snippet}</span>
            </div>
            {query && (
              <span className="result-score">{(song.score * 100).toFixed(0)}%</span>
            )}
          </li>
        ))}
      </ul>

      {songs.length > 10 && !query && (
        <p className="results-count">Mostrant 10 de {songs.length} cançons</p>
      )}
    </div>
  )
}
