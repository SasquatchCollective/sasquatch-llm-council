# Changelog

All notable changes to LLM Council++ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2026-05-10

### Added
- **`POST /api/ask` one-shot endpoint**: Single call, no conversation state, returns JSON directly. Accepts `models`, `chairman_model`, `web_search`, and `execution_mode`. Ideal for scripts and MCP agents.
- **`POST /api/conversations/{id}/message` sync endpoint**: Non-streaming JSON alternative to SSE. Saves to conversation history without requiring event stream parsing.
- **Per-request model overrides**: `council_models` and `chairman_model` fields on both streaming and sync message endpoints. Never mutates global config for ad-hoc queries.
- **`PipelineResult` dataclass**: Shared orchestration helper (`_run_council_pipeline`) eliminates duplicated stage1/2/3 collection logic across sync endpoints.
- **Multi-turn conversation memory**: Conversation endpoints pass full prior chat history to models. Follow-up questions carry context automatically.
- **MCP `chat` tool**: Multi-turn equivalent of `quick_chat` — pass `conversation_id` to continue a conversation with memory. (14 tools total)
- **UI: single-model council support**: Council members can now be reduced to 1 in the Settings UI (was minimum 2).
- **UI: chairman auto-disables**: Chairman section dims and becomes non-interactive when execution mode is not "Full Deliberation".

### Changed
- **Minimum council models reduced to 1**: Single-model queries are now valid for any execution mode (was 2 minimum).
- **`execution_mode` uses `Literal` type**: Pydantic rejects invalid values at parse time instead of runtime checks in each handler.
- **Settings cache**: `get_settings()` now uses mtime-based caching — repeated calls within the same request return the cached instance instead of re-reading disk (eliminates 5-10 redundant file reads per deliberation).
- **Storage I/O reduced**: `add_user_message()` and `add_assistant_message()` accept pre-loaded `conversation` kwarg, avoiding redundant reads after 404 checks.
- **Web search setup deduplicated**: Shared `_apply_search_env()` and `_fetch_search_context()` helpers replace 3 copy-pasted blocks (also fixes missing Serper env var in sync/oneshot paths).
- **Dead import removed**: `from .search import perform_web_search, SearchProvider` removed from `council.py` (unused there).
- **MCP `quick_chat` uses `/api/ask`**: No more save/restore of global settings — calls one-shot endpoint directly.
- **MCP `run_deliberation` uses per-request overrides**: Passes `council_models` in stream body instead of mutating settings with try/finally restore.
- **MCP client `ask()` method added**: `CouncilClient.ask()` wraps `POST /api/ask` for one-shot queries.
- **MCP client `stream_message` accepts overrides**: `council_models` and `chairman_model` params added to avoid settings mutation.
- **`llm-council-api` skill updated to v0.4.1**: Documents `/api/ask`, per-request overrides, sync endpoint, multi-turn conversations, SSE event table, and "Choosing the Right Endpoint" decision matrix.
- **`DEFAULT_EXECUTION_MODE` constant**: Extracted shared default (`'full'`) to `api.js` — eliminates magic string duplication across `App.jsx`, `Settings.jsx`, `CouncilConfig.jsx`.
- **`.subsection--disabled` CSS class**: Replaces inline opacity/pointer-events with reusable class (consistent with `.source-disabled`).
- **Chairman `SearchableModelSelect` respects disabled state**: `isDisabled` prop wired so keyboard users cannot change chairman when irrelevant.

## [0.4.0] - 2026-05-10

### Added
- **Settings export/import/reset endpoints**: `GET /api/settings/export` returns a full settings backup including actual API key values; `POST /api/settings/import` restores from a backup blob; `POST /api/settings/reset` wipes all settings to factory defaults
- **4 new MCP tools** (17 total): `set_api_key` — set any provider API key by name; `export_config` — backup full config as JSON; `import_config` — restore config from JSON string; `reset_config` — factory reset
- **Extended `configure_council` MCP tool**: now accepts `stage1_prompt`, `stage2_prompt`, `stage3_prompt`, `enabled_providers`, and `direct_provider_toggles` in addition to existing parameters
- **Sidebar delete button always visible**: trash icon now shows at 40% opacity on all conversations (was hover-only), brightens to full on hover
- **18 new tests**: backend export/import/reset endpoint tests, MCP tool tests for all new tools, and client method tests (108 total, up from 90)

### Changed
- **`llm-council-api` skill updated to v0.4.0**: documents system prompt fields, `enabled_providers`/`direct_provider_toggles` dict formats, all API key field names, and backup/restore endpoints
- **`import_settings` endpoint simplified**: uses Pydantic body parsing (`Settings` model) instead of manual JSON parsing — FastAPI now returns field-level 422 validation errors instead of generic 400s
- **`export_settings` endpoint**: uses `model_dump_json()` (single-pass) instead of `model_dump()` + `json.dumps()` (two-pass)

## [0.3.0] - 2026-05-10

