# Session 5: Authentication + Knowledge Graph + Influence Tracking (Phases 7-8)

> **Pre-requisite**: Sessions 1-4 complete. Full end-to-end flow works in browser.
> **Goal**: JWT auth on all endpoints, interactive knowledge graph visualization, live influence tracking.
> **Estimated time**: 20-25 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. Pay attention to **Sections 10.1 (Authentication)**, **10.2 (Knowledge Graph)**, and **10.4 (Influence Tracking)**.

Now execute **Phase 7 (Authentication)** and **Phase 8 (Knowledge Graph & Influence Tracking)**.

### Phase 7: Authentication & Security (Steps 41-43)

41. **Implement User model + JWT auth**:
    - `backend/app/models/user.py` — User SQLAlchemy model (already in migration, now implement ORM class)
    - `backend/app/schemas/auth.py` — `RegisterRequest(email, password)`, `LoginRequest(email, password)`, `TokenResponse(access_token, refresh_token, token_type)`
    - `backend/app/api/auth.py` — Three endpoints:
      - `POST /api/v1/auth/register` — hash password with `passlib[bcrypt]`, create user, return tokens
      - `POST /api/v1/auth/login` — verify password, return JWT tokens
      - `POST /api/v1/auth/refresh` — validate refresh token, return new access token
    - JWT tokens via `python-jose`: access token (30 min expiry), refresh token (7 day expiry)
    - Secret key from `APP_SECRET_KEY` env var

42. **Add `get_current_user` dependency**:
    - Update `backend/app/dependencies.py` — decode JWT from `Authorization: Bearer` header
    - Add `current_user: User = Depends(get_current_user)` to ALL existing route handlers
    - Scope all database queries to `user_id = current_user.id` (scenarios, simulations, reports)
    - Auth endpoints (`/auth/*`) are exempt

43. **Build login/register Angular components**:
    - `frontend/src/app/features/auth/login.component.ts` — email + password form, calls login endpoint, stores token in memory
    - `frontend/src/app/features/auth/register.component.ts` — email + password + confirm password form
    - `frontend/src/app/core/interceptors/auth.interceptor.ts` — attach `Authorization: Bearer` header to all API requests
    - `frontend/src/app/core/guards/auth.guard.ts` — redirect to `/auth/login` if no token
    - Add auth guard to all routes except `/auth/*`
    - Store tokens in a Signal-based `auth.state.ts` (in memory, NOT localStorage)
    - On 401 response: clear token, redirect to login

### Phase 8: Knowledge Graph & Influence Tracking (Steps 44-48)

44. **Implement knowledge graph endpoint**:
    - `GET /api/v1/scenarios/{id}/knowledge-graph` returns D3-compatible JSON:
      ```json
      {
        "nodes": [
          {"id": "uuid", "label": "Entity Name", "type": "entity|faction", "group": "faction_name", "size": 10}
        ],
        "edges": [
          {"source": "uuid1", "target": "uuid2", "label": "relationship", "type": "tension|alliance|resource_flow", "weight": 0.8}
        ]
      }
      ```
    - Built from `world_models` table: entities become nodes, tensions/relationships become edges
    - Factions get a distinct node type (hexagon vs circle in frontend)

45. **Build knowledge-graph-viewer Angular component** (`frontend/src/app/shared/components/knowledge-graph-viewer/`):
    - D3.js force simulation embedded in Angular component
    - Nodes: circles for entities, hexagons for factions
    - Node size proportional to `resources` or `influence` value
    - Edge color: red for tensions, green for alliances, blue for resource flows
    - Edge thickness proportional to weight/intensity
    - Hover: show node/edge details tooltip
    - Click: emit selected node event (used by World Editor for edit-on-click)
    - Zoom and pan support
    - Responsive: fills container width/height

46. **Integrate knowledge graph into screens**:
    - **World Editor**: left panel shows knowledge graph. Clicking a node opens that entity/faction in the right panel for editing. Graph updates when user saves edits.
    - **Live Dashboard**: read-only knowledge graph. Updates per tick as relationships change. New edges animate in. Add a toggle to show/hide.

47. **Implement influence tracker** (`backend/app/engine/influence_tracker.py`):
    - `track_influence(simulation_run_id, tick, decisions) -> list[InfluenceEdge]`
    - For each agent decision that targets another agent, create an `influence_edges` record:
      - `form_alliance` → weight +2.0
      - `influence_agent` → weight +1.5
      - `publish_statement` → weight +0.5 (targets whole faction, create edge to faction leader)
      - `escalate_conflict` → weight -2.0
      - `de_escalate_conflict` → weight +1.0
      - `break_alliance` → weight -1.5
      - `reallocate_resource` → weight +0.5 if giving, -0.5 if taking
    - Integrate into orchestrator: call `track_influence()` after state update (between step 5 and 6)

48. **Build influence graph endpoints and integrate**:
    - `GET /api/v1/simulations/{id}/influence-graph` — returns accumulated influence graph:
      ```json
      {
        "nodes": [{"id": "agent_uuid", "label": "Agent Name", "faction": "...", "total_influence": 15.5}],
        "edges": [{"source": "uuid1", "target": "uuid2", "weight": 3.5, "actions": ["form_alliance", "influence_agent"]}]
      }
      ```
    - `GET /api/v1/simulations/{id}/influence-graph/agent/{aid}` — ego network for one agent
    - Update `influence-graph` shared component to render this data
    - Live Dashboard: influence graph updates each tick via WebSocket
    - Report Viewer: final influence graph as a static D3 visualization

### Verification Checklist

- [ ] Register a new user → get tokens back
- [ ] Login → get access + refresh tokens
- [ ] Access scenarios without token → 401
- [ ] Access scenarios with token → works, only sees own data
- [ ] Create two users → each only sees their own scenarios
- [ ] Token expires → refresh endpoint returns new access token
- [ ] World Editor shows knowledge graph with entities and tensions
- [ ] Click entity node in graph → right panel opens that entity for editing
- [ ] Run a simulation → Live Dashboard influence graph updates per tick
- [ ] After simulation → influence graph endpoint returns accumulated edges
- [ ] Report Viewer shows final influence graph

**STOP after verification. Do not proceed to Phase 9.**
