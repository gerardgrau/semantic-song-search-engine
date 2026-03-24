# Frontend (prototype scaffold)

This frontend is a lightweight demo focused on **layout and interaction flow**.

It intentionally uses mock/test content so the team can validate UX before implementing real classic search, intelligent search, and map logic.

## What is implemented

- wide search bar at the top
- left column with two lists:
  - traditional results
  - intelligent results
- right column with a map panel (prototype scatter visualization)
- loading/error states
- backend integration with local fallback mock data

## Structure

```text
frontend/
  index.html
  styles.css
  app.js
  config.js
  config.example.js
```

## Configure API URL

`config.js` contains:

```js
window.APP_CONFIG = {
  API_BASE_URL: "http://127.0.0.1:8000"
}
```

If backend URL changes, edit `frontend/config.js`.

## Run frontend locally

From repository root:

```bash
python -m http.server 3000 -d frontend
```

Open:

- `http://127.0.0.1:3000`

## Notes

- This is a prototype UI scaffold.
- Map points are placeholders for future clustering/embedding visualization.
- Song and score content is test-only.
