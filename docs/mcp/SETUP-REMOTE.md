# SSE Setup (Zero Local Installation)

This guide covers running the MCP server inside the same container as your Council backend and connecting to it over HTTPS. No Python or pip required on the client machine.

If you want to run the MCP server locally and point it at a remote backend, see [SETUP-LOCAL.md](SETUP-LOCAL.md) instead. If you are unsure which to choose, see [CHOOSING-TRANSPORT.md](CHOOSING-TRANSPORT.md).

---

## Prerequisites

- LLM Council++ running in a container (see [docs/DOCKER.md](../DOCKER.md))
- Port 8002 accessible from your client machine (or via VPN/reverse proxy)

---

## Step 1: Enable the MCP port in docker-compose.yml

Open `docker-compose.yml` and uncomment the MCP port mapping:

```yaml
ports:
  - "8001:8001"   # Council backend (already active)
  - "8002:8002"   # MCP server (uncomment this line)
```

---

## Step 2: Start the MCP server inside the container

The MCP server must be started in SSE mode inside the running container. If your container startup script does not already launch it, run:

```bash
docker exec -d llm-council-plus python -m llm_council_mcp --transport sse --host 0.0.0.0 --port 8002
```

The `-d` flag runs it detached (in the background). Replace `llm-council-plus` with the actual container name if different (check with `docker ps`).

To make this permanent, add the command to your container entrypoint or `docker-compose.yml`:

```yaml
command: >
  sh -c "
    python -m backend.main &
    python -m llm_council_mcp --transport sse --host 0.0.0.0 --port 8002
  "
```

---

## Step 3: Register in Claude Code

```bash
claude mcp add llm-council --url https://yourserver.com:8002/mcp
```

Replace `yourserver.com` with your server's IP address or domain.

For Gemini CLI:
```bash
gemini mcp add llm-council --url https://yourserver.com:8002/mcp
```

---

## Step 4: Security

The MCP server has no built-in authentication. Before exposing port 8002 publicly, protect it with one of these approaches:

**Firewall rule (simplest):** Restrict port 8002 to your IP address only. On most cloud providers this is done in the security group or firewall panel.

**VPN:** Run the server on a VPN-only network and connect your client to the VPN before using the MCP tools.

**Reverse proxy with authentication:**
```nginx
# nginx example — protect /mcp with basic auth
location /mcp {
    auth_basic "Council MCP";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8002;
    proxy_set_header Connection '';
    proxy_buffering off;
}
```

> Do not expose port 8002 to the public internet without one of these protections. Anyone with the URL can invoke council tools and consume your LLM API quota.

---

## Step 5: Verify it works

Ask your AI:

> "Check the council health"

A successful response confirms the MCP server reached the backend:

```
Backend is reachable at http://localhost:8001
Providers configured: openrouter, anthropic
Council members: 3 models selected
```

---

## Troubleshooting

**"Connection refused" on port 8002**
- Confirm the MCP server process is running inside the container: `docker exec llm-council-plus ps aux | grep llm_council_mcp`
- Check the port mapping in `docker-compose.yml` and re-run `docker compose up -d`
- Verify firewall rules allow inbound traffic on 8002

**Tools return errors but health check passes**
- The MCP server is running but the Council backend may not have API keys configured
- Open the Council web UI at port 8001 and confirm provider keys are set in Settings

**SSE connection drops after a few seconds**
- If behind a reverse proxy, enable proxy buffering off and increase timeouts (see nginx example above)
- Some load balancers close idle SSE connections; configure keepalive or use a WebSocket-capable proxy
