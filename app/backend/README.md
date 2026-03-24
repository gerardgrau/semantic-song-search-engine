# Backend (prototype scaffold)

This backend is a **mock API** designed to support the frontend layout demo while the real classic and intelligent search engines are still under development.

## Purpose

- provide stable API contracts for the prototype
- return deterministic test data for traditional results, intelligent results, and map points
- keep implementation simple so it can be replaced later by real logic

## Structure

```text
app/backend/
  api/
    main.py
    schemas.py
    mock_data.py
    routes/
      search.py
```

## Endpoints

- `GET /` basic service info
- `GET /health` health check
- `GET /search?q=<query>&limit=<n>` returns:
  - `traditional_results`
  - `intelligent_results`
  - `map_points`

## Run locally

From repository root:

```bash
uvicorn app.backend.api.main:app --reload --host 127.0.0.1 --port 8000
```

Open docs at:

- `http://127.0.0.1:8000/docs`

## Notes

- All data is mock data.
- Ranking and map coordinates are test values only.
- This module intentionally avoids database dependencies for now.
