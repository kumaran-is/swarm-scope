# Session 2: Gemini Integration Layer (Phase 3)

> **Pre-requisite**: Session 1 complete. Backend runs, all tables exist.
> **Goal**: Working Gemini client that can extract structured output from a real document, make function calls, and generate embeddings.
> **Estimated time**: 15-20 minutes + testing/tuning

---

## PROMPT — Copy everything below this line into Claude Code

---

Read the file `SWARM_SCOPE_BUILD_PROMPT.md` in this repository for the full architecture context.

Now execute **Phase 3 (Gemini Layer)** only. Here is exactly what to build:

### Phase 3: Gemini Layer (Steps 13-17)

13. **Implement Gemini client wrapper** in `backend/app/gemini/client.py`:
    - Use `google-genai` Python SDK
    - Create `GeminiClient` class wrapping the SDK
    - Implement `GeminiRateLimiter` class that tracks:
      - Tokens per minute (from `GEMINI_MAX_TOKENS_PER_MINUTE` env var)
      - Requests per minute (from `GEMINI_MAX_REQUESTS_PER_MINUTE` env var)
      - Per-run budget tracking (from `GEMINI_BUDGET_PER_RUN_USD` env var)
      - Queue requests when approaching limits
    - Log every call: `{model, tokens_in, tokens_out, latency_ms, purpose, simulation_run_id}`
    - Retry logic: 3 retries with exponential backoff (1s, 2s, 4s) + jitter
    - Three calling modes exposed as methods:
      - `extract_structured(prompt, response_schema)` → structured output mode
      - `call_with_functions(prompt, function_declarations)` → function calling mode
      - `generate_embedding(text)` → embedding mode

14. **Implement all prompt templates** in `backend/app/gemini/prompts.py`:
    - `WORLD_EXTRACTION_PROMPT` — System prompt instructing Gemini to extract entities, factions, goals, resources, constraints, tensions, and KPIs from a source document. Output must match `WorldExtraction` Pydantic schema.
    - `AGENT_GENERATION_PROMPT` — Given a world model, generate N agent profiles with name, role, faction, personality (Big Five), goals, resources, decision style. Output must match `AgentProfile` schema.
    - `AGENT_DECISION_PROMPT` — Given agent profile + working memory + top 5 episodic memories + current world state, choose an action via function calling. Include the agent's personality and goals in the system prompt.
    - `MEMORY_COMPRESSION_PROMPT` — Given 5 episodic memory entries, produce 1 semantic memory summary.
    - `REPORT_PLANNING_PROMPT` — Given simulation summary, produce report outline with sections.
    - `REPORT_SECTION_PROMPT` — Given outline + section context + tool results, write one report section.
    - `AGENT_CHAT_PROMPT` — Given agent profile + memories + world state + user message, respond in character.
    - `INGESTION_SUMMARIZE_PROMPT` — Given raw external event + world model summary, describe how event affects the scenario.

15. **Implement extraction module** in `backend/app/gemini/extraction.py`:
    - `extract_world_model(source_text: str) -> WorldExtraction` — calls `extract_structured()` with `WORLD_EXTRACTION_PROMPT` and `WorldExtraction` as response schema
    - `generate_agents(world_model: WorldModel, count: int) -> list[AgentProfile]` — calls `extract_structured()` with `AGENT_GENERATION_PROMPT`
    - Both handle JSON parsing errors gracefully (retry once, then return partial result with warning)

16. **Implement decision module** in `backend/app/gemini/decisions.py`:
    - Define all 10 `AGENT_ACTIONS` as `FunctionDeclaration` objects:
      - `form_alliance`, `break_alliance`, `publish_statement`, `reallocate_resource`
      - `escalate_conflict`, `de_escalate_conflict`, `gather_information`
      - `influence_agent`, `change_strategy`, `do_nothing`
    - `get_agent_decision(agent, working_memory, episodic_memories, world_state) -> AgentAction`
    - Calls `call_with_functions()` with all function declarations as tools
    - Parses the function call response into a typed `AgentAction` dataclass

17. **Implement embedding module** in `backend/app/gemini/embeddings.py`:
    - `generate_embedding(text: str) -> list[float]` — uses `text-embedding-004` model
    - `find_relevant_memories(query: str, memories: list[EpisodicMemory], top_k: int = 5) -> list[EpisodicMemory]` — embeds query, computes cosine similarity against pre-embedded memories, returns top K
    - Cache embeddings to avoid re-computing for unchanged memories

### Verification Checklist

After completing Phase 3, test with a **real Gemini API key**:

- [ ] Set `GEMINI_API_KEY` in `.env` and verify client connects
- [ ] Test extraction: pass a sample document (3-4 paragraphs about any policy scenario) → verify it returns valid `WorldExtraction` with entities, factions, tensions, KPIs
- [ ] Test function calling: pass a mock agent context → verify it returns a valid `AgentAction` (one of the 10 defined actions)
- [ ] Test embeddings: embed two similar sentences → verify cosine similarity > 0.7
- [ ] Test rate limiter: verify it logs calls correctly and tracks token usage
- [ ] Test retry logic: temporarily use a bad API key → verify 3 retries then graceful error

**Tuning note**: The extraction prompt will likely need 2-3 iterations. If the world extraction output is shallow (e.g., only 1-2 entities from a complex document), refine `WORLD_EXTRACTION_PROMPT` to include more explicit instructions and an example output structure. This iteration is expected — do not skip it.

**STOP after verification. Do not proceed to Phase 4.**
