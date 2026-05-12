# MCP Usage Examples

These walkthroughs show real interactions between a user, their AI assistant, and the LLM Council++ MCP server. All examples assume the MCP server is registered and the backend is running.

---

## Example 1: Ask the council a question

**What you say to your AI:**

> "Ask the council: what are the pros and cons of microservices architecture? Use web search."

**What happens behind the scenes:**

The AI recognizes this as a full deliberation request and calls `run_deliberation`:

```json
{
  "tool": "run_deliberation",
  "input": {
    "query": "What are the pros and cons of microservices architecture?",
    "web_search": true
  }
}
```

The MCP server streams the request through all three stages against the Council backend. After a minute or two (depending on council size and model speeds), the tool returns:

```json
{
  "conversation_id": "f8a2b3c1-...",
  "title": "Microservices: Pros and Cons",
  "stage1_responses": [
    {
      "model": "openai:gpt-4.1",
      "label": "Response A",
      "content": "Microservices offer independent deployability, team autonomy, and horizontal scalability per service. However they introduce significant operational complexity..."
    },
    {
      "model": "anthropic:claude-sonnet-4",
      "label": "Response B",
      "content": "The core tradeoff in microservices is flexibility vs complexity. On the benefits side..."
    },
    {
      "model": "groq:llama3-70b-8192",
      "label": "Response C",
      "content": "Pros: independent scaling, technology diversity, fault isolation..."
    }
  ],
  "aggregate_rankings": {
    "Response B": 1.3,
    "Response A": 2.0,
    "Response C": 2.7
  },
  "chairman_answer": "Microservices architecture offers compelling advantages for teams at scale — independent deployment, technology freedom, and fault isolation — but these benefits come at the cost of substantial operational overhead. The council's top-ranked response (Response B) correctly identifies that the decision hinges on team size and organizational maturity. Smaller teams are almost always better served by a well-structured monolith. The search results confirm this: Netflix and Uber moved to microservices only after reaching hundreds of engineers and millions of users..."
}
```

**What your AI presents to you:**

The AI surfaces the `chairman_answer` as the primary response and may offer to show you individual model responses or rankings if you ask.

---

## Example 2: Configure a council for coding questions

**What you say to your AI:**

> "Set up a coding-focused council with GPT-4.1, Claude Sonnet, and Gemini Pro. Make sure full deliberation is on."

**What happens behind the scenes:**

The AI first checks what models are available:

```json
{"tool": "list_models", "input": {}}
```

Response (abbreviated):
```json
{
  "models": [
    {"id": "openai:gpt-4.1", "provider": "openai", "name": "GPT-4.1"},
    {"id": "openrouter:anthropic/claude-sonnet-4", "provider": "openrouter", "name": "Claude Sonnet 4"},
    {"id": "openrouter:google/gemini-pro-1.5", "provider": "openrouter", "name": "Gemini Pro 1.5"},
    ...
  ]
}
```

The AI then maps your request to available model IDs and calls `configure_council`:

```json
{
  "tool": "configure_council",
  "input": {
    "models": [
      "openai:gpt-4.1",
      "openrouter:anthropic/claude-sonnet-4",
      "openrouter:google/gemini-pro-1.5"
    ],
    "execution_mode": "full"
  }
}
```

Response:
```json
{
  "success": true,
  "config": {
    "council_members": [
      "openai:gpt-4.1",
      "openrouter:anthropic/claude-sonnet-4",
      "openrouter:google/gemini-pro-1.5"
    ],
    "chairman": "anthropic:claude-opus-4",
    "execution_mode": "full"
  }
}
```

**What your AI presents to you:**

> "Your council is set. GPT-4.1, Claude Sonnet 4, and Gemini Pro 1.5 are now council members with full deliberation enabled. Your current chairman is Claude Opus 4. Ready to ask a coding question?"

Note: The AI picks the closest available model IDs. If a model you named is not configured (e.g., you have no Google API key), the AI will flag this and suggest alternatives from what is available.

---

## Example 3: Quick check with a single model

**What you say to your AI:**

> "Ask GPT-4.1 directly: what's the difference between REST and GraphQL?"

**What happens behind the scenes:**

The AI recognizes you want a direct single-model response, not a full deliberation, and calls `quick_chat`:

```json
{
  "tool": "quick_chat",
  "input": {
    "query": "What's the difference between REST and GraphQL?",
    "model": "openai:gpt-4.1",
    "web_search": false
  }
}
```

This uses the one-shot `/api/ask` endpoint internally — no conversation is created, no settings are mutated.

Response:
```json
{
  "model": "openai:gpt-4.1",
  "response": "REST and GraphQL are both approaches to building APIs, but they differ fundamentally in how clients request data.\n\n**REST** organizes endpoints around resources (e.g., `/users/123`, `/posts`). Each endpoint returns a fixed shape of data. If you need user data plus their posts, you typically make two requests.\n\n**GraphQL** provides a single endpoint where clients specify exactly what fields they need in a query. You can fetch a user and their posts in one request, getting precisely the fields you want — nothing more.\n\n**When to use REST:** Simpler CRUD APIs, public APIs where caching is important, teams unfamiliar with GraphQL.\n\n**When to use GraphQL:** Complex, nested data requirements; mobile clients sensitive to over-fetching; rapidly evolving frontends that need flexibility.",
  "error": null,
  "web_search_used": false
}
```

**What your AI presents to you:**

The AI presents the response directly, typically as a formatted answer. Because this is `quick_chat` (single model, no deliberation), there are no rankings or chairman synthesis — you get the raw model output immediately.

---

## Example 4: Multi-turn conversation with follow-ups

**What you say to your AI:**

> "Chat with Claude about how async/await works in Python"

**What happens behind the scenes (first call):**

The AI uses the `chat` tool to start a new conversation:

```json
{
  "tool": "chat",
  "input": {
    "query": "How does async/await work in Python?",
    "model": "anthropic:claude-sonnet-4"
  }
}
```

Response:
```json
{
  "conversation_id": "conv-abc-123",
  "model": "anthropic:claude-sonnet-4",
  "response": "Python's async/await is built on coroutines and an event loop...",
  "error": null,
  "web_search_used": false
}
```

**You then ask a follow-up:**

> "Can you show me a concrete example with aiohttp?"

**What happens (second call):**

The AI passes the same `conversation_id` to continue the conversation:

```json
{
  "tool": "chat",
  "input": {
    "query": "Can you show me a concrete example with aiohttp?",
    "model": "anthropic:claude-sonnet-4",
    "conversation_id": "conv-abc-123"
  }
}
```

The model receives the full prior conversation as context and responds with a relevant example building on its previous explanation.

**Key behavior:**
- The `conversation_id` links follow-up messages to the same conversation
- The model sees all prior user/assistant turns automatically
- No need to repeat context or re-explain — the model remembers
- For one-off questions without memory, use `quick_chat` instead
