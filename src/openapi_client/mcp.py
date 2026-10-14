"""Native MCP Tool Adapter for the Generator SDK."""

from __future__ import annotations

from typing import Any


def get_tools() -> list[dict[str, Any]]:
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
    ]


def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Execute a tool locally using the SDK methods.

    Args:
        name: The name of the MCP tool to invoke.
        arguments: Keyword arguments for the tool.

    Returns:
        The result returned by the underlying SDK function.

    Raises:
        ValueError: If `name` is not a recognized tool.
    """
    from openapi_client import sdk

    if name == "to_openapi":
        return sdk.generate_to_openapi(**arguments)
    elif name == "from_openapi":
        return sdk.generate_from_openapi(**arguments)
    elif name == "to_docs_json":
        return sdk.generate_docs_json(**arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


def get_resources() -> list[dict[str, str]]:
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
        ValueError: If `uri` is not found.
    """
    if uri == "schema://current":
        return {"openapi": "3.0.0", "info": {"title": "cdd-python", "version": "1.0.0"}}
    raise ValueError(f"Resource not found: {uri}")


def get_prompts() -> list[dict[str, Any]]:
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
        ValueError: If `name` is not a recognized prompt.
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
    raise ValueError(f"Unknown prompt: {name}")
