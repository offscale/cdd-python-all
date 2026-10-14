"""CLI SDK generation and parsing package."""

from __future__ import annotations

from .emit import emit_cli, emit_cli_sdk
from .emit_mcp import emit_mcp_server, extract_mcp_tools_from_spec
from .emit_mcp_adapter import emit_mcp_adapter
from .emit_mcp_sse import emit_mcp_sse_server
from .parse import CLIExtractor, extract_cli_from_ast

__all__ = [
    "CLIExtractor",
    "emit_cli",
    "emit_cli_sdk",
    "emit_mcp_adapter",
    "emit_mcp_server",
    "emit_mcp_sse_server",
    "extract_cli_from_ast",
    "extract_mcp_tools_from_spec",
]
