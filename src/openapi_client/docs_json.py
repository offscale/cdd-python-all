"""OpenAPI and Arazzo documentation JSON snippet generator."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from openapi_client.arazzo.parse import parse_arazzo_json
from openapi_client.functions.utils import sanitize_name
from openapi_client.models import PathItem
from openapi_client.openapi.keywords import HTTP_METHODS
from openapi_client.openapi.parse import parse_openapi_json


def _build_code_entry(
    imports_str: str,
    wrapper_start_str: str,
    snippet_lines: list[str],
    wrapper_end_str: str,
    no_imports: bool,
    no_wrapping: bool,
) -> dict[str, str]:
    """Build a structured documentation snippet entry with assembled code.

    Args:
        imports_str: Import block string.
        wrapper_start_str: Wrapper prologue string (e.g. `def main(): ...`).
        snippet_lines: Core unindented SDK call lines.
        wrapper_end_str: Wrapper epilogue string (e.g. `if __name__ == "__main__": ...`).
        no_imports: If True, omit the `imports` component.
        no_wrapping: If True, omit the `wrapper_start` and `wrapper_end` components.

    Returns:
        Dictionary containing structured code components and assembled `code`.
    """
    nl = chr(10)
    entry: dict[str, str] = {}
    full_lines: list[str] = []

    if not no_imports:
        entry["imports"] = imports_str
        full_lines.append(imports_str)
        full_lines.append("")

    if not no_wrapping:
        entry["wrapper_start"] = wrapper_start_str
        full_lines.append(wrapper_start_str)

    indent = "    " if not no_wrapping else ""
    entry["snippet"] = nl.join(snippet_lines)
    for line in snippet_lines:
        full_lines.append(f"{indent}{line}")

    if not no_wrapping:
        entry["wrapper_end"] = wrapper_end_str
        full_lines.append("")
        full_lines.append(wrapper_end_str)

    entry["code"] = nl.join(full_lines)
    return entry


def _build_operations_docs(
    items: dict[str, PathItem] | None,
    no_imports: bool,
    no_wrapping: bool,
) -> dict[str, dict[str, dict[str, str]]]:
    """Build structured documentation snippets for a mapping of PathItems.

    Args:
        items: Mapping of path or webhook name to `PathItem` models.
        no_imports: If True, omit import statements.
        no_wrapping: If True, omit `main()` wrapper statements.

    Returns:
        Nested dictionary mapping path/webhook key and HTTP method to snippet objects.
    """
    nl = chr(10)
    docs_map: dict[str, dict[str, dict[str, str]]] = {}
    if not items:
        return docs_map

    imports_str = nl.join(["import json", "from generated_client import Client"])
    wrapper_start_str = nl.join(
        ["def main():", '    client = Client(base_url="https://api.example.com")']
    )
    wrapper_end_str = nl.join(['if __name__ == "__main__":', "    main()"])

    for item_key, path_item in items.items():
        method_map: dict[str, dict[str, str]] = {}
        for method in HTTP_METHODS:
            operation = getattr(path_item, method, None)
            if operation:
                raw_op_id = (
                    operation.operationId
                    or f"{method}_{item_key.replace('/', '_').strip('_')}"
                )
                op_id = sanitize_name(raw_op_id)

                snippet_lines: list[str] = []
                args: list[str] = []
                if operation.parameters:
                    for param in operation.parameters:
                        if hasattr(param, "name"):
                            p_name = sanitize_name(param.name)
                            snippet_lines.append(f"{p_name} = 'example'")
                            args.append(f"{p_name}={p_name}")

                if getattr(operation, "requestBody", None):
                    snippet_lines.append("body = {}")
                    args.append("body=body")

                args_str = ", ".join(args)
                snippet_lines.append(f"response = client.{op_id}({args_str})")
                snippet_lines.append("print(response)")

                method_map[method.lower()] = _build_code_entry(
                    imports_str=imports_str,
                    wrapper_start_str=wrapper_start_str,
                    snippet_lines=snippet_lines,
                    wrapper_end_str=wrapper_end_str,
                    no_imports=no_imports,
                    no_wrapping=no_wrapping,
                )

        if method_map:
            docs_map[item_key] = method_map

    return docs_map


def _write_or_print_docs(data: dict[str, Any], output_file: str | None) -> None:
    """Write documentation JSON payload to a file (or directory/docs.json) or stdout.

    Args:
        data: Dictionary payload to serialize as formatted JSON.
        output_file: Optional file or directory path; prints to stdout if None.
    """
    if output_file:
        out_path = Path(output_file)
        if out_path.is_dir():
            out_path = out_path / "docs.json"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        print(json.dumps(data, indent=2))


def generate_docs_json(
    input_path: str,
    no_imports: bool,
    no_wrapping: bool,
    output_file: str | None,
) -> None:
    """Parse an OpenAPI or Arazzo spec and output JSON documentation with code snippets.

    Args:
        input_path: File path or HTTP(S) URL to the OpenAPI or Arazzo specification.
        no_imports: If True, omit import statements from generated snippets.
        no_wrapping: If True, omit `main()` wrapper from generated snippets.
        output_file: Optional file or directory path to write JSON output; prints to stdout if None.
    """
    if input_path.startswith(("http://", "https://")):
        req = urllib.request.Request(input_path)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
    else:
        spec_path = Path(input_path)
        content = spec_path.read_text(encoding="utf-8")

    nl = chr(10)
    raw_doc = json.loads(content)
    if "arazzo" in raw_doc:
        arazzo_spec = parse_arazzo_json(content)
        workflows_docs: dict[str, dict[str, str]] = {}
        imports_str = "from workflows import Workflows"
        wrapper_start_str = nl.join(["def main():", "    runner = Workflows()"])
        wrapper_end_str = nl.join(['if __name__ == "__main__":', "    main()"])
        for wf in arazzo_spec.workflows:
            wf_fn = sanitize_name(wf.workflowId) or "run_workflow"
            snippet_lines = [
                f"result = runner.{wf_fn}()",
                "print(result)",
            ]
            workflows_docs[wf.workflowId] = _build_code_entry(
                imports_str=imports_str,
                wrapper_start_str=wrapper_start_str,
                snippet_lines=snippet_lines,
                wrapper_end_str=wrapper_end_str,
                no_imports=no_imports,
                no_wrapping=no_wrapping,
            )
        arazzo_result: dict[str, Any] = {
            "endpoints": {},
            "webhooks": {},
            "workflows": workflows_docs,
        }
        _write_or_print_docs(arazzo_result, output_file)
        return

    spec = parse_openapi_json(content)
    endpoints = _build_operations_docs(spec.paths, no_imports, no_wrapping)
    webhooks = _build_operations_docs(spec.webhooks, no_imports, no_wrapping)

    result: dict[str, Any] = {
        "endpoints": endpoints,
        "webhooks": webhooks,
        "workflows": {},
    }
    _write_or_print_docs(result, output_file)
