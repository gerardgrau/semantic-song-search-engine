const API_BASE_URL = window.APP_CONFIG?.API_BASE_URL || "http://127.0.0.1:8000";

const formElement = document.getElementById("search-form");
const inputElement = document.getElementById("search-input");
const traditionalListElement = document.getElementById("traditional-list");
const intelligentListElement = document.getElementById("intelligent-list");
const mapCanvasElement = document.getElementById("map-canvas");
const mapCaptionElement = document.getElementById("map-caption");

const fallbackPayload = {
  query: "demo",
  traditional_results: [
    {
      id: "trad-demo-1",
      title: "Cançó tradicional 1",
      artist: "Grup 1",
      album: "Àlbum demo 1",
      year: 2021,
      score: 0.94,
      preview: "Coincidència parcial de prova",
    },
    {
      id: "trad-demo-2",
      title: "Cançó tradicional 2",
      artist: "Grup 2",
      album: "Àlbum demo 2",
      year: 2018,
      score: 0.88,
      preview: "Coincidència parcial de prova",
    },
  ],
  intelligent_results: [
    {
      id: "smart-demo-1",
      title: "Cançó intel·ligent 1",
      artist: "Artista 3",
      album: "Col·lecció semàntica 1",
      year: 2017,
      score: 0.91,
      preview: "Relació semàntica de prova",
    },
    {
      id: "smart-demo-2",
      title: "Cançó intel·ligent 2",
      artist: "Artista 4",
      album: "Col·lecció semàntica 2",
      year: 2020,
      score: 0.86,
      preview: "Relació semàntica de prova",
    },
  ],
  map_points: [
    { song_id: "trad-demo-1", label: "Cançó tradicional 1", x: 18, y: 22, cluster: "Tradicional" },
    { song_id: "trad-demo-2", label: "Cançó tradicional 2", x: 32, y: 40, cluster: "Tradicional" },
    { song_id: "smart-demo-1", label: "Cançó intel·ligent 1", x: 62, y: 34, cluster: "Intel·ligent" },
    { song_id: "smart-demo-2", label: "Cançó intel·ligent 2", x: 76, y: 56, cluster: "Intel·ligent" },
  ],
};

function renderResults(listElement, items) {
  listElement.innerHTML = "";

  if (!items.length) {
    listElement.innerHTML = '<li class="state-message">Sense resultats de prova.</li>';
    return;
  }

  for (const item of items) {
    const listItem = document.createElement("li");
    listItem.className = "result-item";
    listItem.innerHTML = `
      <div class="result-title">${item.title}</div>
      <div class="result-meta">${item.artist} · ${item.album} · ${item.year} · score ${item.score}</div>
      <div class="result-preview">${item.preview}</div>
    `;
    listElement.appendChild(listItem);
  }
}

function renderMap(points, queryLabel) {
  mapCanvasElement.innerHTML = "";
  mapCaptionElement.textContent = queryLabel
    ? `Mostrant punts per a: "${queryLabel}"`
    : "Visualització de prova";

  if (!points.length) {
    const empty = document.createElement("div");
    empty.className = "state-message";
    empty.textContent = "No hi ha punts per mostrar.";
    mapCanvasElement.appendChild(empty);
    return;
  }

  for (const point of points) {
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = "map-point";
    marker.style.left = `${point.x}%`;
    marker.style.top = `${point.y}%`;
    marker.dataset.label = `${point.label} (${point.cluster})`;
    marker.dataset.cluster = point.cluster;
    marker.setAttribute("aria-label", marker.dataset.label);
    mapCanvasElement.appendChild(marker);
  }
}

function showLoading() {
  traditionalListElement.innerHTML = '<li class="state-message">Carregant...</li>';
  intelligentListElement.innerHTML = '<li class="state-message">Carregant...</li>';
  mapCanvasElement.innerHTML = '<div class="state-message">Actualitzant mapa...</div>';
}

async function fetchSearch(query) {
  const url = new URL(`${API_BASE_URL}/search`);
  url.searchParams.set("q", query);
  url.searchParams.set("limit", "5");

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

function renderPayload(payload) {
  renderResults(traditionalListElement, payload.traditional_results || []);
  renderResults(intelligentListElement, payload.intelligent_results || []);
  renderMap(payload.map_points || [], payload.query || "");
}

async function runSearch(query) {
  showLoading();

  try {
    const payload = await fetchSearch(query);
    renderPayload(payload);
  } catch (error) {
    renderPayload({ ...fallbackPayload, query: query || fallbackPayload.query });
  }
}

formElement.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = inputElement.value.trim();
  await runSearch(query);
});

runSearch("");
