# Architecture Research: MCP Server Distribution

**Domain:** MCP server integration with existing FastAPI application
**Researched:** 2026-02-02
**Confidence:** HIGH (verified with official MCP SDK docs and FastMCP documentation)

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CURRENT: Direct DB Access                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Claude Desktop                                                          │
│       │                                                                  │
│       │ stdio transport                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  MCP Server (run_mcp_server.py / backend/app/mcp/server.py) │        │
│  │  - FastMCP("On-Call Health")                                 │        │
│  │  - Tools: analysis_start, analysis_status, etc.             │        │
│  │  - Auth: require_user_api_key() with X-API-Key header       │        │
│  │  - Direct SQLAlchemy queries via SessionLocal()             │        │
│  └─────────────────────────────┬───────────────────────────────┘        │
│                                │                                         │
│                                │ Direct DB queries                       │
│                                ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │                     PostgreSQL Database                      │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Current Component Analysis

| Component | Location | Responsibility | Issue |
|-----------|----------|----------------|-------|
| `backend/app/mcp/server.py` | Embedded in backend | MCP tools with direct DB | Requires DB access, can't distribute |
| `backend/run_mcp_server.py` | Standalone runner | stdio-based MCP server | Duplicates tool code, requires DB |
| `backend/app/mcp/auth.py` | Auth module | API key validation | Coupled to SQLAlchemy models |
| `backend/app/api/endpoints/*.py` | REST API | HTTP endpoints | Already exists, mostly complete |

## Target Architecture

