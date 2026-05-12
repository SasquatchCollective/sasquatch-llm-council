# LLM Council++ — MCP Server

LLM Council++ exposes a Model Context Protocol (MCP) server that lets AI tools like Claude Code and Gemini CLI send questions directly to your council and retrieve deliberation results — all without opening a browser. Ask your AI assistant to run a full 3-stage deliberation, configure council members, or fetch past conversations, and it talks to the backend on your behalf.

## Quick Start

- Install: `pip install -e .` from the project root
- Register: `claude mcp add llm-council python -m llm_council_mcp`
- Use: ask Claude "check the council health" or "run a deliberation on [your question]"

## Choose Your Setup

| Scenario | Guide |
|----------|-------|
| Running Council locally on your machine | [SETUP-LOCAL.md](SETUP-LOCAL.md) |
| Council is on a remote server and you have Python locally | [SETUP-LOCAL.md](SETUP-LOCAL.md) (remote backend section) |
| Council is on a remote server and you want zero local install | [SETUP-REMOTE.md](SETUP-REMOTE.md) |
| Deciding between stdio and SSE transports | [CHOOSING-TRANSPORT.md](CHOOSING-TRANSPORT.md) |

## Tools Reference

See [TOOLS.md](TOOLS.md) for all 13 tools with parameters and examples.

## Examples

See [EXAMPLES.md](EXAMPLES.md) for real-world usage walkthroughs.

## MCP Not Working? Use the REST API Skill Instead

If the MCP server is unavailable, the SSE session is stale, or you prefer direct HTTP access, install the **`llm-council-api` Claude Code skill**. It gives Claude the same capabilities (configure council, run deliberations, list models, check health) via the REST API — no MCP required.

```bash
mkdir -p ~/.claude/skills/llm-council-api
curl -o ~/.claude/skills/llm-council-api/SKILL.md \
  https://raw.githubusercontent.com/your-org/llm-council-plus/main/skills/llm-council-api/SKILL.md
```

See [`skills/llm-council-api/SKILL.md`](../../skills/llm-council-api/SKILL.md) for the full reference including examples, error handling, and troubleshooting.
