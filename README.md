# Oxo Tracker

Oxo Tracker is a Tauri v2 desktop application for testing model agents, prompt safety, connector behavior, and red-team resilience. It combines a Rust desktop host, a FastAPI Python sidecar, a Vue 3 workspace, and local Moonshot assets so evaluation teams can configure targets, run benchmark suites, inspect prompt traces, and keep adversarial conversations in one place.

The product is designed for AI security review workflows where teams need repeatable tests, visible evidence, and side-by-side comparison between clean and attacked interactions.

![Benchmark run details](docs/images/benchmark-run-details.png)

## Product Highlights

- **Benchmark orchestration**: launch cookbook and recipe based evaluations against selected model endpoints, then inspect progress, prompt traces, errors, reports, and downloadable run output.
- **Red-team workspace**: maintain adversarial chat sessions with payload selection, attack-module controls, context strategy options, and clean comparison conversations.
- **Payload library**: browse and curate cookbooks, recipes, datasets, attack modules, and prompt templates used by evaluation runs.
- **Agent and connector management**: create model endpoints and configurable connectors for HTTP, SSE, and WebSocket based AI applications.
- **Agent security review**: upload design documents, diagrams, prompts, tool specs, and screenshots to extract application functions and build a review map.
- **Local-first evidence store**: keep benchmark jobs, red-team sessions, settings, and generated reports in the desktop application's identifier-scoped local data directory.
- **Persistent Attack Agent**: run Planner → Executor → target → AI WATCH workflows in the background with LangGraph checkpoints, prompt-only Skills, pause/resume/stop controls, and no default fixed round limit.

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

The primary product architecture is Tauri v2 + Vue 3 + a Python sidecar:

- Desktop host: Tauri v2/Rust owns the window, process lifecycle, per-launch session token, loopback health check, and sidecar shutdown.
- Backend: FastAPI provides API orchestration, Moonshot adapters, local job runtime, settings, and report stores.
- Frontend: Vue 3, Vite, Pinia, and Naive UI run inside the system WebView2 runtime.
- Data: packaged releases keep mutable data under `%LOCALAPPDATA%\com.oxoai.oxo-tracker`; desktop development uses the separate `%LOCALAPPDATA%\com.oxoai.oxo-tracker-development` directory.
- Models: product features call user-configured online model APIs. No local model runtime or model weights are required.

The browser-only frontend/backend workflow remains available for isolated debugging, but normal product development should use the desktop development command described below.

## Project Layout

```text
app/                         FastAPI backend
  api/routes/                 HTTP API routes
  core/                       configuration and startup wiring
  integrations/moonshot/      Moonshot adapter code
  schemas/                    request/response schemas
  services/                   application services
frontend/                     Vue 3 + Vite + Naive UI frontend
  src-tauri/                  Tauri v2 host, capabilities, icons, and bundle config
desktop/                      desktop asset policy and PyInstaller specification
data/
  moonshot-data/              Moonshot assets installed locally
  jobs/                       local benchmark job runtime data
  redteam_sessions/           local red-team session runtime data
  task_agent_v2/              persistent Attack Agent state and checkpoints
scripts/                      setup/test helper scripts
  dev-desktop.ps1             source-mode desktop development launcher
  build-desktop.ps1           local Windows installer build
  release-desktop.ps1         signed local release build
tests/                        backend tests
```

## Persistent Attack Agent

In a Red Team chat, click **Attack Agent**, enter an observable research goal, and select **Set Goal**. The task continues in the backend when you switch pages or refresh. AI WATCH is enabled automatically; success records retain the exact request, response, evidence, and progress, then the composer returns to normal so another goal can be entered.

The gear button to the right of Attack Agent opens prompt-only Executor Skills and a plain-Vue three-agent workflow view. Default execution is `guarded_unbounded` with `max_rounds=null`. Executor messages are sent directly to the configured target. AI WATCH records P0-P3 findings without stopping the task; target failures, optional budgets, pause, resume, and manual stop remain enforced.

See:

- [Task Agent V2 architecture](docs/task-agent-architecture-v2.md)
- [Task Agent system prompts](docs/task-agent-system-prompts-v2.md)
- [OSAI notes to Skill mapping](docs/osai-notes-skill-mapping.md)
- [Migration and operation guide](docs/task-agent-migration-guide.md)

## Prerequisites

- Python 3.11.x. The project currently targets `>=3.11,<3.12`.
- Node.js 20+ and npm.
- Rust stable installed with `rustup`.
- Visual Studio Build Tools with **Desktop development with C++**, or the documented portable LLVM/cargo-xwin fallback.
- Microsoft Edge WebView2 Runtime.
- Git.
- Network access for Python and npm dependency installation.

Browser-only development defaults:

- Backend: `http://127.0.0.1:8001`
- Frontend: `http://127.0.0.1:5173`

Desktop development keeps Vite on `127.0.0.1:5173`, while the managed Python sidecar receives a random loopback port for each launch.

## Windows Desktop Development (Primary)

Run the commands from PowerShell in the project root.

### 1. Clone the repository

```powershell
git clone https://github.com/Oxo-AI-Security/Oxo-Tracker.git
cd Oxo-Tracker
```

### 2. Bootstrap the source-mode backend and Moonshot assets

```powershell
.\scripts\bootstrap.ps1
```