### Added
- **MCP server** (`llm_council_mcp/`): Expose LLM Council++ as a Model Context Protocol server, letting Claude Code, Gemini CLI, and other MCP clients send questions to the council and retrieve deliberation results programmatically
- **13 MCP tools**: `list_models`, `get_council_config`, `configure_council`, `set_search_provider`, `run_stage1`, `run_stage2`, `run_stage3`, `run_deliberation`, `quick_chat`, `list_conversations`, `get_conversation`, `check_health`, `test_provider`
- **stdio transport** (default): MCP server runs as a local process; AI tools communicate via stdin/stdout with outbound HTTP to the Council backend (local or remote)
- **SSE transport**: MCP server runs as an HTTP server on port 8002; AI tools connect via URL with no local installation required
- **TinyFish search provider**: 5th web search option using TinyFish's free-tier Fetch API (5 req/min); requires free API key from agent.tinyfish.ai
- **90 tests**: backend TinyFish provider tests, MCP integration tests covering all 13 tools and both transport modes
- **`docs/mcp/`**: Comprehensive MCP documentation including transport selection guide, step-by-step setup for stdio and SSE, full tools reference, and real-world usage examples
- **`llm-council-api` Claude Code skill** (`skills/llm-council-api/SKILL.md`, v0.3.0): Installable skill for interacting with the Council via REST API without MCP — covers all endpoints, SSE parsing, error handling, and troubleshooting

## [0.2.3] - 2026-05-04

### Added
- **Docker support** (PR #5): Single-container deployment via `docker compose up -d --build` serving both frontend and API on port 8001. Thanks @kcelsi!
- **Docker healthcheck**: Backend liveness polling via `/api/health` every 30s with automatic restart on failure
- **Non-root container user**: Container now runs as `appuser` for reduced attack surface
- **`docs/` directory**: New structured documentation folder
- **`docs/DOCKER.md`**: Comprehensive Docker deployment guide covering environment variables, persistent storage, Ollama integration, reverse proxy setup (nginx/Caddy with SSE notes), upgrades, and troubleshooting

### Changed
- **CORS hardening**: Dev-ports regex (`5173|5174|3000`) is now suppressed when the built frontend is present (Docker/production mode) — same-origin deployments no longer expose API to external dev-port origins
- **Root cleanup**: Removed stub `main.py`; moved `QUICKSTART.md` and `TEST_PLAN_SEARCH.md` into `docs/`
- **README**: Docker section condensed to quick-start + link to `docs/DOCKER.md`; stale CORS description updated

## [0.2.2] - 2026-02-18

### Fixed
- **Ollama Configuration**: Fixed an issue where the "Local (Ollama)" toggle was disabled even when Ollama was connected (PR #4). Thanks @patrickgamer!

## [0.2.1] - 2026-01-31

### Added
- **Serper.dev Integration**: Google Search via Serper API with 2,500 free queries
- **DuckDuckGo Search Optimization**: Intelligent query processing with intent detection, hybrid web+news search, and relevance reranking
- **Search Settings**: Configurable result count (5-15) and hybrid mode toggle for DuckDuckGo
- **Query Intent Detection**: Automatically detects current events, factual, comparison, and research queries
- **Auto-save Council Config**: Council members and chairman selections now auto-save (no more forgetting to click Save)
- **Council Validation**: Prevent saving incomplete configurations (empty member slots or missing chairman)

### Changed
- **Improved Font Readability**: Switched markdown headers and model names from stylized 'Syne' to readable 'Plus Jakarta Sans'
- **Search Query Processing**: DuckDuckGo now automatically removes conversational fluff and adds temporal context
- **Search Provider Auto-switch**: Testing a search API key now auto-saves and switches to that provider

### Fixed
- YAKE keyword extraction setting now only shows for Tavily/Brave (DuckDuckGo has built-in optimization)
- Font inconsistency between Stage 3 (Chairman) and Stage 1/2 responses
- CORS support for additional frontend port (5174)

## [0.2.0] - 2026-01-31

### Added
- **Mobile Responsiveness**: Full mobile support with hamburger menu, responsive layouts, and touch-friendly UI
- **Chat History Search**: Filter conversations by title in the sidebar
- **Source Validation**: Disable model source toggles when API key not configured with helpful tooltips
- **Version Display**: Show version number in sidebar and settings

### Changed
- **UI Redesign**: New "Council Chamber" dark theme with refined glassmorphism
- **Typography**: Updated font stack (Syne, Plus Jakarta Sans, Source Serif 4, JetBrains Mono)
- **Hero Animations**: Staggered fade-in animations for welcome screen elements

### Fixed
- Auto-cleanup of empty conversations when switching or creating new ones
- Duplicate API route in backend
- Duplicate CSS blocks causing style conflicts
- React key anti-pattern in message list
- Redundant decorator in provider base class

## [0.1.0] - Initial Release

### Added
- 3-stage deliberation system (Individual Responses → Peer Ranking → Chairman Synthesis)
- Multi-provider support: OpenRouter, Ollama, Groq, Direct providers, Custom endpoints
- Web search integration: DuckDuckGo, Tavily, Brave with Jina Reader
- Execution modes: Chat Only, Chat + Ranking, Full Deliberation
- Conversation persistence with JSON storage
- Settings management with import/export
- "I'm Feeling Lucky" random model selection
