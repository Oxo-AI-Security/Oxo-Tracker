# Oxo Tracker

Oxo Tracker is a secure AI evaluation workspace for testing model agents, prompt safety, connector behavior, and red-team resilience. It combines a FastAPI backend, a Vue 3 workspace, and local Moonshot assets so evaluation teams can configure targets, run benchmark suites, inspect prompt traces, and keep adversarial conversations in one place.

The product is designed for AI security review workflows where teams need repeatable tests, visible evidence, and side-by-side comparison between clean and attacked interactions.

![Benchmark run details](docs/images/benchmark-run-details.png)

## Product Highlights

- **Benchmark orchestration**: launch cookbook and recipe based evaluations against selected model endpoints, then inspect progress, prompt traces, errors, reports, and downloadable run output.
- **Red-team workspace**: maintain adversarial chat sessions with payload selection, attack-module controls, context strategy options, and clean comparison conversations.
- **Payload library**: browse and curate cookbooks, recipes, datasets, attack modules, and prompt templates used by evaluation runs.
- **Agent and connector management**: create model endpoints and configurable connectors for HTTP, SSE, and WebSocket based AI applications.
- **Agent security review**: upload design documents, diagrams, prompts, tool specs, and screenshots to extract application functions and build a review map.
- **Local-first evidence store**: keep benchmark jobs, red-team sessions, settings, and generated reports in project data directories for repeatable local review.

## Interface Preview

### Red-team comparison

Use the Agents workspace to run adversarial prompts with payloads while keeping a clean comparison thread visible for the same target endpoint.

![Red-team workspace](docs/images/red-team-workspace.png)

### Evaluation suites

Use the Cookbooks view to inspect built-in and custom evaluation suites, select test coverage, and organize reusable safety scenarios.

![Cookbooks](docs/images/cookbooks.png)

## Core Workflow

1. Configure model agents or custom application connectors.
2. Select payload assets such as cookbooks, recipes, datasets, prompt templates, and attack modules.
3. Run a benchmark or open a red-team session against the selected endpoint.
4. Inspect prompt traces, model responses, judge results, errors, and generated reports.
5. Save evidence locally and export reports for review.

## Architecture

Oxo Tracker uses a Python backend for API orchestration and Moonshot integration, and a Vue frontend for the evaluation workspace.

- Backend: FastAPI, local job runtime, Moonshot service adapters, settings and report stores.
- Frontend: Vue 3, Vite, Pinia, Naive UI, evaluation views, red-team chat workspace, and connector builder.
- Data: local Moonshot assets, benchmark job JSON files, red-team sessions, generated reports, and settings.

## Project Layout

```text
app/                         FastAPI backend
  api/routes/                 HTTP API routes
  core/                       configuration and startup wiring
  integrations/moonshot/      Moonshot adapter code
  schemas/                    request/response schemas
  services/                   application services
frontend/                     Vue 3 + Vite + Naive UI frontend
data/
  moonshot-data/              Moonshot assets installed locally
  jobs/                       local benchmark job runtime data
  redteam_sessions/           local red-team session runtime data
scripts/                      setup/test helper scripts
tests/                        backend tests
```

## Prerequisites

- Python 3.11.x. The project currently targets `>=3.11,<3.12`.
- Node.js 20+ and npm.
- Git.
- Network access for Python and npm dependency installation.

Recommended local ports:

- Backend: `http://127.0.0.1:8001`
- Frontend: `http://127.0.0.1:5173`

## Windows Deployment

Run the commands from PowerShell in the project root.

### 1. Clone the repository

```powershell
git clone https://github.com/Oxo-AI-Security/Oxo-Tracker.git
cd Oxo-Tracker
```

### 2. Create the Python environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks script activation, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Create backend configuration

```powershell
Copy-Item .env.example .env
```

The default `.env.example` points all Moonshot asset paths to `data/moonshot-data`.

### 4. Install Moonshot data

```powershell
Push-Location data
..\.venv\Scripts\python.exe -m moonshot -i moonshot-data -u
Pop-Location
```

On Windows, some TensorFlow packages in Moonshot data may not resolve cleanly. Use the provided Windows requirements file:

