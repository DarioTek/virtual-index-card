# Active plan: Raspberry Pi deployment and client usage documentation

## Objective
Add clear, step-by-step instructions for deploying `finance-tools` to a Raspberry Pi (both the FastMCP server and the FastAPI REST API, including `systemd` services and network security guidance) and explain how clients can connect to and use the tool (remote MCP over Streamable HTTP, stdio proxy / SSH, Python SDKs, FastMCP CLI, and direct REST API calls).

## Scope and Assumptions
- **In scope:**
  - Create `docs/raspberry-pi-deployment.md` with step-by-step Raspberry Pi deployment instructions and comprehensive client usage instructions.
  - Update `README.md` with a concise Raspberry Pi deployment & client usage pointer and link in Project records.
  - Update `docs/architecture.md` to link the deployment guide and note the Streamable HTTP transport option for remote MCP deployments.
  - Validate every documented command, client snippet, and HTTP/MCP endpoint behavior against the actual codebase locally.
- **Out of scope:**
  - Application code changes (existing FastAPI app and FastMCP server already support `uvicorn --host 0.0.0.0` and `fastmcp run --transport http --host 0.0.0.0`).
  - Live verification on physical Raspberry Pi hardware or live Yahoo Finance calls (blocked by sandbox egress policy).
- **Selected backlog items:** None (no matching active backlog item in `BACKLOG.md`).

## Tasks
1. **Completed** — Inspect repository structure, source code (`app.py`, `mcp_server.py`), existing docs, and verify `fastmcp run --transport http`, `fastmcp list`/`call`, stdio proxy, and `uvicorn` locally.
2. **Completed** — Write `docs/raspberry-pi-deployment.md` covering Raspberry Pi prerequisites, installation, interactive smoke tests, `systemd` services, firewall/security, updates, troubleshooting, and client usage across MCP (HTTP, stdio proxy, SSH, CLI, Python `fastmcp` & `mcp` SDKs) and REST API (`curl`, Python, Swagger UI).
3. **Completed** — Update `README.md` and `docs/architecture.md` to reference and link `docs/raspberry-pi-deployment.md`.
4. **Completed** — Validate documented Python client snippets and CLI commands offline against live local servers, run `uv run pytest`, and inspect `git diff` / `git diff --check`.

## Acceptance Criteria
- [x] `docs/raspberry-pi-deployment.md` provides complete, accurate, step-by-step Raspberry Pi setup and `systemd` deployment instructions for both the MCP server and FastAPI service.
- [x] `docs/raspberry-pi-deployment.md` explains the `get_ohlcv_indicators` tool contract and shows working examples for remote MCP clients (host JSON config, stdio proxy, SSH stdio, FastMCP CLI, Python `fastmcp.Client`, Python `mcp` SDK) and REST API clients (`curl`, Python, Swagger `/docs`).
- [x] Security caveats (no built-in auth/TLS; keep on LAN/VPN/reverse proxy) and Raspberry Pi caveats (64-bit OS, Python 3.11+, no `--reload` in production) are clearly documented.
- [x] `README.md` and `docs/architecture.md` link cleanly to the new guide with no broken relative links.
- [x] Documented client code snippets and commands are verified locally and `uv run pytest` passes.

## Files Changed
- Created: `docs/raspberry-pi-deployment.md`
- Modified: `README.md`, `docs/architecture.md`, `PLAN.md`

## Execution Log and Verification
- 2026-11-21: Installed `uv` 0.13.9 and synced `.venv` (`uv sync --group dev`).
- Verified `uv run pytest -q`: 16 passed, 1 pre-existing Starlette `httpx` deprecation warning.
- Verified `.venv/bin/fastmcp run src/finance_tools/mcp_server.py:mcp --transport http --host 127.0.0.1 --port 8001 --no-banner` serves Streamable HTTP on `/mcp`.
- Verified client workflows against local servers:
  - `fastmcp.Client` (both in-memory with monkeypatched OHLCV confirming `result.data` dict shape and over live HTTP `/mcp` listing `get_ohlcv_indicators`).
  - Standard `mcp` SDK `streamablehttp_client` + `ClientSession` over live HTTP `/mcp`.
  - FastMCP stdio-to-HTTP proxy (`fastmcp run http://127.0.0.1:8001/mcp --no-banner`).
  - FastMCP CLI (`fastmcp list ... --auth none` and `fastmcp call ... --auth none` validation error path).
  - FastAPI REST API (`.venv/bin/uvicorn finance_tools.app:app`) `GET /health` (200), `GET /docs` (200), and `GET /indicators/AAPL?bb_length=1` (422).
- Remaining unverified items: execution on physical Raspberry Pi ARM64 hardware (`systemd`/`ufw`) and live Yahoo Finance data fetches (egress blocked in sandbox).