The bootstrap script creates `.venv`, installs the same local-model-free dependency set used by desktop releases plus pytest, creates `.env`, installs Moonshot assets when absent, and downloads only the required NLTK language data. It does not install spaCy models, TensorFlow, PyTorch, Transformers, or local model weights.

If PowerShell blocks scripts, allow them only for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\bootstrap.ps1
```

### 3. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### 4. Start the desktop application directly from source

```powershell
cd frontend
npm run desktop:dev
```

This is the default daily development workflow. It does **not** run PyInstaller, NSIS, or create an installer. The launcher:

- starts `app.desktop_server` directly with `.venv\Scripts\python.exe`;
- uses the source `data\moonshot-data` directory without copying 500 MiB of assets;
- allocates a random loopback port and a new 64-character session token;
- starts Vite and the Tauri development window;
- applies a development-only Tauri config that does not require packaged sidecar binaries or resources;
- keeps frontend hot module replacement enabled;
- stops the Python process when the Tauri process exits.

Backend source changes require restarting `npm run desktop:dev`; frontend changes update through Vite HMR. Calling `tauri dev` directly is intentionally rejected because it would bypass the managed Python development backend.

The desktop window uses an integrated title area instead of the native Windows title bar. The custom minimize and close buttons both keep Oxo Tracker running in the taskbar. To exit completely, right-click the Oxo Tracker taskbar entry and choose **Close window**; this sends the native close request that shuts down the Tauri host and Python sidecar together.

### Optional browser-only development

Use this only when debugging the backend or Vue UI independently. Start the backend in one terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Backend API docs are available at:

```text
http://127.0.0.1:8001/docs
```

Then start the browser frontend in another terminal:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

## Linux Browser Development (Optional)

The packaged desktop target is currently Windows x64. Linux can still run the browser-only development workflow.

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
pip install -r requirements-dev.txt
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

Install the lightweight language data used by supported metrics:

```bash
python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger_eng stopwords
```

Do not install the Moonshot asset repository's full requirements file; it includes local-model stacks that Oxo Tracker does not use.

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

## Windows Desktop Build and Manual Release

An unsigned engineering installer can be built locally for validation:

```powershell
.\scripts\build-desktop.ps1 -Version 0.1.0 -AllowUnsigned
```

A formal release requires a clean Git worktree, an Authenticode certificate, and the Tauri updater signing key pair. Generate the updater key once, store it outside the repository, and back up both the private key and its password:

```powershell
cd frontend
npm run tauri signer generate -- -w "$env:USERPROFILE\.tauri\oxo-tracker.key"
cd ..
$env:TAURI_SIGNING_PRIVATE_KEY_PATH="$env:USERPROFILE\.tauri\oxo-tracker.key"
```

The public key is safely committed as `frontend/src-tauri/updater.pubkey` so every future client verifies the same publisher key. If the private key is password protected, set `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` in the same terminal. Do not save the private key or its password in `.env` or Git. Then build the formal release:

```powershell
.\scripts\release-desktop.ps1 -Version 1.0.0 -CertificateThumbprint <certificate-thumbprint>
```

The build creates an NSIS per-user installer plus its Tauri `.sig`, SHA-256, SBOM, third-party notices, dataset manifest, release notes, and an OSS-ready `latest.json` under `artifacts\desktop-release\<version>`. There is no GitHub Actions workflow and the scripts do not upload anything. Upload the installer and release files to [Oxo-AI-Security/Oxo-Tracker-Releases](https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases) first; upload `latest.json` to `oss://oxotracker/stable/latest.json` only after the GitHub Release is complete.

## Environment Files

Do not commit real `.env` files. Use the example files as templates:

- Root backend config: `.env.example` -> `.env`
- Frontend config: `frontend/.env.example` -> `frontend/.env` for browser-only development.

Desktop development receives its random API URL and token from the launcher; it does not use `VITE_API_BASE_URL`.

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

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run frontend tests and Rust formatting checks:

```powershell
cd frontend
npm test -- --run
cd src-tauri
cargo fmt --check
```

## Troubleshooting

### Desktop development does not start

Always use the managed launcher:

```powershell
cd frontend
npm run desktop:dev
```

Confirm `.venv\Scripts\python.exe`, `data\moonshot-data\datasets`, Rust, Visual Studio Build Tools, and WebView2 are present. Running `tauri dev` directly is unsupported because it does not start the Python source backend.

### Browser frontend cannot reach backend

Check `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Restart the Vite dev server after changing `.env`.

### Port already in use

The desktop launcher requires `127.0.0.1:5173` and stops before opening Tauri when another process owns that port. Close the existing Vite/browser-development process, then run `npm run desktop:dev` again. This guard prevents Tauri from loading a stale development page.

For browser-only backend development, use another backend port:

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

### Rust cannot find a Windows linker

Install Visual Studio Build Tools with the **Desktop development with C++** workload, then open a new PowerShell terminal. The local scripts can also use an existing LLVM/LLD and cargo-xwin SDK cache when Build Tools are unavailable.

Do not solve desktop dependency errors by installing TensorFlow, PyTorch, spaCy models, Transformers, Ollama, or model weights; these are outside the supported product architecture.

### Start with fresh development settings

Desktop development keeps settings separate from installed releases at:

```text
%LOCALAPPDATA%\com.oxoai.oxo-tracker-development
```

Close the application before moving this directory to the Recycle Bin. Source Moonshot assets under `data\moonshot-data` are not removed.
