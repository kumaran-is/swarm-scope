# Session 8: Live External Data Ingestion (Phase 12)

> **Pre-requisite**: Sessions 1-7 complete. Ensemble mode works.
> **Goal**: External data (webhooks, scheduled API pulls) automatically become interventions in running simulations.
> **Estimated time**: 20-25 minutes

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context. Pay attention to **Section 10.9 (Live External Data Ingestion)** which contains the complete spec.

Now execute **Phase 12 (Live External Data Ingestion)** only.

### Phase 12: Live External Data Ingestion (Steps 62-70)

62. **Implement ingestion models** — ORM models for `ingestion_sources` and `ingested_events` tables (already in migration from Session 1):
    - `backend/app/models/ingestion.py` — `IngestionSource` and `IngestedEvent` models
    - `backend/app/schemas/ingestion.py` — request/response schemas:
      - `IngestionSourceCreate(name, source_type, config, mapping_rules, rate_limit_per_minute)`
      - `IngestionSourceResponse`, `IngestedEventResponse`
      - `WebhookPayload` (generic dict)

63. **Implement ingestion handler** (`backend/app/engine/ingestion_handler.py`):
    ```python
    class IngestionHandler:
        async def process_webhook_event(self, source_id: UUID, payload: dict) -> IngestedEvent:
            """
            1. Load ingestion source config + mapping rules
            2. Check rate limit (count events in last minute for this source)
            3. Extract event description using mapping_rules.event_field from payload
            4. If mapping_rules.gemini_summarize == True:
               - Call Gemini with INGESTION_SUMMARIZE_PROMPT:
                 "Given this external event and the world model, describe impact"
                 Input: {raw_event_text, world_model_summary}
                 Output: {event_description, severity, affected_entities, suggested_impact}
            5. Create intervention record: type='inject_event', payload={description, severity, source}
            6. Create ingested_event record linking to intervention
            7. Push WebSocket notification: external_event_ingested
            """
            pass
        
        async def run_scheduled_pull(self, source: IngestionSource, simulation_run_id: UUID) -> list[IngestedEvent]:
            """
            1. Fetch from source.config.url using httpx (async)
            2. Extract events array from response using config.response_path (JSONPath-like)
            3. For each event: process same as webhook (steps 3-7 above)
            4. Respect global rate limit: MAX_INGESTED_EVENTS_PER_TICK
            """
            pass
        
        def _check_rate_limit(self, source_id: UUID) -> bool:
            """Count events received in last 60 seconds. Return False if over limit."""
            pass
        
        async def _gemini_summarize(self, raw_text: str, world_summary: str) -> dict:
            """Call Gemini to convert raw external data into simulation-meaningful event."""
            pass
    ```

64. **Implement ingestion worker** (`backend/app/workers/ingestion_worker.py`):
    ```python
    class IngestionWorker:
        async def check_sources(self, simulation_run_id: UUID, current_tick: int) -> list[IngestedEvent]:
            """
            Called by orchestrator at the START of each tick (Step 0).
            
            1. Load all active ingestion_sources for this scenario
            2. For each source with source_type='scheduled_pull':
               - Check if current_tick % poll_interval_ticks == 0
               - If due: run scheduled pull
            3. Return all new ingested events (both from scheduled pulls and any
               pending webhook events received since last tick)
            """
            pass
    ```

65. **Implement webhook receiver endpoint**:
    ```python
    # backend/app/api/webhooks.py
    
    @router.post("/webhooks/ingest/{source_id}")
    async def receive_webhook(source_id: UUID, request: Request):
        """
        No JWT auth — uses HMAC-SHA256 verification instead.
        
        1. Read raw request body
        2. Load ingestion_source by source_id
        3. Verify X-Webhook-Signature header:
           expected = hmac.new(source.webhook_secret, body, sha256).hexdigest()
           if header != expected: return 403
        4. Parse body as JSON
        5. Pass to ingestion_handler.process_webhook_event()
        6. Return 200 with {event_id, status}
        """
    ```

    Mount this router WITHOUT the auth dependency (it has its own HMAC auth).

