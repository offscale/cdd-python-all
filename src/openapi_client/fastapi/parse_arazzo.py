"""Module for extracting an Arazzo 1.1.0 specification from FastAPI workflow route ASTs."""

from __future__ import annotations

import ast
from typing import Any

import libcst as cst

from openapi_client.arazzo_models import (
    Arazzo,
    ArazzoInfo,
    SourceDescription,
    StepObject,
    WorkflowObject,
)
from openapi_client.docstrings.parse import parse_docstring


class FastAPIArazzoExtractor(cst.CSTVisitor):
    """LibCST Visitor to extract Arazzo workflows from a FastAPI workflow router module."""

    def __init__(self) -> None:
        """Initialize the `FastAPIArazzoExtractor`."""
        self.snapshot_spec: dict[str, Any] | None = None
        self.workflows: list[WorkflowObject] = []

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Extract `__arazzo_server_spec__` metadata if present.

        Args:
            node: The `libcst.AnnAssign` node being visited.
        """
        if (
            isinstance(node.target, cst.Name)
            and node.target.value == "__arazzo_server_spec__"
        ):
            code = (
                cst.Module([]).code_for_node(node.value).strip()
                if node.value
                else "None"
            )
            val = ast.literal_eval(code)
            self.snapshot_spec = val if isinstance(val, dict) else None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Extract workflow definitions from `@router.post('/<workflowId>')` route functions.

        Args:
            node: The `libcst.FunctionDef` node being visited.
        """
        dec = node.decorators[0].decorator
        arg_code = (
            cst.Module([]).code_for_node(dec.args[0].value).strip()
            if isinstance(dec, cst.Call) and dec.args
            else "'default'"
        )
        wf_id = str(ast.literal_eval(arg_code)).strip("/").split("/")[-1]

        summary, _ = parse_docstring(node)
        step_ids: list[str] = ["step_1"]
        for stmt in node.body.body:
            item = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else None
            if (
                isinstance(item, cst.AnnAssign)
                and isinstance(item.target, cst.Name)
                and item.target.value == "executed_steps"
                and item.value is not None
            ):
                s_code = cst.Module([]).code_for_node(item.value).strip()
                parsed_steps = ast.literal_eval(s_code)
                step_ids = [str(s) for s in parsed_steps]

        self.workflows.append(
            WorkflowObject(
                workflowId=wf_id,
                summary=summary,
                steps=[StepObject(stepId=sid, operationId=sid) for sid in step_ids],
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

    if visitor.snapshot_spec is not None:
        return Arazzo(**visitor.snapshot_spec)

    return Arazzo(
        arazzo="1.1.0",
        info=ArazzoInfo(title="FastAPI Server Workflows", version="1.0.0"),
        sourceDescriptions=[
            SourceDescription(name="default", url="openapi.json", type="openapi")
        ],
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
