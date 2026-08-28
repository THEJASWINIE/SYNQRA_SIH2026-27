# FOG-ORCHESTRATOR 2.0 — Task 1 HMI

Operator/control-room Human-Machine Interface for FOG-ORCHESTRATOR 2.0.

**Current stage: M1 — Foundation.** The application is a verified full-stack shell: a React
frontend, a FastAPI backend, and a health endpoint proving they talk to each other. There
are no HMI screens yet.

> **The HMI is advisory only.** It computes no safe speed, headway, risk, bottleneck score,
> queue prediction, dispatch assignment or route. Those are Task 2 (Digital Twin) values,
> received through a data interface and visualized. See
> [`docs/adr/ADR-001-hmi-advisory-only.md`](docs/adr/ADR-001-hmi-advisory-only.md).

## Authoritative documents

| Document | What it governs |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Project rules, scope boundary, provisional architecture decisions |
| `docs/FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf` | The functional specification |
| [`requirements/DECISIONS.md`](requirements/DECISIONS.md) | Decision register; controls the frozen planning baseline |
| [`requirements/task1-implementation-plan.md`](requirements/task1-implementation-plan.md) | Milestones M1–M13 |

Planning Baseline **v1.1**, frozen. Planning documents change only through the revision
rule in `DECISIONS.md` §1.3.

## Prerequisites

| Tool | Version used | Check |
|---|---|---|
| Node.js | 24.18.0 (Node 20+ works) | `node -v` |
| npm | 11.16.0 | `npm -v` |
| Python | 3.12.10 (3.11+ required) | `python --version` |

## Clean-machine setup

From a fresh checkout. Two terminals; run the backend first.

### 1. Backend

Commands differ per shell. Pick your row and use it throughout — the activation command,
the copy command and the path separator all change together.

**Windows — PowerShell** (`pwsh` or `powershell`)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

If activation is blocked by execution policy — `... cannot be loaded because running
scripts is disabled on this system` — allow signed local scripts for your user, once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**Windows — Command Prompt** (`cmd.exe`)

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate.bat
pip install -e ".[dev]"
copy .env.example .env
```

**Windows — Git Bash / MSYS2**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env
```

**Linux / macOS**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Note the difference: on Windows the scripts live in `.venv/Scripts/`, on Linux and macOS in
`.venv/bin/`. `source .venv/Scripts/activate` works **only** in Git Bash — it fails in
PowerShell and in Command Prompt, which need `Activate.ps1` and `activate.bat`
respectively.

Confirm activation before continuing — the prompt should be prefixed `(.venv)`:

```
python -c "import sys; print(sys.prefix)"
```

It must print a path ending in `backend\.venv` (or `backend/.venv`). If it prints your
system Python instead, activation did not take effect.

### 2. Frontend

`npm install` is identical in every shell; only the copy command differs.

**Windows — PowerShell**

```powershell
cd frontend
npm install
Copy-Item .env.example .env
```

**Windows — Command Prompt**

```bat
cd frontend
npm install
copy .env.example .env
```

**Git Bash / Linux / macOS**

```bash
cd frontend
npm install
cp .env.example .env
```

## Running

### Backend — terminal 1

Activate the virtual environment first, using your shell's command from the setup section
above. Then, identically in every shell:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If `uvicorn` is not found, the virtual environment is not active. Either activate it, or
call it through the interpreter without activating:

```bash
# Windows
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# Linux / macOS
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Serves:
- `http://127.0.0.1:8000/api/health` — health endpoint
- `http://127.0.0.1:8000/docs` — interactive OpenAPI documentation

### Frontend — terminal 2

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The page shows `Backend: Connected` with the service name,
version, milestone, backend timestamp and round-trip time. Stop the backend and press
**Re-check**: it changes to `Backend: Unreachable` with an explanation. It never shows a
stale value as if it were current.

## Health endpoint

`GET /api/health` → `200 OK`

```json
{
  "status": "ok",
  "service": "fog-orchestrator-hmi-backend",
  "version": "0.1.0",
  "milestone": "M1",
  "timestamp": "2026-08-26T06:07:14.379114Z"
}
```

Typed by `HealthResponse` in `backend/app/schemas/health.py`. The timestamp is always
timezone-aware — data freshness (NFR-003) depends on unambiguous times from the first line.

