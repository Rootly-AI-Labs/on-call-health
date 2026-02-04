"""CLI entry point for oncallhealth-mcp server."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import NoReturn


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="oncallhealth-mcp",
        description="MCP server for On-Call Health burnout analysis",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (http transport only, default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (http transport only, default: 8000)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser.parse_args()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the server."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def validate_config() -> None:
    """Validate required configuration is present."""
    api_key = os.environ.get("ONCALLHEALTH_API_KEY")
    if not api_key:
        print(
            "Error: ONCALLHEALTH_API_KEY environment variable is required.\n\n"
            "Set it with:\n"
            "  export ONCALLHEALTH_API_KEY=your_api_key\n\n"
            "Or pass it inline:\n"
            "  ONCALLHEALTH_API_KEY=your_api_key oncallhealth-mcp",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> NoReturn:
    """Main entry point for the CLI."""
    args = parse_args()
    setup_logging(args.verbose)
    validate_config()

    # Import server lazily to avoid import errors before validation
    from oncallhealth_mcp.server import mcp_server

    logger = logging.getLogger(__name__)
    logger.info(f"Starting On-Call Health MCP server (transport={args.transport})")

    if args.transport == "stdio":
        # Run with stdio transport
        mcp_server.run()
    else:
        # Run with HTTP transport using uvicorn
        try:
            import uvicorn
        except ImportError:
            print(
                "Error: uvicorn is required for HTTP transport.\n"
                "Install with: pip install uvicorn",
                file=sys.stderr,
            )
            sys.exit(1)

        # Get ASGI app from FastMCP
        if hasattr(mcp_server, "app"):
            app = mcp_server.app
        elif hasattr(mcp_server, "asgi_app"):
            app = mcp_server.asgi_app()
        elif hasattr(mcp_server, "sse_app"):
            app = mcp_server.sse_app()
        else:
            print("Error: Cannot resolve ASGI app from FastMCP server", file=sys.stderr)
            sys.exit(1)

        uvicorn.run(app, host=args.host, port=args.port)

    sys.exit(0)


if __name__ == "__main__":
    main()
