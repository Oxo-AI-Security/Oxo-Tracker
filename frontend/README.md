# AI Test Platform Frontend

Vue 3 + Vite + Naive UI + Ionicons5 frontend for the AI Test Platform backend.

## Structure

```text
src/
  api/          HTTP clients
  components/   reusable UI widgets
  layouts/      app shell and navigation
  router/       vue-router setup
  stores/       Pinia state
  types/        shared TypeScript types
  views/        dashboard pages
```

## Run

```powershell
cd C:\Users\13207\Desktop\ai-test-platform\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

The backend URL is configured in `.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

