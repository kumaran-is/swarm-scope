# Session 1: Foundation + Backend Core (Phases 1-2)

> **Pre-requisite**: None. This is the first session.
> **Goal**: Monorepo scaffolded, Docker running, PostgreSQL connected, all tables created, backend core implemented.
> **Estimated time**: 15-20 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. That file contains the complete system design including project structure, database schema, engine design, API specs, frontend specs, and all feature details.

Now execute **Phase 1 (Foundation)** and **Phase 2 (Backend Core)** only. Here is exactly what to build:

### Phase 1: Foundation (Steps 1-6)

1. **Initialize the monorepo structure** — Create the full directory layout as specified in Section 1 of the build prompt. Include all directories: `backend/app/models/`, `backend/app/schemas/`, `backend/app/api/`, `backend/app/engine/`, `backend/app/gemini/`, `backend/app/workers/`, `backend/app/utils/`, `frontend/`, `infra/`. Add `__init__.py` files to all Python packages.

2. **Set up `pyproject.toml`** with these dependencies:
   - `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`
   - `google-genai`, `redis`, `python-multipart`, `pypdf`, `python-docx`
   - `python-jose[cryptography]`, `passlib[bcrypt]`, `numpy`, `httpx`
   - Pin Python `>=3.14`
   - Use `uv` or `poetry` as the package manager

3. **Set up Angular 21 project**: Run `ng new frontend --standalone --style=scss --routing` inside the `frontend/` directory. Configure `angular.json` and `tsconfig.json`.

4. **Create `docker-compose.yml`** as specified in Section 7 of the build prompt:
   - `backend` service (FastAPI on port 8000)
   - `frontend` service (nginx on port 4200)
   - `postgres` service (PostgreSQL 17 on port 5432)
   - `redis` service (Redis 7 on port 6379)
   - Create `infra/Dockerfile.backend` and `infra/Dockerfile.frontend`

5. **Create Alembic config and initial migration** with ALL tables from Section 2 of the build prompt:
   - `scenarios` — UUID PK, name, description, source_file_path, source_text, domain, config JSONB, status, user_id FK
   - `world_models` — UUID PK, scenario_id FK, summary, entities/factions/resources/constraints/tensions/kpis as JSONB
   - `agents` — UUID PK, scenario_id FK, name, role, faction, personality JSONB, goals JSONB, resources JSONB, status, is_chat_enabled, activation_score, working/episodic/semantic memory as JSONB
   - `simulation_runs` — UUID PK, scenario_id FK, random_seed, status, current_tick, max_ticks, config JSONB, ensemble_run_id FK, ensemble_seed_index, forked_from_tick_id FK
   - `ticks` — UUID PK, simulation_run_id FK, tick_number, phase, active_agent_ids, events JSONB, world_state_delta, kpi_values, snapshot, interventions_applied, duration_ms, gemini_calls, gemini_tokens_used
   - `interventions` — UUID PK, simulation_run_id FK, type, payload JSONB, description, target_tick, applied_at_tick, status
   - `reports` — UUID PK, simulation_run_id FK, executive_summary, narrative, timeline JSONB, influence_graph JSONB, key_findings JSONB, kpi_trajectories JSONB, counterfactual_notes
   - `users` — UUID PK, email UNIQUE, password_hash, api_key UNIQUE
   - `influence_edges` — UUID PK, simulation_run_id FK, source_agent_id FK, target_agent_id FK, action_type, tick_number, weight, context
   - `ensemble_runs` — UUID PK, scenario_id FK, user_id FK, ensemble_size, base_config JSONB, status, statistics JSONB
   - `surveys` — UUID PK, simulation_run_id FK, question, target_agent_ids, response_format, responses JSONB, aggregate_analysis JSONB
   - `ingestion_sources` — UUID PK, scenario_id FK, name, source_type, config JSONB, webhook_secret, mapping_rules JSONB, is_active, rate_limit_per_minute
   - `ingested_events` — UUID PK, ingestion_source_id FK, simulation_run_id FK, raw_payload JSONB, processed_intervention JSONB, intervention_id FK, status, rejection_reason

6. **Create `.env.example`** as specified in Section 8 of the build prompt. Include all Gemini, Database, Redis, App, Ensemble, and Ingestion environment variables.

### Phase 2: Backend Core (Steps 7-12)

7. **Implement `config.py`** — Use Pydantic Settings to load all env vars. Create a `Settings` class with fields for every env var in `.env.example`. Use `@lru_cache` for singleton access.

8. **Implement all SQLAlchemy ORM models** in `backend/app/models/`:
   - `scenario.py`, `world.py`, `agent.py`, `simulation.py`, `intervention.py`, `report.py`
   - `user.py`, `ensemble.py`, `ingestion.py`
   - Use `mapped_column`, `Mapped` type hints (SQLAlchemy 2.0 style)
   - All UUIDs use `server_default=text("gen_random_uuid()")`

9. **Implement all Pydantic v2 schemas** in `backend/app/schemas/`:
   - Request and response schemas for every model
   - Use `model_config = ConfigDict(from_attributes=True)`

10. **Implement `dependencies.py`** — Dependency injection functions:
    - `get_db()` → async SQLAlchemy session
    - `get_redis()` → Redis client
    - `get_gemini_client()` → Gemini client (placeholder for now)
    - `get_current_user()` → JWT-decoded user (placeholder for now)

11. **Implement `main.py`** — FastAPI app factory:
    - CORS middleware for `http://localhost:4200`
    - Lifespan handler for DB engine creation/disposal
    - Mount the top-level router (empty for now)
    - Health check endpoint at `GET /health`

12. **Implement file parser utility** in `backend/app/utils/file_parser.py`:
    - `parse_file(file_path: str) -> str` — detects file type and extracts plain text
    - PDF via `pypdf`, DOCX via `python-docx`, TXT/MD read directly
    - Max file size: 50MB

### Verification Checklist

After completing both phases, verify:

- [ ] `docker-compose up` starts all 4 services without errors
- [ ] PostgreSQL is accessible on port 5432
- [ ] `alembic upgrade head` creates all tables
- [ ] `GET http://localhost:8000/health` returns 200
- [ ] All Python imports work (no circular dependencies)
- [ ] All Pydantic schemas can serialize/deserialize from ORM models

**STOP after verification. Do not proceed to Phase 3.**