### Option 1: SSE-Hosted MCP Server (Same Process)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SSE-HOSTED: FastAPI + MCP in Same Process            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Claude Desktop / Cursor / Any MCP Client                               │
│       │                                                                  │
│       │ SSE transport (HTTP)                                            │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │                 FastAPI Application (main.py)                │        │
│  │  ┌─────────────────────────────────────────────────────────┐│        │
│  │  │  /mcp/sse        → SSE endpoint (SseServerTransport)   ││        │
│  │  │  /mcp/messages/  → Message handling endpoint            ││        │
│  │  └─────────────────────────────────────────────────────────┘│        │
│  │  ┌─────────────────────────────────────────────────────────┐│        │
│  │  │  /api/analysis/* → REST API endpoints                  ││        │
│  │  │  /api/integrations/* → Integration endpoints           ││        │
│  │  └─────────────────────────────────────────────────────────┘│        │
│  │                                                              │        │
│  │  MCP Server (internal)                                       │        │
│  │  - Tools call REST API via httpx (internal or localhost)    │        │
│  │  - OR tools call service layer directly (same process)      │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                │                                         │
│                                ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │                     PostgreSQL Database                      │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Option 2: PyPI-Distributed MCP Server (Separate Process)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 PYPI-DISTRIBUTED: Separate Processes                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────┐    ┌────────────────────────────────────┐   │
│  │  Claude Desktop        │    │  On-Call Health Backend             │   │
│  │                        │    │  (oncallhealth.ai)                  │   │
│  │       │                │    │                                     │   │
│  │       │ stdio          │    │  ┌────────────────────────────┐    │   │
│  │       ▼                │    │  │  REST API                  │    │   │
│  │  ┌──────────────────┐  │    │  │  /api/mcp/analysis/*      │    │   │
│  │  │ oncallhealth-mcp │  │───▶│  │  /api/mcp/integrations/*  │    │   │
│  │  │ (uvx package)    │  │HTTPS│  └────────────────────────────┘    │   │
│  │  │                  │  │    │                │                    │   │
│  │  │ - REST API client│  │    │                ▼                    │   │
│  │  │ - API key auth   │  │    │  ┌────────────────────────────┐    │   │
│  │  │ - httpx + retry  │  │    │  │     PostgreSQL Database    │    │   │
│  │  └──────────────────┘  │    │  └────────────────────────────┘    │   │
│  └────────────────────────┘    └────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Recommended Architecture: Hybrid Approach

**Recommendation:** Implement BOTH options with shared code. The REST API client layer is the critical component that enables both deployment models.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HYBRID: Shared Core + Two Transports             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │               MCP Tools Layer (shared code)                      │    │
│  │  - analysis_start(), analysis_status(), integrations_list()     │    │
│  │  - Uses OnCallHealthClient for all backend communication        │    │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │                                       │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │               OnCallHealthClient (REST API Client)               │    │
│  │  - httpx.AsyncClient with retry/backoff                         │    │
│  │  - API key injection via X-API-Key header                       │    │
│  │  - Base URL configurable (localhost or https://oncallhealth.ai) │    │
│  └───────────────────────────────┬─────────────────────────────────┘    │
│                                  │                                       │
│          ┌───────────────────────┴───────────────────────┐              │
│          │                                               │              │
│          ▼                                               ▼              │
│  ┌───────────────────────┐                ┌───────────────────────┐    │
│  │ SSE Transport         │                │ stdio Transport       │    │
│  │ (hosted at backend)   │                │ (PyPI uvx package)    │    │
│  │                       │                │                       │    │
│  │ Client config:        │                │ Client config:        │    │
│  │ url: /mcp/sse        │                │ command: uvx          │    │
│  │                       │                │ args: oncallhealth-mcp│    │
│  └───────────────────────┘                └───────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Boundaries

### New Components to Create

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `oncallhealth_mcp/client.py` | New package | REST API client with httpx |
| `oncallhealth_mcp/tools.py` | New package | MCP tool definitions using client |
| `oncallhealth_mcp/server.py` | New package | FastMCP server wrapper |
| `oncallhealth_mcp/__main__.py` | New package | CLI entry point for uvx |
| `backend/app/mcp/sse.py` | Backend | SSE transport integration |

### Modified Components

| Component | Changes |
|-----------|---------|
| `backend/app/main.py` | Mount SSE endpoints at /mcp |
| `backend/app/api/endpoints/` | Add MCP-specific endpoints if needed |
| `backend/requirements.txt` | Add `mcp`, `starlette` (if not present) |

### Components to Deprecate/Remove

| Component | Reason |
|-----------|--------|
| `backend/run_mcp_server.py` | Replaced by oncallhealth-mcp package |
| Direct DB access in MCP tools | Replaced by REST API client |

## SSE Integration Pattern

Based on official MCP SDK and FastMCP documentation:

### Pattern 1: SseServerTransport with Starlette (Recommended)

```python
# backend/app/mcp/sse.py
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route

def create_sse_server(mcp_server):
    """Create Starlette app for SSE transport."""
    transport = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server._mcp_server.run(
                streams[0], streams[1],
                mcp_server._mcp_server.create_initialization_options()
            )

    routes = [
        Route("/sse/", endpoint=handle_sse),
        Mount("/messages/", app=transport.handle_post_message),
    ]

    return Starlette(routes=routes)
```

### Pattern 2: FastMCP http_app() Method

```python
# backend/app/main.py
from fastmcp import FastMCP

mcp = FastMCP("On-Call Health")
mcp_app = mcp.http_app(path='/mcp')

# Mount to FastAPI
app = FastAPI(lifespan=mcp_app.lifespan)
app.mount("/mcp", mcp_app)
```

**Recommendation:** Use Pattern 1 (SseServerTransport) because:
1. More control over authentication middleware
2. Clearer separation of concerns
3. Better compatibility with existing FastAPI middleware

## REST API Client Design

### Client Architecture

```python
# oncallhealth_mcp/client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

class OnCallHealthClient:
    """REST API client for On-Call Health backend."""

    def __init__(
        self,
        base_url: str = "https://oncallhealth.ai",
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("OCH_API_KEY")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
    )
    async def start_analysis(
        self,
        days_back: int = 30,
        include_weekends: bool = True,
        integration_id: int | None = None,
    ) -> dict:
        """Start a new burnout analysis."""
        response = await self._client.post(
            "/api/analysis/start",
            json={
                "days_back": days_back,
                "include_weekends": include_weekends,
                "integration_id": integration_id,
            },
        )
        response.raise_for_status()
        return response.json()

    # Similar methods for other endpoints...
```

### Error Handling Strategy

```python
class OnCallHealthError(Exception):
    """Base error for API client."""
    pass

class AuthenticationError(OnCallHealthError):
    """API key invalid or missing."""
    pass

class RateLimitError(OnCallHealthError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after

async def _handle_response(response: httpx.Response) -> dict:
    """Handle API response with proper error mapping."""
    if response.status_code == 401:
        raise AuthenticationError("Invalid or missing API key")
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        raise RateLimitError(retry_after)
    if response.status_code >= 400:
        raise OnCallHealthError(f"API error: {response.status_code}")
    return response.json()
```

## PyPI Package Structure

```
oncallhealth-mcp/
├── pyproject.toml
├── README.md
├── src/
│   └── oncallhealth_mcp/
│       ├── __init__.py
│       ├── __main__.py      # Entry point: python -m oncallhealth_mcp
│       ├── client.py        # REST API client
│       ├── server.py        # FastMCP server with tools
│       └── tools.py         # Tool definitions
└── tests/
    └── ...
```

### pyproject.toml Configuration

```toml
[project]
name = "oncallhealth-mcp"
version = "0.1.0"
description = "MCP server for On-Call Health burnout analysis"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "tenacity>=8.0.0",
]

[project.scripts]
oncallhealth-mcp = "oncallhealth_mcp.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "oncallhealth": {
      "command": "uvx",
      "args": ["oncallhealth-mcp"],
      "env": {
        "OCH_API_KEY": "och_live_..."
      }
    }
  }
}
```

## Refactoring Strategy: Direct DB to REST API

### Phase 1: Create REST API Client

Map existing direct DB operations to REST API calls:

| Current (Direct DB) | Target (REST API) | Endpoint |
|---------------------|-------------------|----------|
| `db.query(Analysis).filter(...)` | `client.get_analysis(id)` | `GET /api/analysis/{id}` |
| `db.add(Analysis(...))` | `client.start_analysis(...)` | `POST /api/analysis/start` |
| `db.query(RootlyIntegration).filter(...)` | `client.list_integrations()` | `GET /api/integrations` |

### Phase 2: Create MCP-Specific API Endpoints

Some MCP operations may need dedicated endpoints:

```python
# backend/app/api/endpoints/mcp_api.py
router = APIRouter(prefix="/api/mcp")

@router.get("/integrations")
async def list_integrations_for_mcp(
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    """List all integrations for MCP client."""
    user = get_user_from_api_key(api_key, db)
    # Return serialized integrations
    ...
```

### Phase 3: Update MCP Tools to Use Client

```python
# oncallhealth_mcp/tools.py
from oncallhealth_mcp.client import OnCallHealthClient

# Global client instance (or pass via context)
_client: OnCallHealthClient | None = None

def get_client() -> OnCallHealthClient:
    global _client
    if _client is None:
        _client = OnCallHealthClient()
    return _client

@mcp_server.tool()
async def analysis_start(
    days_back: int = 30,
    include_weekends: bool = True,
    integration_id: int | None = None,
) -> dict:
    """Start a new burnout analysis."""
    client = get_client()
    async with client:
        return await client.start_analysis(
            days_back=days_back,
            include_weekends=include_weekends,
            integration_id=integration_id,
        )
```

## Data Flow

### SSE-Hosted Flow

```
1. MCP Client connects to oncallhealth.ai/mcp/sse
2. SSE connection established
3. Client sends tool invocation via /mcp/messages/
4. MCP server receives tool call
5. Tool calls OnCallHealthClient (localhost or internal)
6. REST API processes request, returns response
7. Tool formats response
8. SSE pushes response to client
```

### PyPI-Distributed Flow

```
1. uvx launches oncallhealth-mcp locally
2. stdio transport established with Claude Desktop
3. Claude sends tool invocation via stdin
4. Tool calls OnCallHealthClient (https://oncallhealth.ai)
5. HTTPS request to backend API
6. Backend processes request, returns response
7. Tool formats response
8. stdout returns response to Claude
```

## Authentication Architecture

### Current: API Key in MCP Context

```python
# Current auth flow (direct DB)
def require_user_api_key(ctx, db):
    api_key = extract_api_key_header(ctx)  # From X-API-Key
    # Validate against DB
    return user
```

### Target: API Key in HTTP Header

```python
# New auth flow (REST API)
class OnCallHealthClient:
    def __init__(self, api_key: str):
        self.headers = {"X-API-Key": api_key}

    async def request(self, method, path, **kwargs):
        response = await self._client.request(
            method, path, headers=self.headers, **kwargs
        )
        # Backend validates API key as normal
        return response
```

### SSE Authentication Challenge

The MCP specification does not define standard authentication for SSE. Options:

1. **Network-level security** (VPN, IP whitelist) - simple but inflexible
2. **Reverse proxy auth** - nginx/traefik handles auth before MCP
3. **Custom auth middleware** - validate API key on SSE connect
4. **Query parameter token** - pass API key in SSE URL (less secure)

**Recommendation:** Use custom middleware that validates X-API-Key header on the `/mcp/sse` endpoint connection. The backend already has this pattern.

## Build Order (Dependencies)

```
Phase 1: REST API Client Layer
├── 1.1 Create oncallhealth_mcp package structure
├── 1.2 Implement OnCallHealthClient
├── 1.3 Add error handling and retry logic
└── 1.4 Write client tests

Phase 2: MCP Tools Refactor
├── 2.1 Create tools.py with client-based implementations
├── 2.2 Migrate analysis_start, analysis_status, etc.
├── 2.3 Update auth to use API key in HTTP header
└── 2.4 Write tool integration tests

Phase 3: SSE Transport Integration
├── 3.1 Create sse.py with SseServerTransport
├── 3.2 Mount SSE endpoints in main.py
├── 3.3 Add authentication middleware for SSE
└── 3.4 Test SSE connection with MCP Inspector

Phase 4: PyPI Distribution
├── 4.1 Create pyproject.toml with entry points
├── 4.2 Create __main__.py for CLI
├── 4.3 Test with uvx locally
├── 4.4 Publish to PyPI
└── 4.5 Test uvx installation and Claude Desktop config

Phase 5: Documentation & Cleanup
├── 5.1 Update README with installation instructions
├── 5.2 Deprecate run_mcp_server.py
└── 5.3 Add MCP connection examples to docs
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mixing Transport Concerns with Business Logic

**What people do:** Put SSE connection handling code inside tool functions
**Why it's wrong:** Makes tools untestable and non-portable
**Do this instead:** Keep tools transport-agnostic, let server handle transport

### Anti-Pattern 2: Hardcoded Base URLs

**What people do:** `base_url = "https://oncallhealth.ai"` everywhere
**Why it's wrong:** Breaks local development and testing
**Do this instead:** Use environment variable with sensible default

```python
base_url = os.getenv("OCH_API_URL", "https://oncallhealth.ai")
```

### Anti-Pattern 3: Synchronous HTTP in Async Tools

**What people do:** Use `requests` library in async MCP tools
**Why it's wrong:** Blocks event loop, degrades performance
**Do this instead:** Use `httpx.AsyncClient` consistently

### Anti-Pattern 4: No Retry Logic

**What people do:** Single HTTP request with no retry
**Why it's wrong:** Network flakiness causes tool failures
**Do this instead:** Use tenacity with exponential backoff

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    retry=retry_if_exception_type(httpx.TransportError),
)
async def make_request(self, ...):
    ...
```

### Anti-Pattern 5: Exposing Raw HTTP Errors to MCP

**What people do:** Let httpx exceptions bubble up to MCP client
**Why it's wrong:** MCP client sees confusing transport errors
**Do this instead:** Catch and translate to domain errors

```python
try:
    response = await client.start_analysis(...)
except AuthenticationError:
    return {"error": "Invalid API key. Check your OCH_API_KEY setting."}
except RateLimitError as e:
    return {"error": f"Rate limited. Try again in {e.retry_after} seconds."}
```

## Scalability Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 users | Single FastAPI process with SSE, no changes needed |
| 100-1K users | Consider connection pooling for SSE, monitor memory |
| 1K+ users | Move SSE to dedicated workers, use Streamable HTTP transport |

### SSE Connection Limits

SSE holds open connections. With many concurrent users:
- Each SSE connection consumes a file descriptor
- Default uvicorn workers may need tuning
- Consider Streamable HTTP for scale (newer MCP transport)

### Streamable HTTP (Future Consideration)

MCP is introducing Streamable HTTP transport that may supersede SSE for some use cases. The architecture should be designed to accommodate this:

```python
# Future: Streamable HTTP transport
mcp_app = mcp.streamable_http_app()  # Returns FastAPI app with /mcp route
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| PostgreSQL | Via REST API (not direct) | MCP tools never touch DB directly |
| oncallhealth.ai | HTTPS REST API | Authenticated via X-API-Key header |
| Claude Desktop | stdio or SSE | Transport abstracted away |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| MCP Tools <-> REST API | HTTP/HTTPS | Always async httpx |
| SSE Server <-> FastAPI | Starlette mount | Same process, share lifespan |
| PyPI Package <-> Backend | HTTPS only | No shared state |

## Sources

- [FastMCP FastAPI Integration](https://gofastmcp.com/integrations/fastapi) - HIGH confidence
- [MCP Python SDK (GitHub)](https://github.com/modelcontextprotocol/python-sdk) - HIGH confidence
- [Building SSE MCP Server with FastAPI](https://www.ragie.ai/blog/building-a-server-sent-events-sse-mcp-server-with-fastapi) - MEDIUM confidence
- [mcp-server-git PyPI](https://pypi.org/project/mcp-server-git/) - HIGH confidence (official example)
- [httpx Transports Documentation](https://www.python-httpx.org/advanced/transports/) - HIGH confidence
- [Python Packaging Guide - pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) - HIGH confidence
- [httpx-retries Package](https://will-ockmore.github.io/httpx-retries/) - MEDIUM confidence

---
*Architecture research for: MCP Server Distribution*
*Researched: 2026-02-02*
