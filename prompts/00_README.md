# SwarmScope Build Prompts — Execution Guide

Run these prompts in order in Claude Code. Each session is self-contained.

## Before You Start

1. Place `SWARM_SCOPE_BUILD_PROMPT.md` in your project root — every session prompt references it
2. Have your **Gemini API key** ready (needed from Session 2 onward)
3. Have **Docker** running (needed from Session 1 onward)

## Execution Order

| # | Prompt File | Phases | What It Builds | Est. Time |
|---|-------------|--------|----------------|-----------|
| 01 | `01_FOUNDATION_AND_BACKEND_CORE.md` | 1-2 | Monorepo, Docker, PostgreSQL, all tables, ORM models, Pydantic schemas, FastAPI shell | 15-20 min |
| 02 | `02_GEMINI_LAYER.md` | 3 | Gemini client, rate limiter, extraction, function calling, embeddings, all prompt templates | 15-20 min + tuning |
| 03 | `03_ENGINE.md` | 4 | World compiler, agent generator, activation, rule engine, decision engine, state manager, memory manager, orchestrator | 25-35 min |
| 04 | `04_API_AND_FRONTEND.md` | 5-6 | All REST endpoints, WebSocket, simulation/report workers, all 7 Angular screens | 30-40 min |
| 05 | `05_AUTH_AND_KNOWLEDGE_GRAPH.md` | 7-8 | JWT auth, D3 knowledge graph, influence tracking, auth interceptor | 20-25 min |
| 06 | `06_REPORTING_SURVEYS_FORKING.md` | 9-10 | Tool-augmented reports, batch surveys, fork-from-tick, scenario library | 25-30 min |
| 07 | `07_ENSEMBLE_MODE.md` | 11 | Multi-run statistics, confidence bands, robustness scores, ensemble viewer | 20-25 min |
| 08 | `08_LIVE_DATA_INGESTION.md` | 12 | Webhook ingestion, scheduled pulls, Gemini summarization, external events feed | 20-25 min |
| 09 | `09_INTEGRATION_AND_POLISH.md` | 13 | E2E testing, error handling, cost dashboard, README | 20-30 min |

**Total estimated time: 3-4 hours of Claude Code execution**

## How to Run Each Session

Open Claude Code and paste:

```
Read the file SWARM_SCOPE_BUILD_PROMPT.md for full architecture context.

Then read and execute the prompt in prompts/0X_SESSION_NAME.md
```

Replace `0X_SESSION_NAME` with the current session file.

## Rules

1. **Never skip a session.** Each depends on the one before it.
2. **Always verify** before moving to the next session. Each prompt ends with a verification checklist.
3. **Session 3 (Engine) is the hardest.** Budget extra time. Don't move on until the 5-agent, 3-tick test works.
4. **Session 2 (Gemini) needs tuning.** The extraction prompts will need 2-3 iterations with real documents.
5. **Test with small numbers first.** Use 5-10 agents and 3-5 ticks until everything works, then scale up.
6. **Keep costs low during development.** Use `GEMINI_BUDGET_PER_RUN_USD=1.00` until production.
