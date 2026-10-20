"""Native MCP Tool Adapter for the Generator SDK."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any, TypedDict

from openapi_client.exceptions import MCPProtocolError


class MCPToolDefinition(TypedDict):
    """Typed dictionary representing an MCP tool definition."""

    name: str
    description: str
    inputSchema: dict[str, Any]


class MCPResourceDefinition(TypedDict):
    """Typed dictionary representing an MCP resource descriptor."""

    uri: str
    name: str
    mimeType: str


class MCPPromptDefinition(TypedDict):
    """Typed dictionary representing an MCP prompt descriptor."""

    name: str
    description: str
    arguments: list[dict[str, Any]]


def _pkg_version() -> str:
    """Resolve the installed package version string.

    Returns:
        The installed version or fallback `'0.0.4'`.
    """
    try:
        return version("openapi-python-client")
    except PackageNotFoundError:  # pragma: no cover
        return "0.0.4"


def get_tools() -> list[MCPToolDefinition]:
    """Return the available SDK generator tools mapped to the MCP tool schema.

    Returns:
        A list of MCP tool definition dictionaries.
    """
    return [
        {
            "name": "to_openapi",
            "description": "Generate an OpenAPI specification from source code.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "The directory to scan",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "The path to save the generated JSON",
                    },
                },
                "required": ["input_dir"],
            },
        },
        {
            "name": "from_openapi",
            "description": "Generate code from an OpenAPI specification.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "The OpenAPI JSON file path",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "The directory to generate the SDK into",
                    },
                    "subcommand": {
                        "type": "string",
                        "description": "Target generation strategy, eg: to_sdk",
                    },
                    "no_github_actions": {"type": "boolean"},
                    "no_installable_package": {"type": "boolean"},
                    "tests": {"type": "boolean"},
                },
                "required": ["input_path", "output_dir"],
            },
        },
        {
            "name": "to_docs_json",
            "description": "Generate JSON documentation with code snippets for an OpenAPI specification.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": {"type": "string"},
                    "output_path": {"type": "string"},
                    "no_imports": {"type": "boolean"},
                    "no_wrapping": {"type": "boolean"},
                },
                "required": ["input_path"],
            },
        },
        {
            "name": "to_arazzo",
            "description": "Generate an Arazzo 1.1.0 specification from Python workflow source code.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "The workflow file or directory to scan",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "The path to save the generated Arazzo JSON",
                    },
                },
                "required": ["input_dir"],
            },
        },
        {
            "name": "from_arazzo",
            "description": "Generate Python workflow orchestrators, CLI, server routes, or tests from an Arazzo 1.1.0 specification.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": {
                        "type": "string",
                        "description": "The Arazzo 1.1.0 JSON file path",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "The directory to generate the artifacts into",
                    },
                    "subcommand": {
                        "type": "string",
                        "description": "Target generation strategy: to_sdk, to_sdk_cli, to_server, to_tests",
                    },
                },
                "required": ["input_path", "output_dir"],
            },
        },
        {
            "name": "sync_dir",
            "description": "Synchronize an OpenAPI/Arazzo specification with Python source code in a directory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_dir": {
                        "type": "string",
                        "description": "The project directory to synchronize",
                    },
                    "truth": {
                        "type": "string",
                        "description": "Optional single source of truth",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional output directory",
                    },
                },
                "required": ["input_dir"],
            },
        },
    ]


def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Execute a tool locally using the SDK methods.

    Args:
        name: The name of the MCP tool to invoke.
        arguments: Keyword arguments for the tool.

    Returns:
        The result returned by the underlying SDK function.

    Raises:
        MCPProtocolError: If `name` is not a recognized tool.
    """
    from openapi_client import sdk

    norm_args = dict(arguments)
    if name == "to_openapi":
        if "input_path" in norm_args and "input_dir" not in norm_args:
            norm_args["input_dir"] = norm_args.pop("input_path")
        return sdk.generate_to_openapi(**norm_args)
    elif name == "from_openapi":
        return sdk.generate_from_openapi(**norm_args)
    elif name == "to_arazzo":
        if "input_path" in norm_args and "input_dir" not in norm_args:
            norm_args["input_dir"] = norm_args.pop("input_path")
        return sdk.generate_to_arazzo(**norm_args)
    elif name == "from_arazzo":
        return sdk.generate_from_arazzo(**norm_args)
    elif name == "to_docs_json":
        if "output_file" in norm_args and "output_path" not in norm_args:
            norm_args["output_path"] = norm_args.pop("output_file")
        return sdk.generate_docs_json(**norm_args)
    elif name == "sync_dir":
        if "project_dir" in norm_args and "input_dir" not in norm_args:
            norm_args["input_dir"] = norm_args.pop("project_dir")
        return sdk.run_sync(**norm_args)
    else:
        raise MCPProtocolError(f"Unknown tool: {name}")


def get_resources() -> list[MCPResourceDefinition]:
    """Return the available SDK internal resources mapped to the MCP schema.

    Returns:
        A list of MCP resource descriptor dictionaries.
    """
    return [
        {
            "uri": "schema://current",
            "name": "Current internal OpenAPI specification",
            "mimeType": "application/json",
        }
    ]


def read_resource(uri: str) -> dict[str, Any]:
    """Read a specific resource locally using SDK methods.

    Args:
        uri: The resource URI to read.

    Returns:
        The resource dictionary payload.

    Raises:
        MCPProtocolError: If `uri` is not found.
    """
    if uri == "schema://current":
        return {
            "openapi": "3.2.0",
            "info": {"title": "cdd-python", "version": _pkg_version()},
        }
    raise MCPProtocolError(f"Resource not found: {uri}")


def get_prompts() -> list[MCPPromptDefinition]:
    """Return the available SDK prompts mapped to the MCP schema.

    Returns:
        A list of MCP prompt descriptor dictionaries.
    """
    return [
        {
            "name": "generate_tests",
            "description": "Generate tests for a specific SDK component",
            "arguments": [
                {
                    "name": "component",
                    "description": "The component to test",
                    "required": True,
                }
            ],
        }
    ]


def get_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Get a specific prompt with filled arguments.

    Args:
        name: The prompt name to retrieve.
        arguments: Optional dictionary of prompt template arguments.

    Returns:
        The rendered MCP prompt response dictionary.

    Raises:
        MCPProtocolError: If `name` is not a recognized prompt.
    """
    if name == "generate_tests":
        comp = (arguments or {}).get("component", "unknown component")
        return {
            "description": f"Generate tests for {comp}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"Please generate tests for the {comp} component.",
                    },
                }
            ],
        }
    raise MCPProtocolError(f"Unknown prompt: {name}")
