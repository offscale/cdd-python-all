"""Native MCP Tool Adapter for the Generator SDK."""


def get_tools():
    """Return the available SDK generator tools mapped to the MCP tool schema."""
    return [
        {
            "name": "generate_to_openapi",
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
            "name": "generate_from_openapi",
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
            "name": "generate_docs_json",
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


def execute_tool(name: str, arguments: dict):
    """Execute a tool locally using the SDK methods."""
    from openapi_client import sdk

    if name == "generate_to_openapi":
        return sdk.generate_to_openapi(**arguments)
    elif name == "generate_from_openapi":
        return sdk.generate_from_openapi(**arguments)
    elif name == "generate_docs_json":
        return sdk.generate_docs_json(**arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


def get_resources():
    """Return the available SDK internal resources mapped to the MCP schema."""
    return [
        {
            "uri": "schema://current",
            "name": "Current internal OpenAPI specification",
            "mimeType": "application/json",
        }
    ]


def read_resource(uri: str):
    """Read a specific resource locally using SDK methods."""
    if uri == "schema://current":
        return {"openapi": "3.0.0", "info": {"title": "cdd-python", "version": "1.0.0"}}
    raise ValueError(f"Resource not found: {uri}")


def get_prompts():
    """Return the available SDK prompts mapped to the MCP schema."""
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


def get_prompt(name: str, arguments: dict = None):
    """Get a specific prompt with filled arguments."""
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
