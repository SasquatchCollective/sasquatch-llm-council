# MCP Tools Reference

The LLM Council++ MCP server exposes 14 tools grouped into four categories. Your AI assistant calls these automatically based on what you ask it to do — you rarely need to specify a tool name directly.

---

## Council Management

### `list_models`

Lists all models available from all configured providers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| _(none)_ | | | |

**Example prompt:** "What models are available in my council?"

**Example response:**
```json
{
  "models": [
    {"id": "openrouter:anthropic/claude-sonnet-4", "provider": "openrouter", "name": "Claude Sonnet 4"},
    {"id": "ollama:llama3.1:latest", "provider": "ollama", "name": "llama3.1:latest"},
    {"id": "groq:llama3-70b-8192", "provider": "groq", "name": "Llama 3 70B"}
  ],
  "total": 3
}
```

---

### `get_council_config`

Returns the current council configuration: selected models, chairman, temperatures, and execution mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| _(none)_ | | | |

**Example prompt:** "What's my current council setup?"

**Example response:**
```json
{
  "council_members": ["openrouter:anthropic/claude-sonnet-4", "openai:gpt-4.1"],
  "chairman": "anthropic:claude-opus-4",
  "stage1_temperature": 0.5,
  "stage2_temperature": 0.3,
  "stage3_temperature": 0.4,
  "execution_mode": "full"
}
```

---

### `configure_council`

Updates council members, chairman, temperatures, or execution mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `models` | array of strings | No | 1–8 model IDs for the council |
| `chairman` | string | No | Model ID for the chairman |
| `stage1_temperature` | float (0.0–2.0) | No | Stage 1 creativity level |
| `stage2_temperature` | float (0.0–2.0) | No | Stage 2 ranking consistency |
| `stage3_temperature` | float (0.0–2.0) | No | Stage 3 synthesis creativity |
| `execution_mode` | string | No | `chat_only`, `chat_ranking`, or `full` |

**Example prompt:** "Set up a coding council with GPT-4.1 and Claude Sonnet, using full deliberation mode."

**Example response:**
```json
{
  "success": true,
  "config": {
    "council_members": ["openai:gpt-4.1", "openrouter:anthropic/claude-sonnet-4"],
    "execution_mode": "full"
  }
}
```

---

### `set_search_provider`

Sets the active web search provider.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | `duckduckgo`, `tavily`, `brave`, `serper`, or `tinyfish` |

**Example prompt:** "Switch my search provider to Tavily."

**Example response:**
```json
{"success": true, "provider": "tavily"}
```

---

## Deliberation

### `run_stage1`

Runs Stage 1: sends the query to all council members in parallel and collects individual responses.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | The question or prompt |
| `web_search` | boolean | No | Enable web search context (default: false) |
| `conversation_id` | string | No | Attach to an existing conversation |

**Example prompt:** "Ask the council: what are the main tradeoffs of event-driven architecture?"

**Example response:**
```json
{
  "conversation_id": "abc-123",
  "responses": [
    {"model": "openai:gpt-4.1", "label": "Response A", "content": "Event-driven architecture..."},
    {"model": "anthropic:claude-sonnet-4", "label": "Response B", "content": "The primary tradeoffs..."}
  ],
  "stage": "stage1_complete"
}
```

---

### `run_stage2`

Runs Stage 2: each council member anonymously ranks and reviews all Stage 1 responses.

Must be called after `run_stage1` with the same `conversation_id`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Same query used in Stage 1 |
| `conversation_id` | string | Yes | Conversation ID from Stage 1 |

**Example prompt:** (Called automatically as part of a full deliberation flow)

**Example response:**
```json
{
  "conversation_id": "abc-123",
  "rankings": [
    {"model": "openai:gpt-4.1", "ranking": ["Response B", "Response A"]},
    {"model": "anthropic:claude-sonnet-4", "ranking": ["Response A", "Response B"]}
  ],
  "aggregate_scores": {"Response A": 1.5, "Response B": 1.5},
  "stage": "stage2_complete"
}
```

---

### `run_stage3`

Runs Stage 3: the chairman synthesizes a final answer using all Stage 1 responses, Stage 2 rankings, and any search context.

Must be called after `run_stage2` with the same `conversation_id`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Same query used in Stages 1 and 2 |
| `conversation_id` | string | Yes | Conversation ID from earlier stages |

**Example prompt:** (Called automatically as part of a full deliberation flow)

**Example response:**
```json
{
  "conversation_id": "abc-123",
  "chairman_answer": "Event-driven architecture offers excellent scalability and decoupling...",
  "stage": "stage3_complete"
}
```

---

### `run_deliberation`

