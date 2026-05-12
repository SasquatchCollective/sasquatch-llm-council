# Choosing a Transport: stdio vs SSE

The MCP server supports two transport modes. Picking the right one depends on where your LLM Council++ backend is running and whether you want to install anything locally.

---

## What is stdio transport?

In stdio mode, your AI tool (Claude Code, Gemini CLI) launches the MCP server as a child process and communicates with it over standard input/output. The MCP server process lives on your local machine and makes outbound HTTP requests to reach the Council backend.

- The backend can be local (`localhost:8001`) or remote (`https://yourserver.com:8001`) — you control this with `--base-url`.
- No extra port needs to be open for the MCP layer itself; only the backend API port (8001) must be reachable.
- Requires Python to be installed locally.

## What is SSE transport?

In SSE (Server-Sent Events) mode, the MCP server runs as an HTTP server — typically inside the same container as the Council backend — and listens on port 8002. Your AI tool connects to it over HTTPS, with no local process involved.

- Zero local installation: no Python, no pip, just a URL.
- Requires port 8002 to be publicly reachable (firewall, reverse proxy, or VPN).
- The MCP server and Council backend both run on the remote host.

---

## Side-by-side comparison

| | stdio (local) | stdio (remote backend) | SSE (remote) |
|---|---|---|---|
| Local Python needed | Yes | Yes | No |
| Backend location | localhost:8001 | Remote server | Remote server |
| MCP server location | Your machine | Your machine | Remote server |
| Ports to open | None | Backend 8001 | Backend 8001 + MCP 8002 |
| Security | Process isolation | Outbound HTTPS only | Needs firewall/VPN for 8002 |
| Best for | Local development | Remote server, laptop client | Shared team server, zero install |

---

## Decision guide

**If you are running Council on your laptop:**
Use stdio with a local backend. Nothing is exposed to the network.
```
Claude Code --stdio--> MCP server --HTTP--> localhost:8001
```

**If Council runs on a remote server but you have Python locally:**
Use stdio with `--base-url`. The MCP server runs on your machine and makes outbound HTTPS calls to the server.
```
Claude Code --stdio--> MCP server --HTTPS--> yourserver.com:8001
```

**If Council runs on a remote server and you do not want to install anything locally:**
Use SSE. Run the MCP server on the same host as the backend, expose port 8002, and register the URL in your AI tool.
```
Claude Code --HTTPS--> Remote MCP server (8002) --HTTP--> backend (8001)
```

---

## Architecture diagrams

```
stdio local:               stdio remote:                 SSE remote:

Claude Code                Claude Code                   Claude Code
    |                          |                              |
    | stdin/stdout             | stdin/stdout                 | HTTPS :8002
    v                          v                              v
MCP server (local)         MCP server (local)         Remote MCP server
    |                          |                              |
    | HTTP                     | HTTPS                        | HTTP (internal)
    v                          v                              v
localhost:8001            yourserver.com:8001           backend (8001)
```

---

## Frequently asked questions

**Can I use SSE locally?**
Yes. You can run the MCP server in SSE mode on localhost and point Claude Code to `http://localhost:8002/mcp`. This is unusual — stdio is simpler locally — but it works if you want to test the SSE path.

**Does SSE have built-in authentication?**
No. The MCP server does not implement token-based auth on the SSE endpoint. If port 8002 is exposed to the internet, protect it with a firewall rule, a VPN, or a reverse proxy that enforces auth (nginx with `auth_basic`, Caddy with `basicauth`, Cloudflare Access, etc.).

**Which transport has better performance?**
For individual users the difference is imperceptible — both add only a few milliseconds of overhead on top of LLM inference time. stdio avoids one network hop for local setups. SSE adds a network round-trip but saves you from maintaining a local Python environment.

**Do both transports support streaming responses?**
Yes. Both transports stream deliberation output back to the AI tool as it arrives from the backend.
