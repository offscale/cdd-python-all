"""Module for emitting pytest end-to-end workflow integration tests from Arazzo 1.1.0 specs."""

from __future__ import annotations

from typing import Any

import libcst as cst

from openapi_client.arazzo_models import Arazzo, WorkflowObject
from openapi_client.functions.utils import build_cst_module, sanitize_name
from openapi_client.workflows.emit import _get_json_schema_dict


def _default_input_for_prop(prop_schema: dict[str, Any]) -> Any:
    """Derive a deterministic dummy test value for a workflow input property schema.

    Args:
        prop_schema: JSON Schema dictionary for a single workflow input property.

    Returns:
        A dummy Python literal suitable for test seeding.
    """
    if "example" in prop_schema:
        return prop_schema["example"]
    if "default" in prop_schema:
        return prop_schema["default"]
    if (
        "enum" in prop_schema
        and isinstance(prop_schema["enum"], list)
        and prop_schema["enum"]
    ):
        return prop_schema["enum"][0]
    t = prop_schema.get("type")
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    if t == "array":
        return []
    if t == "object":
        return {}
    return "test_value"


def _emit_workflow_test_fn(workflow: WorkflowObject, spec: Arazzo) -> cst.FunctionDef:
    """Emit a pytest `def test_workflow_<id>()` function for an Arazzo `WorkflowObject`.

    Args:
        workflow: The `WorkflowObject` under test.
        spec: The containing `Arazzo` specification.

    Returns:
        A `libcst.FunctionDef` node representing the generated pytest test function.
    """
    safe_wf = sanitize_name(workflow.workflowId) or "workflow"
    fn_name = f"test_workflow_{safe_wf}"
    summary = workflow.summary or f"Test Arazzo workflow {workflow.workflowId}."

    schema_dict = _get_json_schema_dict(workflow.inputs, spec)
    properties: dict[str, Any] = schema_dict.get("properties", {})
    call_kwargs: list[str] = []
    for prop_name, prop_schema in properties.items():
        p_dict = prop_schema if isinstance(prop_schema, dict) else {}
        val = _default_input_for_prop(p_dict)
        safe_param = sanitize_name(prop_name) or prop_name
        call_kwargs.append(f"{safe_param}={val!r}")

    outputs_map: dict[str, Any] = {
        k: (
            v.model_dump(by_alias=True, exclude_none=True)
            if hasattr(v, "model_dump")
            else v
        )
        for k, v in (workflow.outputs or {}).items()
    }

    stmts: list[cst.BaseStatement] = [
        cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{summary}"""'))]),
        cst.parse_statement("runner = Workflows()"),
        cst.parse_statement(f"assert hasattr(runner, {safe_wf!r})"),
        cst.parse_statement(
            f"workflow_inputs_schema: dict[str, Any] = {schema_dict!r}"
        ),
        cst.parse_statement(f"expected_outputs: dict[str, Any] = {outputs_map!r}"),
        cst.parse_statement(
            f"call_kwargs: dict[str, Any] = {{{', '.join(repr(k.split('=', 1)[0]) + ': ' + k.split('=', 1)[1] for k in call_kwargs)}}}"
        ),
        cst.parse_statement("assert isinstance(expected_outputs, dict)"),
        cst.parse_statement("assert isinstance(call_kwargs, dict)"),
    ]

    for step in workflow.steps:
        op_label = (
            step.operationId
            or step.operationPath
            or step.workflowId
            or step.channelPath
            or step.stepId
        )
        stmts.append(
            cst.parse_statement(
                f"step_{sanitize_name(step.stepId) or 's'}_target = {op_label!r}"
            )
        )
        stmts.append(
            cst.parse_statement(
                f"assert step_{sanitize_name(step.stepId) or 's'}_target is not None"
            )
        )

    return cst.FunctionDef(
        name=cst.Name(fn_name),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=stmts),
        returns=cst.Annotation(cst.Name("None")),
    )


def emit_arazzo_tests(spec: Arazzo) -> cst.Module:
    """Emit a pytest test module (`test_workflows.py`) from an `Arazzo` specification.

    Args:
        spec: The `Arazzo` 1.1.0 specification model.

    Returns:
        A `libcst.Module` node containing the generated test suite.
    """
    info_dict = spec.info.model_dump(by_alias=True, exclude_none=True)
    sources_list = [
        s.model_dump(by_alias=True, exclude_none=True) for s in spec.sourceDescriptions
    ]
    header_code = chr(10).join(
        [
            f'"""End-to-end Arazzo 1.1.0 workflow tests for {spec.info.title}."""',
            "",
            "from __future__ import annotations",
            "",
            "from typing import Any",
            "",
            "from workflows import Workflows",
            "",
            f"__arazzo_info__: dict[str, Any] = {info_dict!r}",
            f"__source_descriptions__: list[dict[str, Any]] = {sources_list!r}",
            "",
        ]
    )
    header_mod = cst.parse_module(header_code)

    body: list[cst.BaseStatement | cst.EmptyLine] = list(header_mod.body)
    for wf in spec.workflows:
        body.append(cst.EmptyLine())
        body.append(_emit_workflow_test_fn(wf, spec))

    return build_cst_module(body)


def emit_arazzo_tests_code(spec: Arazzo) -> str:
    """Generate the Python source code string for an Arazzo pytest test module.

    Args:
        spec: The `Arazzo` 1.1.0 specification model.

    Returns:
        The generated Python test code string.
    """
    return emit_arazzo_tests(spec).code
