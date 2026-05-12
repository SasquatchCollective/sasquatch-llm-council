# LLM Council++

![LLM Council++](header.png)

A 3-stage deliberation system where multiple LLMs collaboratively answer questions through independent response, anonymous peer review, and chairman synthesis.

---

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                        YOUR QUESTION                         │
│            (+ optional web search for real-time info)        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    STAGE 1: DELIBERATION                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Claude  │  │  GPT-4  │  │ Gemini  │  │  Llama  │  ...   │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       ▼            ▼            ▼            ▼              │
│  Response A   Response B   Response C   Response D          │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    STAGE 2: PEER REVIEW                      │
│  Each model reviews ALL responses (anonymized as A, B, C, D) │
│  and ranks them by accuracy, insight, and completeness       │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    STAGE 3: SYNTHESIS                         │
│  Chairman model reviews all responses + rankings + context   │
│  and produces a final synthesized answer                     │
└──────────────────────────────────────────────────────────────┘
```

Three execution modes control deliberation depth:

| Mode | Stages | Use Case |
|------|--------|----------|
| **Chat Only** | Stage 1 | Quick responses, comparing model outputs |
| **Chat + Ranking** | Stages 1 & 2 | Peer review without synthesis |
| **Full Deliberation** | All 3 stages | Complete council process (default) |

---

## Installation

**Prerequisites:** Python 3.10+, Node.js 18+, [uv](https://docs.astral.sh/uv/)

```bash
git clone <your-repo-url>
cd llm-council-plus
uv sync                    # Backend dependencies
cd frontend && npm install # Frontend dependencies
```

### Running

```bash
# Recommended
./start.sh

# Or manually:
uv run python -m backend.main   # Terminal 1 — backend on :8001
cd frontend && npm run dev       # Terminal 2 — frontend on :5173
```

Open **http://localhost:5173** and configure API keys in Settings.

### Docker

```bash
docker compose up -d --build
```

Open **http://localhost:8001**. Data persists to `./data` on the host. See [docs/DOCKER.md](docs/DOCKER.md) for Ollama, reverse proxy, and environment variable details.

### Network Access

The backend listens on `0.0.0.0:8001` by default. For frontend network access:

```bash
cd frontend && npm run dev -- --host
```

`./start.sh` does this automatically.

---

## Providers

Mix and match models from different sources:

| Provider | Type | Description |
|----------|------|-------------|
| **OpenRouter** | Cloud | 100+ models via single API |
| **Ollama** | Local | Run open-source models locally |
| **Groq** | Cloud | Ultra-fast inference |
| **OpenAI** | Cloud | Direct OpenAI API |
| **Anthropic** | Cloud | Direct Anthropic API |
| **Google** | Cloud | Direct Google AI API |
| **Mistral** | Cloud | Direct Mistral API |
| **DeepSeek** | Cloud | Direct DeepSeek API |
| **Custom Endpoint** | Any | Any OpenAI-compatible API (Together AI, Fireworks, vLLM, LM Studio, etc.) |

Models are routed by prefix: `openai:gpt-4.1`, `ollama:llama3.1:latest`, `anthropic:claude-sonnet-4`, `custom:model-name`, etc.

---

## Web Search

Ground responses in real-time information with pluggable search providers:

| Provider | Setup |
|----------|-------|
| **DuckDuckGo** | No API key needed |
| **TinyFish** | Free tier, no API key needed |
| **Serper** | API key from [serper.dev](https://serper.dev) |
| **Tavily** | API key from [tavily.com](https://tavily.com) |
| **Brave** | API key from [brave.com/search/api](https://brave.com/search/api/) |

Full article content is fetched via [Jina Reader](https://jina.ai/reader) for the top N results (configurable 0-10).

**Query modes:** Direct (default, sends exact query) or Smart Keywords (YAKE extraction, useful for long prompts).

---

## Configuration

On first launch, Settings opens automatically. At minimum:

1. **LLM API Keys** — enter keys for at least one provider
2. **Council Config** — select council members (1-8) and a chairman model
3. **Save Changes**

### API Key Links

| Provider | Link |
|----------|------|
| OpenRouter | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Groq | [console.groq.com/keys](https://console.groq.com/keys) |
| OpenAI | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| Anthropic | [console.anthropic.com](https://console.anthropic.com/) |
| Google AI | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Mistral | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys/) |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com/) |

API keys auto-save on successful test.

### Ollama (Local Models)

```bash
ollama pull llama3.1
ollama serve
```

Then enter `http://localhost:11434` in Settings and click Connect.

### Custom OpenAI-Compatible Endpoint

Enter a display name, base URL (e.g. `https://api.together.xyz/v1`), and optional API key. Works with Together AI, Fireworks, vLLM, LM Studio, GitHub Models, etc.

### Temperature Controls

- **Council Heat** (Stage 1): response creativity, default 0.5
- **Chairman Heat** (Stage 3): synthesis creativity, default 0.4
- **Stage 2 Heat**: ranking consistency, default 0.3

---

## MCP Server

LLM Council++ can run as an MCP server, letting tools like Claude Code and Gemini CLI query the council programmatically.

```bash
pip install -e .
claude mcp add llm-council python -m llm_council_mcp
```

See [docs/mcp/](docs/mcp/) for full setup guides.

---

## Claude Code Skill

For direct HTTP access without MCP, install the `llm-council-api` skill:

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/llm-council-api" ~/.claude/skills/llm-council-api
```

See [`skills/llm-council-api/SKILL.md`](skills/llm-council-api/SKILL.md) for the full reference.

---

## Data Storage

```
data/
├── settings.json          # Configuration (includes API keys)
└── conversations/         # Conversation history
    ├── {uuid}.json
    └── ...
```

All data stays local. The only external calls are to your configured LLM and search providers.

**Note:** API keys are stored in plain text in `data/settings.json`. The `data/` directory is in `.gitignore` by default — do not remove it.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Failed to load conversations" | Backend still starting; retries automatically |
| Models not in dropdown | Check provider is enabled, API key tested, Ollama connected |
| Jina Reader 451 errors | Site blocks AI scrapers; use Tavily/Brave or set `full_content_results` to 0 |
| OpenRouter rate limits | Free tier: 20 req/min, 50/day. Use Groq or Ollama instead |
| node_modules binary errors | `rm -rf frontend/node_modules && cd frontend && npm install` |

Logs: backend in terminal running `uv run python -m backend.main`, frontend in browser DevTools.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, Python 3.10+, httpx |
| Frontend | React 19, Vite, react-markdown |
| Styling | CSS with dark theme |
| Storage | JSON files in `data/` |
| Package Management | uv (Python), npm (JavaScript) |

---

## Credits

Fork of [llm-council](https://github.com/karpathy/llm-council) by [Andrej Karpathy](https://github.com/karpathy).

## License

MIT — see [LICENSE](LICENSE).
