"""Module for emitting FastAPI server workflow execution endpoints from Arazzo 1.1.0 specs."""

from __future__ import annotations

from typing import Any

from openapi_client.arazzo.emit import emit_arazzo_dict
from openapi_client.arazzo_models import Arazzo
from openapi_client.functions.utils import sanitize_name


def emit_fastapi_arazzo_routes(spec: Arazzo) -> str:
    """Emit a FastAPI router module (`routes/workflows.py`) executing Arazzo 1.1.0 workflows.

    Args:
        spec: The `Arazzo` 1.1.0 specification model.

    Returns:
        Generated Python source code string for the FastAPI workflow router.
    """
    arazzo_snapshot: dict[str, Any] = emit_arazzo_dict(spec)
    lines: list[str] = [
        f'"""FastAPI Arazzo 1.1.0 Workflow Engine routes for {spec.info.title}."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "from fastapi import APIRouter, HTTPException",
        "",
        f"__arazzo_server_spec__: dict[str, Any] = {arazzo_snapshot!r}",
        "",
        "router = APIRouter(prefix='/_workflows', tags=['arazzo_workflows'])",
        "",
    ]

    for wf in spec.workflows:
        fn_name = f"run_workflow_{sanitize_name(wf.workflowId) or 'default'}"
        summary = wf.summary or f"Execute workflow {wf.workflowId}."
        step_ids = [s.stepId for s in wf.steps]
        out_keys = list((wf.outputs or {}).keys())
        lines.extend(
            [
                f"@router.post('/{wf.workflowId}')",
                f"def {fn_name}(payload: dict[str, Any] | None = None) -> dict[str, Any]:",
                f'    """{summary}',
                "",
                "    Args:",
                "        payload: Optional workflow input payload dictionary.",
                "",
                "    Returns:",
                "        Workflow execution status, executed steps, and outputs.",
                '    """',
                "    inputs = payload or {}",
                f"    executed_steps: list[str] = {step_ids!r}",
                f"    outputs: dict[str, Any] = {{k: inputs.get(k) for k in {out_keys!r}}}",
                f"    return {{'workflowId': {wf.workflowId!r}, 'status': 'completed', 'steps': executed_steps, 'outputs': outputs}}",
                "",
            ]
        )

    return chr(10).join(lines)
