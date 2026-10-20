"""Module for extracting an Arazzo 1.1.0 specification from FastAPI workflow route ASTs."""

from __future__ import annotations

import ast
from typing import Any

import libcst as cst

from openapi_client.arazzo_models import (
    Arazzo,
    ArazzoInfo,
    SelectorObject,
    SourceDescription,
    StepObject,
    WorkflowObject,
)
from openapi_client.docstrings.parse import parse_docstring


def _safe_eval(code_str: str) -> Any:
    """Safely evaluate a Python literal expression string via `ast.literal_eval`.

    Args:
        code_str: Source code string of the expression.

    Returns:
        The evaluated Python literal, or `None` if evaluation fails.
    """
    try:
        return ast.literal_eval(code_str)
    except (ValueError, SyntaxError):
        return None


class FastAPIArazzoExtractor(cst.CSTVisitor):
    """LibCST Visitor to extract Arazzo workflows from a FastAPI workflow router module."""

    def __init__(self) -> None:
        """Initialize the `FastAPIArazzoExtractor`."""
        self.info_dict: dict[str, Any] | None = None
        self.source_descriptions: list[dict[str, Any]] | None = None
        self.workflows: list[WorkflowObject] = []

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Extract `__arazzo_info__` and `__source_descriptions__` metadata if present.

        Args:
            node: The `libcst.AnnAssign` node being visited.
        """
        t_name = node.target.value if isinstance(node.target, cst.Name) else ""
        attr = {
            "__arazzo_info__": "info_dict",
            "__source_descriptions__": "source_descriptions",
        }.get(t_name)
        if attr and node.value is not None:
            setattr(
                self,
                attr,
                _safe_eval(cst.Module([]).code_for_node(node.value).strip()),
            )

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Extract workflow definitions from `@router.post('/<workflowId>')` route functions.

        Args:
            node: The `libcst.FunctionDef` node being visited.
        """
        if not node.decorators:
            return
        dec = node.decorators[0].decorator
        arg_code = (
            cst.Module([]).code_for_node(dec.args[0].value).strip()
            if isinstance(dec, cst.Call) and dec.args
            else "'default'"
        )
        wf_id = str(_safe_eval(arg_code) or "default").strip("/").split("/")[-1]

        raw_summary, _ = parse_docstring(node)
        summary = None if raw_summary == f"Execute workflow {wf_id}." else raw_summary
        step_ids: list[str] = ["step_1"]
        step_objects: list[StepObject] | None = None
        inputs_schema: dict[str, Any] | None = None
        outputs_map: dict[str, str | SelectorObject] | None = None

        for stmt in node.body.body:
            item = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else None
            if (
                isinstance(item, cst.AnnAssign)
                and isinstance(item.target, cst.Name)
                and item.value is not None
            ):
                parsed_val = _safe_eval(
                    cst.Module([]).code_for_node(item.value).strip()
                )
                if item.target.value == "executed_steps" and isinstance(
                    parsed_val, list
                ):
                    step_ids = [str(s) for s in parsed_val]
                elif item.target.value == "workflow_steps" and isinstance(
                    parsed_val, list
                ):
                    step_objects = [StepObject(**s) for s in parsed_val]
                elif item.target.value == "workflow_inputs_schema" and isinstance(
                    parsed_val, dict
                ):
                    inputs_schema = parsed_val if parsed_val else None
                elif item.target.value == "workflow_outputs_spec" and isinstance(
                    parsed_val, dict
                ):
                    outputs_map = (
                        {
                            k: (SelectorObject(**v) if isinstance(v, dict) else str(v))
                            for k, v in parsed_val.items()
                        }
                        if parsed_val
                        else None
                    )

        steps = step_objects or [
            StepObject(stepId=sid, operationId=sid) for sid in step_ids
        ]
        self.workflows.append(
            WorkflowObject(
                workflowId=wf_id,
                summary=summary,
                inputs=inputs_schema,
                steps=steps,
                outputs=outputs_map,
            )
        )


def extract_arazzo_from_fastapi_ast(module: cst.Module) -> Arazzo:
    """Extract an `Arazzo` specification from a parsed FastAPI LibCST `Module`.

    Args:
        module: The parsed LibCST `Module` node.

    Returns:
        The extracted `Arazzo` specification model.
    """
    visitor = FastAPIArazzoExtractor()
    module.visit(visitor)

    info_obj = (
        ArazzoInfo(**visitor.info_dict)
        if visitor.info_dict
        else ArazzoInfo(title="FastAPI Server Workflows", version="1.0.0")
    )
    sources = (
        [SourceDescription(**sd) for sd in visitor.source_descriptions]
        if visitor.source_descriptions
        else [SourceDescription(name="default", url="openapi.json", type="openapi")]
    )

    return Arazzo(
        arazzo="1.1.0",
        info=info_obj,
        sourceDescriptions=sources,
        workflows=visitor.workflows,
    )


def extract_arazzo_from_fastapi_code(code: str) -> Arazzo:
    """Extract an `Arazzo` specification from FastAPI workflow route source code.

    Args:
        code: Python source code string.

    Returns:
        The extracted `Arazzo` specification model.
    """
    return extract_arazzo_from_fastapi_ast(cst.parse_module(code))
