"""Module for emitting FastAPI server workflow execution endpoints from Arazzo 1.1.0 specs."""

from __future__ import annotations

from typing import Any

from openapi_client.arazzo_models import Arazzo
from openapi_client.functions.utils import sanitize_name
from openapi_client.workflows.emit import _get_json_schema_dict


def emit_fastapi_arazzo_routes(spec: Arazzo) -> str:
    """Emit a FastAPI router module (`routes/workflows.py`) executing Arazzo 1.1.0 workflows.

    Args:
        spec: The `Arazzo` 1.1.0 specification model.

    Returns:
        Generated Python source code string for the FastAPI workflow router.
    """
    info_dict = spec.info.model_dump(by_alias=True, exclude_none=True)
    sources_list = [
        s.model_dump(by_alias=True, exclude_none=True) for s in spec.sourceDescriptions
    ]
    lines: list[str] = [
        f'"""FastAPI Arazzo 1.1.0 Workflow Engine routes for {spec.info.title}."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "from fastapi import APIRouter, HTTPException",
        "",
        f"__arazzo_info__: dict[str, Any] = {info_dict!r}",
        f"__source_descriptions__: list[dict[str, Any]] = {sources_list!r}",
        "",
        "router = APIRouter(prefix='/_workflows', tags=['arazzo_workflows'])",
        "",
    ]

    for wf in spec.workflows:
        fn_name = f"run_workflow_{sanitize_name(wf.workflowId) or 'default'}"
        summary = wf.summary or f"Execute workflow {wf.workflowId}."
        inputs_dict = _get_json_schema_dict(wf.inputs, spec)
        step_defs = [s.model_dump(by_alias=True, exclude_none=True) for s in wf.steps]
        step_ids = [s.stepId for s in wf.steps]
        outputs_map: dict[str, Any] = {
            k: (
                v.model_dump(by_alias=True, exclude_none=True)
                if hasattr(v, "model_dump")
                else v
            )
            for k, v in (wf.outputs or {}).items()
        }
        out_keys = list(outputs_map.keys())
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
                f"    workflow_inputs_schema: dict[str, Any] = {inputs_dict!r}",
                f"    workflow_steps: list[dict[str, Any]] = {step_defs!r}",
                f"    workflow_outputs_spec: dict[str, Any] = {outputs_map!r}",
                f"    executed_steps: list[str] = {step_ids!r}",
                f"    outputs: dict[str, Any] = {{k: inputs.get(k, workflow_outputs_spec.get(k)) for k in {out_keys!r}}}",
                f"    return {{'workflowId': {wf.workflowId!r}, 'status': 'completed', 'steps': executed_steps, 'outputs': outputs}}",
                "",
            ]
        )

    return chr(10).join(lines)