```powershell
pip install -r requirements-moonshot-data-windows.txt
python -m nltk.downloader punkt stopwords
python -m spacy download en_core_web_lg
```

You can also run the bundled bootstrap script:

```powershell
.\scripts\bootstrap.ps1
```

### 5. Install frontend dependencies

```powershell
cd frontend
npm install
Copy-Item .env.example .env
cd ..
```

Make sure `frontend\.env` points to the backend:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

### 6. Start the backend

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Backend API docs are available at:

```text
http://127.0.0.1:8001/docs
```

### 7. Start the frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

## Linux Deployment

Run the commands from a shell in the project root.

### 1. Clone the repository

```bash
git clone https://github.com/Oxo-AI-Security/Oxo-Tracker.git
cd Oxo-Tracker
```

### 2. Create the Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `python3.11` is not installed, install it first with your package manager.

Ubuntu example:

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev build-essential
```

### 3. Create backend configuration

```bash
cp .env.example .env
```

### 4. Install Moonshot data

```bash
cd data
../.venv/bin/python -m moonshot -i moonshot-data -u
cd ..
```

Install Moonshot data dependencies:

```bash
pip install -r data/moonshot-data/requirements.txt
python -m nltk.downloader punkt stopwords
python -m spacy download en_core_web_lg
```

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cp .env.example .env
cd ..
```

Make sure `frontend/.env` points to the backend:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

### 6. Start the backend

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Backend API docs are available at:

```text
http://127.0.0.1:8001/docs
```

### 7. Start the frontend

Open a second terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

## Production Build

Build the frontend:

```bash
cd frontend
npm run build
```

Preview the built frontend locally:

```bash
npm run preview -- --host 127.0.0.1 --port 4173
```

For production deployment, run the FastAPI backend with a process manager such as systemd, Supervisor, PM2, Docker, or your platform service manager. Serve `frontend/dist` with Nginx or another static web server, and proxy `/api` requests to the backend.

## Environment Files

Do not commit real `.env` files. Use the example files as templates:

- Root backend config: `.env.example` -> `.env`
- Frontend config: `frontend/.env.example` -> `frontend/.env`

Common frontend setting:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Common backend setting:

```text
APP_NAME="Oxo Tracker"
APP_ENV=local
CONNECTORS="./data/moonshot-data/connectors"
CONNECTORS_ENDPOINTS="./data/moonshot-data/connectors-endpoints"
```

## Custom Connector Notes

The configurable connector flow stores custom connector endpoints under:

```text
data/moonshot-data/connectors-endpoints
```

Runtime endpoint JSON files are local data and should not contain secrets committed to Git. The reusable connector implementation is bundled in this repository at:

```text
app/integrations/moonshot/assets/configurable-app-connector.py
```

When the backend starts, it syncs that implementation into Moonshot's connector directory:

```text
data/moonshot-data/connectors/configurable-app-connector.py
```

In the Agents -> Connector UI, create a connector endpoint by providing:

- Full request URL, such as `http://10.255.25.153:5000/chat`.
- Optional authentication headers.
- Request body template with the prompt placeholder.
- Sample response body and output extraction path.

## Verification

Backend syntax check:

```bash
python -m py_compile app/api/routes/moonshot_explicit.py app/integrations/moonshot/assets/configurable-app-connector.py
```

Frontend build check:

```bash
cd frontend
npm run build
```

Run backend tests:

```bash
pytest
```

## Troubleshooting

### Frontend cannot reach backend

Check `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Restart the Vite dev server after changing `.env`.

### Port already in use

Use another backend port:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Then update `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8002
```

### Moonshot assets are missing

Reinstall Moonshot data:

```bash
cd data
../.venv/bin/python -m moonshot -i moonshot-data -u
cd ..
```

On Windows, replace `../.venv/bin/python` with `..\.venv\Scripts\python.exe`.

### Windows dependency installation fails on TensorFlow

Use:

```powershell
pip install -r requirements-moonshot-data-windows.txt
```

Then install language resources:

```powershell
python -m nltk.downloader punkt stopwords
python -m spacy download en_core_web_lg
```