Runs the full 3-stage deliberation in a single call. This is the most common tool for end-to-end use. Per-request model overrides never modify global settings.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | The question or prompt |
| `web_search` | boolean | No | Enable web search context (default: false) |
| `models` | array of strings | No | Override council members for this run only (1+ models) |

**Example prompt:** "Ask the council: what are the pros and cons of microservices?"

**Example response:**
```json
{
  "conversation_id": "abc-123",
  "stage1_responses": [...],
  "stage2_rankings": [...],
  "chairman_answer": "Microservices offer independent deployability and team autonomy...",
  "title": "Microservices: Pros and Cons"
}
```

---

### `quick_chat`

Sends a query to a single model with no deliberation. Uses the one-shot `/api/ask` endpoint — no conversation state, no settings mutation. **Stateless**: each call is independent with no memory. For multi-turn, use `chat` instead.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | The question or prompt |
| `model` | string | Yes | Model ID (e.g., `openai:gpt-4.1`) |
| `web_search` | boolean | No | Enable web search context (default: false) |

**Example prompt:** "Ask GPT-4.1 directly: what is the difference between REST and GraphQL?"

**Example response:**
```json
{
  "model": "openai:gpt-4.1",
  "response": "REST and GraphQL are both API paradigms, but they differ in...",
  "error": null,
  "web_search_used": false
}
```

### `chat`

Chat with a model in a multi-turn conversation. The model sees the full conversation history from prior turns, so follow-up questions work naturally. First call: omit `conversation_id` to start a new conversation. Subsequent calls: pass the `conversation_id` from the previous response to continue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | The question or follow-up |
| `model` | string | Yes | Model ID (e.g., `openai:gpt-4.1`) |
| `conversation_id` | string | No | Pass from previous response to continue conversation |
| `web_search` | boolean | No | Enable web search context (default: false) |

**Example prompt:** "Chat with Claude about quantum computing, then ask a follow-up"

**First call response:**
```json
{
  "conversation_id": "abc-123",
  "model": "anthropic:claude-sonnet-4",
  "response": "Quantum computing uses qubits that can exist in superposition...",
  "error": null,
  "web_search_used": false
}
```

**Follow-up call** (pass `conversation_id: "abc-123"`):
```json
{
  "conversation_id": "abc-123",
  "model": "anthropic:claude-sonnet-4",
  "response": "Building on what I explained earlier about superposition, entanglement allows...",
  "error": null,
  "web_search_used": false
}
```

---

## Conversation Management

### `list_conversations`

Returns a list of saved conversations with titles and timestamps.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| _(none)_ | | | |

**Example prompt:** "Show me my recent council conversations."

**Example response:**
```json
{
  "conversations": [
    {"id": "abc-123", "title": "Microservices: Pros and Cons", "created_at": "2026-05-10T14:22:00Z"},
    {"id": "def-456", "title": "Event-Driven Architecture Tradeoffs", "created_at": "2026-05-09T10:11:00Z"}
  ],
  "total": 2
}
```

---

### `get_conversation`

Retrieves the full content of a specific conversation, including all stages.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | Yes | The conversation ID to retrieve |

**Example prompt:** "Get the conversation abc-123 and summarize the chairman's answer."

**Example response:**
```json
{
  "id": "abc-123",
  "title": "Microservices: Pros and Cons",
  "stage1": [...],
  "stage2": [...],
  "stage3": {"chairman_answer": "..."},
  "created_at": "2026-05-10T14:22:00Z"
}
```

---

## Health

### `check_health`

Checks whether the Council backend is reachable and returns provider configuration status.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| _(none)_ | | | |

**Example prompt:** "Check the council health."

**Example response:**
```json
{
  "status": "ok",
  "backend_url": "http://localhost:8001",
  "providers": {
    "openrouter": "configured",
    "anthropic": "configured",
    "ollama": "not_configured"
  },
  "council_members": 3,
  "chairman": "anthropic:claude-opus-4"
}
```

---

### `test_provider`

Tests connectivity to a specific LLM provider. Optionally accepts an API key to test before saving it in Settings.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | Provider name: `openrouter`, `openai`, `anthropic`, `google`, `groq`, `mistral`, `deepseek`, `ollama`, `custom` |
| `api_key` | string | No | API key to test (uses saved key if omitted) |

**Example prompt:** "Test my Anthropic connection."

**Example response:**
```json
{
  "provider": "anthropic",
  "status": "ok",
  "models_available": 4,
  "latency_ms": 312
}
```

---

## Error Format

When a tool call fails, the response includes a structured error object:

```json
{
  "error": {
    "type": "rate_limit",
    "message": "429 Too Many Requests from OpenRouter",
    "retryable": true
  }
}
```

Error types: `rate_limit`, `auth_error`, `timeout`, `model_not_found`, `network_error`, `provider_error`.
