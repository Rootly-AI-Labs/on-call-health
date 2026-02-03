# oncallhealth-mcp

[![PyPI version](https://badge.fury.io/py/oncallhealth-mcp.svg)](https://badge.fury.io/py/oncallhealth-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

MCP server for On-Call Health burnout analysis. Connects AI assistants like Claude to your on-call data for workload insights.

## Installation

### Using uvx (recommended)

```bash
uvx oncallhealth-mcp
```

### Using pip

```bash
pip install oncallhealth-mcp
```

## Quick Start

1. Get your API key from [oncallhealth.ai/settings/api-keys](https://oncallhealth.ai/settings/api-keys)

2. Run the server:

```bash
# Using uvx
ONCALLHEALTH_API_KEY=och_live_... uvx oncallhealth-mcp

# Using pip installation
ONCALLHEALTH_API_KEY=och_live_... oncallhealth-mcp
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ONCALLHEALTH_API_KEY` | Yes | - | API key from oncallhealth.ai |
| `ONCALLHEALTH_API_URL` | No | `https://api.oncallhealth.ai` | API endpoint URL |

## CLI Reference

```
usage: oncallhealth-mcp [-h] [--transport {stdio,http}] [--host HOST]
                        [--port PORT] [-v] [--version]

MCP server for On-Call Health burnout analysis

options:
  -h, --help            show this help message and exit
  --transport {stdio,http}
                        Transport to use (default: stdio)
  --host HOST           Host to bind to (http transport only, default: 127.0.0.1)
  --port PORT           Port to bind to (http transport only, default: 8000)
  -v, --verbose         Enable verbose logging
  --version             show program's version number and exit
```

### Transport Options

- **stdio** (default): Standard input/output transport. Used by Claude Desktop and most MCP clients.
- **http**: HTTP transport with Server-Sent Events. Useful for web-based clients or debugging.

### Examples

```bash
# Run with stdio transport (default)
ONCALLHEALTH_API_KEY=och_live_... oncallhealth-mcp

# Run with HTTP transport
ONCALLHEALTH_API_KEY=och_live_... oncallhealth-mcp --transport http --port 8080

# Enable verbose logging
ONCALLHEALTH_API_KEY=och_live_... oncallhealth-mcp --verbose
```

## Claude Desktop Integration

Add to your `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### Using uvx (recommended)

```json
{
  "mcpServers": {
    "oncallhealth": {
      "command": "uvx",
      "args": ["oncallhealth-mcp"],
      "env": {
        "ONCALLHEALTH_API_KEY": "och_live_your_api_key_here"
      }
    }
  }
}
```

### Using pip installation

```json
{
  "mcpServers": {
    "oncallhealth": {
      "command": "oncallhealth-mcp",
      "env": {
        "ONCALLHEALTH_API_KEY": "och_live_your_api_key_here"
      }
    }
  }
}
```

### Security Note

Your API key in the config file should be kept secure. Consider using environment variables or a secrets manager in production environments.

## Available MCP Tools

### analysis_start

Start a new burnout analysis for your on-call data.

**Parameters:**
- `days_back` (int, default: 30): Number of days to analyze
- `include_weekends` (bool, default: true): Include weekend data
- `integration_id` (int, optional): Specific integration to analyze

### analysis_status

Check the status of a running analysis.

**Parameters:**
- `analysis_id` (int): ID of the analysis to check

### analysis_results

Get full results for a completed analysis.

**Parameters:**
- `analysis_id` (int): ID of the completed analysis

### analysis_current

Get the most recent analysis for your account.

**Parameters:** None

### integrations_list

List all connected integrations (Rootly, GitHub, Slack, Jira, Linear).

**Parameters:** None

## Resources

### oncallhealth://methodology

Provides a brief description of the On-Call Health methodology for measuring workload and burnout risk.

## Prompts

### weekly_brief

Template for generating a weekly on-call health summary.

**Parameters:**
- `team_name` (str): Name of the team to summarize

## Links

- [On-Call Health](https://oncallhealth.ai) - Main website
- [Documentation](https://oncallhealth.ai/docs/mcp) - MCP documentation
- [GitHub Issues](https://github.com/on-call-health/oncallhealth-mcp/issues) - Report bugs

## License

MIT
