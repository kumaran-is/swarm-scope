# SwarmScope — Scenario Simulation Lab

A multi-agent scenario simulation platform powered by Google Gemini. Upload a source document, compile a world model, spawn an agent population, and watch them interact across hundreds of ticks — with real-time dashboards, interventions, surveys, ensemble statistics, and AI-generated reports.

---

## Key Features

1. **Gemini-Powered Agents** — Every agent decision is a structured Gemini call with function calling
2. **Selective Activation** — Activation scoring limits Gemini calls to top-K agents per tick (cost control)
3. **3-Layer Agent Memory** — Working (per-tick), episodic (rolling 20 entries), semantic (compressed long-term)
4. **Deterministic Replay** — Seeded `random.Random` instance ensures reproducible simulations
5. **Real-Time WebSocket Feed** — Browser receives tick-complete events as the simulation runs
6. **Intervention Console** — Inject events, modify KPIs, or send agent directives mid-simulation
7. **Fork from Any Tick** — Branch a simulation from a saved snapshot with a new seed
8. **Ensemble Mode** — Run N simulations, aggregate KPI confidence bands and robustness scores
9. **Tool-Augmented Reports** — Gemini queries tick data, interviews agents, and traces causal chains
10. **Batch Agent Surveys** — Ask all agents a question; get sentiment analysis and consensus scores
11. **Live Data Ingestion** — Webhooks and scheduled API pulls auto-become interventions
12. **Knowledge Graph** — D3 force-directed graph of entities, factions, and tensions

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic |
| AI | Google Gemini 2.5 Pro (structured output + function calling + embeddings) |
| Database | PostgreSQL 17 + Redis 7 |
| Frontend | Angular 21 (standalone components, Signals, D3.js) |
| Infrastructure | Docker Compose, nginx |

---

## Prerequisites

- Docker + Docker Compose
- Node.js 22+
- Python 3.12+ with `uv`
- Google Gemini API key

---

## Quick Start

```bash
cp env.example .env
# Edit .env — set GEMINI_API_KEY and APP_SECRET_KEY

docker-compose up --build
# Open http://localhost:4200
```

### Development (hot reload)

```bash
# Backend
cd backend
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm start
```

---

## Architecture Overview

### Tick Loop (10 steps)

```
0. Check ingestion sources (webhook events → interventions)
1. Apply pending interventions
2. Score all agents (0.0–1.0), select top K=15
3. Evaluate deterministic rules (proximity, resource, weather)
4. Get Gemini decisions for activated agents (asyncio.Semaphore(5))
5. Apply state delta (resources, relationships, world KPIs)
6. Compress agent memories (episodic → semantic via Gemini)
7. Evaluate KPI thresholds
8. Save tick snapshot (for fork-from-tick)
9. Log events to DB
10. Broadcast via WebSocket
```

### 3-Layer Agent Memory

- **Working memory** — reset each tick (current perceptions, recent actions)
- **Episodic memory** — rolling 20 entries (what happened, with timestamps)
- **Semantic memory** — Gemini-compressed long-term patterns (rebuilt when episodic overflows)

### Selective Activation Formula

```
score = 0.3 × stress + 0.2 × resource_deficit + 0.2 × goal_proximity
      + 0.15 × relationship_tension + 0.15 × random_jitter(seed)
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL async URL |
| `REDIS_URL` | Yes | Redis connection URL |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `APP_SECRET_KEY` | Yes | JWT signing secret (min 32 chars) |
| `APP_ENV` | No | `development` or `production` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `MAX_UPLOAD_SIZE_MB` | No | File upload limit (default: 10) |

---

## API Documentation

FastAPI auto-generates interactive docs at: `http://localhost:8000/docs`

Key endpoint groups:
- `POST /api/v1/auth/register` — create account
- `POST /api/v1/auth/token` — login (returns JWT)
- `POST /api/v1/scenarios` — upload scenario document
- `POST /api/v1/simulations` — start simulation
- `WS /api/v1/ws/{sim_id}` — real-time tick feed
- `POST /api/v1/ensembles` — launch ensemble run
- `POST /api/v1/webhooks/ingest/{source_id}` — receive external events

---

## MVP Scope and Limitations

- No multi-tenancy beyond per-user data scoping
- Gemini rate limits apply (~60 RPM on free tier); use `max_agents=10` for testing
- WebSocket state is in-process; not horizontally scalable without Redis pub/sub
- Alembic migrations require `DATABASE_URL` to be set; Docker Compose handles this
- Report generation and ensemble runs can take several minutes with many agents

---

## License

MIT
