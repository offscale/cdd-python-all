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
        The evaluated Python literal.
    """
    return ast.literal_eval(code_str)


class ASTWorkflowTestExtractor(cst.CSTVisitor):
    """LibCST Visitor to extract Arazzo workflows from pytest test functions."""

    def __init__(self) -> None:
        """Initialize the `ASTWorkflowTestExtractor`."""
        self.info_dict: dict[str, Any] | None = None
        self.source_descriptions: list[dict[str, Any]] | None = None
        self.workflows: list[WorkflowObject] = []

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Extract module-level `__arazzo_info__` and `__source_descriptions__` metadata.

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
        raw_summary, description = parse_docstring(node)
        summary = (
            None if raw_summary == f"Test Arazzo workflow {wf_id}." else raw_summary
        )
        steps: list[StepObject] = []
        var_to_step: dict[str, str] = {}
        inputs_schema: dict[str, Any] | None = None
        outputs_map: dict[str, str | SelectorObject] | None = None

        for stmt in node.body.body:
            stmt_code = cst.Module([]).code_for_node(stmt).strip()

            item = stmt.body[0] if isinstance(stmt, cst.SimpleStatementLine) else None
            if (
                isinstance(item, cst.AnnAssign)
                and isinstance(item.target, cst.Name)
                and item.value is not None
            ):
                parsed_val = _safe_eval(
                    cst.Module([]).code_for_node(item.value).strip()
                )
                if item.target.value == "workflow_inputs_schema" and isinstance(
                    parsed_val, dict
                ):
                    inputs_schema = parsed_val if parsed_val else None
                    continue
                if item.target.value == "expected_outputs" and isinstance(
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
                    continue

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
                inputs=inputs_schema,
                steps=steps,
                outputs=outputs_map,
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

    info_obj = (
        ArazzoInfo(**visitor.info_dict)
        if visitor.info_dict
        else ArazzoInfo(title="Extracted Test Workflows", version="1.0.0")
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


def extract_arazzo_from_test_code(code: str) -> Arazzo:
    """Extract an `Arazzo` specification from pytest source code.

    Args:
        code: Python test source code string.

    Returns:
        The extracted `Arazzo` specification model.
    """
    return extract_arazzo_from_test_ast(cst.parse_module(code))
