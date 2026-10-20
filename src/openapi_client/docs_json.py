"""OpenAPI and Arazzo documentation JSON snippet generator."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from openapi_client.arazzo.parse import parse_arazzo_json
from openapi_client.functions.utils import sanitize_name
from openapi_client.openapi.parse import parse_openapi_json


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
        output_file: Optional file path to write JSON output; prints to stdout if None.
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
        workflows_docs: dict[str, str] = {}
        for wf in arazzo_spec.workflows:
            wf_fn = sanitize_name(wf.workflowId) or "run_workflow"
            wf_lines: list[str] = []
            if not no_imports:
                wf_lines.extend(["from workflows import Workflows", ""])
            if not no_wrapping:
                wf_lines.extend(["def main():", "    runner = Workflows()"])
            indent = "    " if not no_wrapping else ""
            wf_lines.append(f"{indent}result = runner.{wf_fn}()")
            wf_lines.append(f"{indent}print(result)")
            if not no_wrapping:
                wf_lines.extend(["", 'if __name__ == "__main__":', "    main()"])
            workflows_docs[wf.workflowId] = nl.join(wf_lines)
        arazzo_result = {"workflows": workflows_docs}
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(arazzo_result, f, indent=2)
        else:
            print(json.dumps(arazzo_result, indent=2))
        return

    spec = parse_openapi_json(content)

    endpoints: dict[str, dict[str, str]] = {}

    if spec.paths:
        for path, path_item in spec.paths.items():
            path_map: dict[str, str] = {}
            for method in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "options",
                "head",
                "trace",
            ]:
                operation = getattr(path_item, method, None)
                if operation:
                    raw_op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    op_id = sanitize_name(raw_op_id)

                    lines: list[str] = []

                    if not no_imports:
                        lines.append("import json")
                        lines.append("from generated_client import Client")
                        lines.append("")

                    if not no_wrapping:
                        lines.append("def main():")
                        lines.append(
                            '    client = Client(base_url="https://api.example.com")'
                        )

                    indent = "    " if not no_wrapping else ""

                    args: list[str] = []
                    if operation.parameters:
                        for param in operation.parameters:
                            if hasattr(param, "name"):
                                p_name = param.name.replace("-", "_")
                                lines.append(f"{indent}{p_name} = 'example'")
                                args.append(f"{p_name}={p_name}")

                    if getattr(operation, "requestBody", None):
                        lines.append(f"{indent}body = {{}}")
                        args.append("body=body")

                    args_str = ", ".join(args)
                    lines.append(f"{indent}response = client.{op_id}({args_str})")
                    lines.append(f"{indent}print(response)")

                    if not no_wrapping:
                        lines.append("")
                        lines.append('if __name__ == "__main__":')
                        lines.append("    main()")

                    path_map[method.lower()] = nl.join(lines)

            if path_map:
                endpoints[path] = path_map

    result = {"endpoints": endpoints}

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))
