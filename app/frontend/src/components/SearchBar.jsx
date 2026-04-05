import { useState } from 'react'

export default function SearchBar({ onSearch, onReset, isLoading }) {
  const [query, setQuery] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = query.trim()
    if (trimmed) onSearch(trimmed)
  }

  function handleReset() {
    setQuery('')
    onReset()
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Escriu una cerca (ex: cançons tristes en català)..."
        disabled={isLoading}
      />
      <button type="submit" disabled={isLoading || !query.trim()}>
        Cercar
      </button>
      <button type="button" onClick={handleReset} disabled={isLoading} className="btn-reset">
        Reset
      </button>
    </form>
  )
}
