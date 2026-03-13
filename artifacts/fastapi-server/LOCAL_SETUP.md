# Local Setup — FastAPI SQL Agent

Multi-agent LangGraph pipeline that converts natural language into validated SAP HANA SQL.

---

## Prerequisites

- **Python 3.11+** (`python --version` to check)
- **pip** or **pip3**
- An **OpenAI API key** (from https://platform.openai.com/api-keys)

---

## Step 1 — Clone / copy the server folder

If you are working from the Replit project, download or copy the
`artifacts/fastapi-server/` folder to your machine.

---

## Step 2 — Create a virtual environment

```bash
cd artifacts/fastapi-server

python -m venv .venv

# Activate it:
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Set environment variables

The server expects two env vars for OpenAI access.

### Option A — export in your terminal (quick)

```bash
# macOS / Linux
export AI_INTEGRATIONS_OPENAI_BASE_URL="https://api.openai.com/v1"
export AI_INTEGRATIONS_OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:AI_INTEGRATIONS_OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:AI_INTEGRATIONS_OPENAI_API_KEY  = "sk-..."
```

### Option B — .env file (recommended)

Create a file called `.env` inside `artifacts/fastapi-server/`:

```
AI_INTEGRATIONS_OPENAI_BASE_URL=https://api.openai.com/v1
AI_INTEGRATIONS_OPENAI_API_KEY=sk-...
```

Then load it before starting the server (the server uses `python-dotenv` to pick it up automatically if you add the load call — see note below).

---

## Step 5 — Start the server

```bash
# From inside artifacts/fastapi-server/
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## Step 6 — Test it

### Health check
```bash
curl http://localhost:8000/healthz
# {"status":"ok","service":"fastapi-sql-agent"}
```

### List tables
```bash
curl http://localhost:8000/sql-agent/tables
```

### Generate SQL from natural language
```bash
curl -X POST http://localhost:8000/sql-agent/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me the top 5 customers by total order value this year", "max_iterations": 3}'
```

### Swagger UI (interactive docs)
Open in your browser: http://localhost:8000/docs

---

## Adding new tables

Edit `table_registry.py` — add a new `TableDefinition` to the `TABLE_REGISTRY` list.
All three agents automatically pick up the change on the next request (no restart needed with `--reload`).

---

## Project structure

```
artifacts/fastapi-server/
├── main.py              ← FastAPI app, routes
├── graph.py             ← LangGraph orchestration (3-agent loop)
├── state.py             ← Shared TypedDict state schema
├── table_registry.py    ← Plug-and-play HANA table definitions
├── requirements.txt     ← Python dependencies
└── agents/
    ├── schema_extractor.py   ← Agent 1: picks relevant tables
    ├── sql_generator.py      ← Agent 2: writes HANA SQL
    └── sql_validator.py      ← Agent 3: validates & gives feedback
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure your venv is activated and `pip install -r requirements.txt` ran |
| `AuthenticationError` | Check your `AI_INTEGRATIONS_OPENAI_API_KEY` is correct and exported |
| Port 8000 already in use | Run `lsof -i :8000` and kill the process, or use `--port 8001` |
| `gpt-5.2` model not found | Change `model="gpt-5.2"` to `"gpt-4o"` or `"gpt-4-turbo"` in each `agents/*.py` file |