66. **Implement ingestion source CRUD endpoints**:
    ```
    POST   /api/v1/scenarios/{id}/ingestion-sources            # Create source
    GET    /api/v1/scenarios/{id}/ingestion-sources             # List sources
    PUT    /api/v1/scenarios/{id}/ingestion-sources/{sid}       # Update config
    DELETE /api/v1/scenarios/{id}/ingestion-sources/{sid}       # Remove
    POST   /api/v1/scenarios/{id}/ingestion-sources/{sid}/test  # Test with mock data
    GET    /api/v1/simulations/{id}/ingested-events             # List ingested events for a run
    ```

    The "test" endpoint sends a fake payload through the full pipeline (including Gemini summarization if enabled) and returns what intervention would be created, without actually creating it.

67. **Update orchestrator tick loop** — Add Step 0:
    ```python
    # In orchestrator.py, at the start of each tick loop iteration:
    
    # Step 0: Check external ingestion sources
    if self.ingestion_worker:
        external_events = await self.ingestion_worker.check_sources(simulation_run.id, tick)
        for event in external_events:
            self.event_log.log_event(simulation_run.id, tick, 'external_ingestion', None, event.to_dict())
    
    # Step 1: Apply pending interventions (now includes auto-created from ingestion)
    # ... rest unchanged
    ```

68. **Build ingestion source config UI in Scenario Intake screen**:
    - Add collapsible "External Data Sources" section below the config panel
    - "Add Source" button opens modal:
      - Name input
      - Type selector: "Webhook" or "Scheduled Pull"
      - **Webhook mode:**
        - Auto-generated webhook URL displayed (copy button)
        - Auto-generated webhook secret displayed (copy button, shown once)
        - Mapping rules: event_field (JSONPath), severity_field (optional), Gemini summarize toggle
        - Rate limit per minute (number input, default 5)
      - **Scheduled Pull mode:**
        - URL input
        - HTTP method selector (GET/POST)
        - Headers (key-value pairs, add/remove)
        - Query params (key-value pairs, variable substitution with `{{scenario_keywords}}`)
        - Poll interval in ticks (number input, default 3)
        - Response path (JSONPath to events array)
        - Same mapping rules as webhook
      - "Test Connection" button → calls test endpoint → shows sample output
      - "Save" button
    - Sources list: cards showing name, type, status (active/paused), event count, toggle switch for is_active
    - Edit and delete buttons per source

69. **Build "External Events Feed" panel in Live Dashboard**:
    - New toggleable panel (button in dashboard header: "External Feed")
    - Shows incoming events as a scrolling list:
      - Timestamp
      - Source name badge
      - Event summary (from Gemini or raw)
      - Status badge: "Converted to intervention" (green) or "Rejected: {reason}" (red)
      - Link icon: click to see the intervention in Intervention Console
    - Empty state: "No external data sources configured" with link to Scenario Intake

70. **Add WebSocket message type**:
    Update WebSocket handler to broadcast when external events are ingested:
    ```json
    {
      "type": "external_event_ingested",
      "tick": 5,
      "data": {
        "event_id": "uuid",
        "source_name": "Reuters News Feed",
        "event_summary": "Major trade agreement announced...",
        "severity": "high",
        "intervention_created": true,
        "intervention_id": "uuid"
      }
    }
    ```

### Verification Checklist

**Test webhook mode:**
- [ ] Create an ingestion source (webhook type) for a scenario
- [ ] Copy the webhook URL and secret
- [ ] Send a curl request with valid HMAC signature → event received, intervention created
- [ ] Send curl with invalid signature → 403 Forbidden
- [ ] Send 10 rapid requests → rate limiting kicks in, excess events rejected
- [ ] Start simulation → webhook events become interventions at next tick
- [ ] Live Dashboard "External Events Feed" shows the events in real time
- [ ] WebSocket receives `external_event_ingested` messages

**Test scheduled pull mode:**
- [ ] Create a scheduled pull source pointing to a public JSON API (e.g., a mock endpoint or JSONPlaceholder)
- [ ] Set poll_interval_ticks=2
- [ ] Run simulation → verify source is queried at tick 2, 4, 6, etc.
- [ ] Fetched data is summarized by Gemini and converted to interventions
- [ ] Dashboard shows pulled events

**Test Gemini summarization:**
- [ ] Enable gemini_summarize on a source
- [ ] Send raw JSON payload (e.g., a news headline)
- [ ] Verify Gemini converts it into a simulation-meaningful event with affected entities
- [ ] Gemini cost is tracked under the simulation's budget

**Test the test endpoint:**
- [ ] Call `/test` endpoint with mock payload → returns what intervention would be created, no side effects

**STOP after verification. Do not proceed to Phase 13.**
