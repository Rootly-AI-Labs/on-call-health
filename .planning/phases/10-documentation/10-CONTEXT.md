# Phase 10: Documentation - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Create user-facing documentation so users can successfully deploy the MCP server using either the hosted SSE endpoint or the PyPI package. This includes setup instructions, environment variable reference, migration guidance from v1.0 (stdio+direct-DB mode), and AWS deployment documentation for Phase 11.

**In scope:**
- Hosted SSE endpoint setup guide (Claude Desktop configuration)
- PyPI package installation guide (augments existing README)
- Environment variable reference (consolidated table)
- Migration guide from v1.0 to v1.1 (breaking change documentation)
- AWS deployment documentation (for Phase 11 use)

**Out of scope:**
- Code changes (implementation complete in Phases 5-9)
- API endpoint documentation (separate from MCP docs)
- Internal development setup (already documented in existing MCP_SETUP.md)
- Monitoring/observability guides (deferred to post-v1.1)

</domain>

<decisions>
## Implementation Decisions

### Documentation Structure and Organization

**Decision: Separate deployment guides (modular approach)**

User was presented with 3 options but discussion focused on specific content decisions rather than overall structure. Based on Phase 10 requirements (DOCS-01 through DOCS-06) and existing documentation patterns, the implied structure is:

- `docs/DEPLOYMENT_SSE.md` - Hosted SSE endpoint setup
- `docs/DEPLOYMENT_PYPI.md` - PyPI package setup (or augment existing `packages/oncallhealth-mcp/README.md`)
- `docs/DEPLOYMENT_AWS.md` - AWS deployment (for Phase 11)
- `docs/MIGRATION.md` - v1.0 → v1.1 migration guide
- Single environment variable reference table (location TBD during planning)

### Hosted SSE Endpoint Documentation Scope

**Troubleshooting section: Minimal only**
- Include health check verification (`/health` endpoint)
- Document basic error messages (invalid API key, connection limit, rate limit)
- Do NOT include extensive debugging steps
- Do NOT document network troubleshooting (firewall, VPN, proxy issues)

**Transport comparison: Not included**
- Do NOT explain SSE vs Streamable HTTP difference
- Do NOT include comparison table of `/sse` vs `/mcp` endpoints
- Do NOT explain which clients use which transport
- Just document the hosted endpoint URL (e.g., `https://mcp.oncallhealth.ai`)

**Security best practices: Not included**
- Do NOT include dedicated security section
- Assume users understand API key security basics
- Do NOT document HTTPS requirements (obvious)
- Do NOT explain data transmission details
- Do NOT include key rotation guidance

**Architecture diagram: Not included**
- Do NOT create visual diagram showing Claude Desktop → SSE → REST API → backend
- Text-based documentation only
- No architectural flow diagrams

### Environment Variables Documentation Format

**Format: Single consolidated reference table**
- One comprehensive table with ALL variables across all deployment modes
- Columns should include: Variable, Required For (which deployment mode), Default, Description
- Modes to distinguish: PyPI, Hosted SSE, AWS deployment
- Variables to document:
  - `ONCALLHEALTH_API_KEY` (required for all modes)
  - `ONCALLHEALTH_API_URL` (optional, defaults to production)
  - `LOG_LEVEL` (optional, for debugging)
  - AWS-specific vars (Phase 11: ECS task definition variables)
- Location of consolidated table: TBD during planning (could be in main docs/ directory or linked from each guide)

### Migration Guide Depth

**Not explicitly discussed, defer to Claude's discretion during planning.**

Implied requirement from DOCS-04: Must document breaking change from v1.0 stdio+direct-DB mode to v1.1 distributed REST API mode.

### Claude's Discretion

User delegated these decisions to Claude during planning:

- Exact file locations (`docs/` directory vs other locations)
- Whether to augment existing `packages/oncallhealth-mcp/README.md` or create separate `docs/DEPLOYMENT_PYPI.md`
- Migration guide depth (minimal vs step-by-step)
- How to organize the consolidated environment variable table
- Specific wording for error messages in troubleshooting section
- Hosted SSE endpoint URL (will be determined in Phase 11 AWS deployment)
- Whether to archive old legacy guides (MCP_SETUP.md, MCP_CLAUDE_CODE_SETUP.md)

</decisions>

<specifics>
## Specific Ideas

**Existing documentation to reference:**
- `packages/oncallhealth-mcp/README.md` - Already comprehensive (183 lines), covers PyPI installation, Claude Desktop config, CLI reference, available tools
- `docs/MCP_SETUP.md` - Legacy stdio+direct-DB setup (will become outdated after v1.1)
- `docs/MCP_CLAUDE_CODE_SETUP.md` - Legacy Claude Code MCP setup (also outdated after v1.1)

**Requirements coverage:**
- DOCS-01: SSE endpoint usage guide (Claude Desktop config) → `docs/DEPLOYMENT_SSE.md`
- DOCS-02: PyPI/uvx installation guide → augment existing README or create `docs/DEPLOYMENT_PYPI.md`
- DOCS-03: Environment variable reference → single consolidated table
- DOCS-04: Migration notice (breaking change) → `docs/MIGRATION.md`
- DOCS-05: AWS deployment guide → `docs/DEPLOYMENT_AWS.md` (for Phase 11)
- DOCS-06: Docker build and deployment → covered in DOCS-05

**User workflow context:**
- Hosted SSE: User gets API key → configures Claude Desktop with SSE endpoint URL → connects
- PyPI: User runs `pip install oncallhealth-mcp` or `uvx oncallhealth-mcp` → sets `ONCALLHEALTH_API_KEY` → runs CLI
- Migration: User on v1.0 (stdio+direct-DB) → generates API key → updates config to v1.1 (SSE or PyPI) → removes DATABASE_URL

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-documentation*
*Context gathered: 2026-02-03*
