import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export async function fetchAllSongs() {
  const { data } = await api.get('/songs')
  return data
}

export async function searchSongs(query) {
  const { data } = await api.get('/search', { params: { q: query } })
  return data
}

export async function fetchSongById(songId) {
  const { data } = await api.get(`/songs/${songId}`)
  return data
}
