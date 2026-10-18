"""Module for extracting an Arazzo 1.1.0 specification from multi-step pytest workflow tests."""

from __future__ import annotations

import ast
import re
from typing import Any

import libcst as cst

from openapi_client.arazzo_models import (
    Arazzo,
    ArazzoInfo,
    ArazzoParameter,
    CriterionObject,
    SourceDescription,
    StepObject,
    WorkflowObject,
)
from openapi_client.docstrings.parse import parse_docstring


class ASTWorkflowTestExtractor(cst.CSTVisitor):
    """LibCST Visitor to extract Arazzo workflows from pytest test functions."""

    def __init__(self) -> None:
        """Initialize the `ASTWorkflowTestExtractor`."""
        self.snapshot_spec: dict[str, Any] | None = None
        self.workflows: list[WorkflowObject] = []

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Extract `__arazzo_test_spec__` metadata if present.

        Args:
            node: The `libcst.AnnAssign` node being visited.
        """
        code = (
            cst.Module([]).code_for_node(node.value).strip() if node.value else "None"
        )
        val = ast.literal_eval(code)
        self.snapshot_spec = val if isinstance(val, dict) else None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Extract a `WorkflowObject` from `test_workflow_*` or multi-step `test_*` functions.

        Args:
            node: The `libcst.FunctionDef` node being visited.
        """
        fn_name = node.name.value
        if not fn_name.startswith("test_"):
            return

        wf_id = (
            fn_name[len("test_workflow_") :]
            if fn_name.startswith("test_workflow_")
            else fn_name[len("test_") :]
        )
        summary, description = parse_docstring(node)
        steps: list[StepObject] = []
        var_to_step: dict[str, str] = {}

        for stmt in node.body.body:
            stmt_code = cst.Module([]).code_for_node(stmt).strip()

            m_target = re.match(
                r"""^step_([A-Za-z0-9_]+)_target\s*=\s*(['"])([^'"]+)\2$""", stmt_code
            )
            if m_target:
                sid = m_target.group(1)
                target = m_target.group(3)
                steps.append(StepObject(stepId=sid, operationId=target))
                continue

            m_call = re.match(
                r"^([A-Za-z0-9_]+)\s*=\s*client\.([A-Za-z0-9_]+)\((.*)\)$", stmt_code
            )
            if m_call:
                resp_var, op_name, args_raw = m_call.groups()
                step_id = f"step_{len(steps) + 1}"
                var_to_step[resp_var] = step_id
                params: list[ArazzoParameter] = []
                if args_raw.strip():
                    for prev_var, prev_sid in var_to_step.items():
                        if prev_var != resp_var and prev_var in args_raw:
                            params.append(
                                ArazzoParameter(
                                    name="id",
                                    in_="path",
                                    value=f"$steps.{prev_sid}.outputs.id",
                                )
                            )
                steps.append(
                    StepObject(
                        stepId=step_id,
                        operationId=op_name,
                        parameters=params if params else None,
                    )
                )
                continue

            m_status = re.match(
                r"^assert\s+([A-Za-z0-9_]+)\.status(?:_code)?\s*==\s*(\d+)$",
                stmt_code,
            )
            if m_status and steps:
                code_num = m_status.group(2)
                last_step = steps[-1]
                last_step.successCriteria = (last_step.successCriteria or []) + [
                    CriterionObject(condition=f"$statusCode == {code_num}")
                ]

        self.workflows.append(
            WorkflowObject(
                workflowId=wf_id,
                summary=summary,
                description=description,
                steps=steps,
            )
        )


def extract_arazzo_from_test_ast(module: cst.Module) -> Arazzo:
    """Extract an `Arazzo` specification from a parsed pytest LibCST `Module`.

    Args:
        module: The parsed LibCST `Module` node.

    Returns:
        The extracted `Arazzo` specification model.
    """
    visitor = ASTWorkflowTestExtractor()
    module.visit(visitor)

    if visitor.snapshot_spec is not None:
        return Arazzo(**visitor.snapshot_spec)

    return Arazzo(
        arazzo="1.1.0",
        info=ArazzoInfo(title="Extracted Test Workflows", version="1.0.0"),
        sourceDescriptions=[
            SourceDescription(name="default", url="openapi.json", type="openapi")
        ],
        workflows=visitor.workflows,
    )


def extract_arazzo_from_test_code(code: str) -> Arazzo:
    """Extract an `Arazzo` specification from pytest source code.

    Args:
        code: Python test source code string.

    Returns:
        The extracted `Arazzo` specification model.
    """
    return extract_arazzo_from_test_ast(cst.parse_module(code))