> This is the *service* health of the backend process. It is not the `Health` /
> `SystemHealth` contract message from `requirements/task1-data-contract.md` §9, which
> describes Task 2 component and link health and arrives in M2.

## Checks

Run each from its own directory. These are exactly what CI runs.

### Frontend (`cd frontend`)

| Command | What it does |
|---|---|
| `npm run lint` | Biome lint + format check |
| `npm run format` | Apply Biome formatting |
| `npm run typecheck` | `tsc --noEmit`, strict |
| `npm test` | Vitest smoke tests |
| `npm run build` | Type check, then production build |

### Backend (`cd backend`, venv active)

| Command | What it does |
|---|---|
| `ruff check .` | Lint |
| `ruff format --check .` | Format check |
| `pytest -q` | Health endpoint tests |

## Project structure

```
.
├── CLAUDE.md                  Project rules and scope boundary
├── README.md                  This file
├── .env.example               All configurable values, documented in one place
├── .github/workflows/ci.yml   Lint, type check, test, build, secret scan
├── docs/
│   ├── FOG_ORCHESTRATOR_Task1_HMI_Requirements.pdf   The specification
│   └── adr/ADR-001-hmi-advisory-only.md              Architecture record
├── requirements/              Frozen Planning Baseline v1.1 (six documents)
├── backend/
│   ├── pyproject.toml         Dependencies, ruff and pytest configuration
│   ├── .env.example
│   ├── app/
│   │   ├── main.py            FastAPI application; health endpoint; CORS
│   │   ├── config.py          Environment-backed settings — no secrets in source
│   │   └── schemas/health.py  Typed health response
│   └── tests/test_health.py   Backend smoke tests
└── frontend/
    ├── package.json           Dependencies and the commands above
    ├── vite.config.ts         Dev server and Vitest configuration
    ├── tsconfig.json          Strict TypeScript
    ├── biome.json             Lint and format rules
    ├── .env.example
    ├── index.html
    └── src/
        ├── main.tsx             React entry point
        ├── App.tsx              M1 shell — connectivity proof, not a screen
        ├── App.test.tsx         Frontend smoke tests
        ├── api/healthClient.ts  Transport lives here, never in a component
        └── theme/statusTokens.ts  Text + glyph per state; colour is never alone
```

### How to read the frontend

The architecture the HMI must grow into is:

```
External Provider → Normalization Layer → Typed Application State → HMI
```

M1 builds only the outermost edge of that. `api/healthClient.ts` owns the network call and
returns a normalized, typed result; `App.tsx` renders that result and never calls `fetch`
itself. The real `DataProvider` interface, the contract schemas and the normalization layer
are **M2** and are deliberately absent.

`theme/statusTokens.ts` exists from day one because NFR-008 forbids relying on colour alone
for safety state. Every token carries a `label` and a `glyph`; colour is an enhancement.
Retro-fitting that after six screens is how the requirement quietly erodes.

## Configuration

No credential appears in source (NFR-011). All values come from the environment.

| Variable | Side | Default | Purpose |
|---|---|---|---|
| `HMI_HOST` | backend | `127.0.0.1` | Bind address |
| `HMI_PORT` | backend | `8000` | Bind port |
| `HMI_CORS_ORIGINS` | backend | `http://localhost:5173,http://127.0.0.1:5173` | Origins allowed to call the API |
| `VITE_API_BASE_URL` | frontend | `http://127.0.0.1:8000` | Backend base URL |

`.env` is gitignored; `.env.example` is the committed template. Never put a secret in a
`VITE_`-prefixed variable — Vite ships those to the browser.

## Scope

Task 1 owns visualization, monitoring, alerts and operator awareness. It does **not**
implement vehicle physics, fog physics, safe speed or headway calculation, queue
prediction, bottleneck algorithms, dispatch optimization or route optimization. When such a
value is needed, Task 1 defines a typed interface and uses mock data.

Full boundary: [`CLAUDE.md`](CLAUDE.md) and `.claude/skills/scope-control/SKILL.md`.

## What is not built yet

M1 is the foundation only. Still to come: shared schemas and the normalization layer (M2),
mock data and scenarios (M3), the six HMI screens (M4–M10), failure-scenario verification
(M11), Task 2 integration (M12), optional computer vision (M13).
#   H M I  
 