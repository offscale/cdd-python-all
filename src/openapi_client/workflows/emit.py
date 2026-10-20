"""Module for emitting Python Client SDK workflow orchestrators from Arazzo 1.1.0 specifications."""

from __future__ import annotations

from typing import Any

import libcst as cst

from openapi_client.arazzo.expressions import compile_expression_to_cst
from openapi_client.arazzo.parse import (
    resolve_operation_path,
    resolve_reusable_failure_action,
    resolve_reusable_parameter,
    resolve_reusable_success_action,
)
from openapi_client.arazzo_models import (
    Arazzo,
    SelectorObject,
    StepObject,
    WorkflowObject,
)
from openapi_client.functions.utils import (
    build_cst_module,
    get_annotation_for_schema,
    sanitize_name,
)
from openapi_client.models import OpenAPI, Reference, Schema


def _get_json_schema_dict(
    inputs: Schema | Reference | dict[str, Any] | None, spec: Arazzo
) -> dict[str, Any]:
    """Convert an Arazzo `inputs` schema or `$components.inputs.*` reference to a raw dict.

    Args:
        inputs: Workflow inputs schema (`Schema`, `Reference`, `dict`, or `None`).
        spec: The containing `Arazzo` specification.

    Returns:
        A dictionary representation of the JSON Schema object.
    """
    if inputs is None:
        return {}
    raw_dict: dict[str, Any] = (
        inputs
        if isinstance(inputs, dict)
        else inputs.model_dump(by_alias=True, exclude_none=True)
    )
    ref = raw_dict.get("$ref")
    if (
        isinstance(ref, str)
        and ref.startswith("$components.inputs.")
        and spec.components
        and spec.components.inputs
        and ref[len("$components.inputs.") :] in spec.components.inputs
    ):
        return _get_json_schema_dict(
            spec.components.inputs[ref[len("$components.inputs.") :]], spec
        )
    return raw_dict


def _json_type_to_python_type(prop_schema: dict[str, Any]) -> str:
    """Map a JSON Schema property dictionary to a Python type annotation string.

    Args:
        prop_schema: Property schema dictionary.

    Returns:
        Python type annotation string (`str`, `int`, `float`, `bool`, `list[Any]`, `dict[str, Any]`, or `Any`).
    """
    return get_annotation_for_schema(prop_schema)


def _emit_step_statements(
    step: StepObject,
    workflow: WorkflowObject,
    spec: Arazzo,
    sources: dict[str, OpenAPI | Arazzo | dict[str, Any]],
) -> list[cst.BaseStatement]:
    """Emit LibCST statements for a single Arazzo `StepObject`.

    Args:
        step: The `StepObject` to compile.
        workflow: The parent `WorkflowObject`.
        spec: The root `Arazzo` specification.
        sources: Resolved `sourceDescriptions` dictionary.

    Returns:
        A list of `libcst.BaseStatement` nodes executing the step.
    """
    stmts: list[cst.BaseStatement] = []

    if step.dependsOn:
        for dep_step in step.dependsOn:
            stmts.append(
                cst.parse_statement(
                    f"assert {dep_step!r} in steps_context, f'Prerequisite step {dep_step} not executed'"
                )
            )

    resolved_params = [
        resolve_reusable_parameter(p, spec)
        for p in (workflow.parameters or []) + (step.parameters or [])
    ]

    call_kwargs: list[str] = []
    for p in resolved_params:
        param_ident = sanitize_name(p.name) or "param"
        val_cst = compile_expression_to_cst(p.value)
        val_code = cst.Module([]).code_for_node(val_cst)
        call_kwargs.append(f"{param_ident}={val_code}")

    if step.requestBody is not None:
        base_payload = step.requestBody.payload
        if step.requestBody.replacements:
            reps_repr = [
                r.model_dump(by_alias=True, exclude_none=True)
                for r in step.requestBody.replacements
            ]
            stmts.append(
                cst.parse_statement(
                    f"step_body = apply_payload_replacements({base_payload!r}, [PayloadReplacement(**r) for r in {reps_repr!r}], context)"
                )
            )
        else:
            val_cst = compile_expression_to_cst(base_payload)
            val_code = cst.Module([]).code_for_node(val_cst)
            stmts.append(cst.parse_statement(f"step_body = {val_code}"))
        if step.requestBody.contentType is not None:
            call_kwargs.append(f"content_type={step.requestBody.contentType!r}")
        call_kwargs.append("body=step_body")

    if step.timeout is not None:
        call_kwargs.append(f"timeout={step.timeout!r}")

    kwargs_str = ", ".join(call_kwargs)

    call_expr_code = f"self.client.call_step({step.stepId!r})"
    if step.operationId:
        if "." in step.operationId and step.operationId.startswith(
            "$sourceDescriptions."
        ):
            parts = step.operationId[len("$sourceDescriptions.") :].split(".", 1)
            src_name: str | None = parts[0]
            op_name = (
                sanitize_name(parts[1])
                if len(parts) > 1
                else sanitize_name(step.stepId)
            )
            call_expr_code = f"self.clients[{src_name!r}].{op_name}({kwargs_str})"
        else:
            op_name = sanitize_name(step.operationId)
            call_expr_code = f"self.client.{op_name}({kwargs_str})"
    elif step.operationPath:
        src_name, method, path, resolved_op = resolve_operation_path(
            step.operationPath, sources
        )
        op_path_kw = f"operation_path={step.operationPath!r}"
        combined_kw = f"{kwargs_str}, {op_path_kw}" if kwargs_str else op_path_kw
        if resolved_op and resolved_op.operationId:
            op_name = sanitize_name(resolved_op.operationId)
            call_expr_code = (
                f"self.clients[{src_name!r}].{op_name}({combined_kw})"
                if src_name and len(sources) > 1
                else f"self.client.{op_name}({combined_kw})"
            )
        else:
            verb = (method or "get").upper()
            route = path or step.operationPath
            call_expr_code = f"self.client.request({verb!r}, {route!r}, {combined_kw})"
    elif step.workflowId:
        wf_method = sanitize_name(step.workflowId)
        call_expr_code = f"self.{wf_method}({kwargs_str})"
    elif step.channelPath:
        act = step.action or "send"
        corr = step.correlationId
        extra = f", action={act!r}, correlation_id={corr!r}" + (
            f", {kwargs_str}" if kwargs_str else ""
        )
        call_expr_code = f"self.client.channel({step.channelPath!r}{extra})"

    failure_actions = [
        resolve_reusable_failure_action(fa, spec)
        for fa in (step.onFailure or workflow.failureActions or [])
    ]
    retry_action = next((fa for fa in failure_actions if fa.type == "retry"), None)

    if retry_action is not None:
        limit = retry_action.retryLimit if retry_action.retryLimit is not None else 1
        delay = retry_action.retryAfter if retry_action.retryAfter is not None else 0
        stmts.append(cst.parse_statement(f"_retries_left = {limit!r}"))
        while_code = chr(10).join(
            [
                "while True:",
                f"    response = {call_expr_code}",
                "    if getattr(response, 'status', 200) < 400 or _retries_left <= 0:",
                "        break",
                "    _retries_left -= 1",
                f"    if {delay!r} > 0:",
                f"        time.sleep({delay!r})",
            ]
        )
        stmts.append(cst.parse_statement(while_code))
    else:
        stmts.append(cst.parse_statement(f"response = {call_expr_code}"))

    stmts.append(
        cst.parse_statement(
            "context['statusCode'] = getattr(response, 'status', getattr(response, 'status_code', 200))"
        )
    )
    stmts.append(
        cst.parse_statement(
            "context['response'] = {'body': getattr(response, 'data', response), 'header': getattr(response, 'headers', {})}"
        )
    )

    if step.successCriteria:
        for crit in step.successCriteria:
            crit_dict = crit.model_dump(by_alias=True, exclude_none=True)
            stmts.append(
                cst.parse_statement(
                    f"assert evaluate_criterion(CriterionObject(**{crit_dict!r}), context), f'Step {step.stepId} failed criterion: {crit.condition}'"
                )
            )

    success_actions = [
        resolve_reusable_success_action(sa, spec)
        for sa in (step.onSuccess or workflow.successActions or [])
    ]
    for sa in success_actions:
        if sa.type == "goto" and sa.workflowId:
            target_wf = sanitize_name(sa.workflowId)
            goto_code = chr(10).join(
                [
                    "if getattr(response, 'status', 200) < 400:",
                    f"    return self.{target_wf}()",
                ]
            )
            stmts.append(cst.parse_statement(goto_code))
        else:
            c_dict = (
                sa.criteria[0].model_dump(by_alias=True, exclude_none=True)
                if sa.criteria
                else {"condition": "$statusCode == 200"}
            )
            end_code = chr(10).join(
                [
                    f"if evaluate_criterion(CriterionObject(**{c_dict!r}), context):",
                    "    return workflow_outputs",
                ]
            )
            stmts.append(cst.parse_statement(end_code))

    step_outputs_entries: list[str] = []
    if step.outputs:
        for out_key, out_expr in step.outputs.items():
            if isinstance(out_expr, SelectorObject):
                sel_dict = out_expr.model_dump(by_alias=True, exclude_none=True)
                step_outputs_entries.append(
                    f"{out_key!r}: evaluate_selector(SelectorObject(**{sel_dict!r}), context)"
                )
            else:
                compiled_out = compile_expression_to_cst(out_expr)
                out_code = cst.Module([]).code_for_node(compiled_out)
                step_outputs_entries.append(f"{out_key!r}: {out_code}")

    outputs_dict_str = "{" + ", ".join(step_outputs_entries) + "}"
    step_meta: dict[str, Any] = {}
    if step.parameters:
        step_meta["parameters"] = [
            p.model_dump(by_alias=True, exclude_none=True) for p in step.parameters
        ]
    if step.onSuccess:
        step_meta["onSuccess"] = [
            s.model_dump(by_alias=True, exclude_none=True) for s in step.onSuccess
        ]
    if step.onFailure:
        step_meta["onFailure"] = [
            f.model_dump(by_alias=True, exclude_none=True) for f in step.onFailure
        ]
    meta_suffix = f", 'meta': {step_meta!r}" if step_meta else ""
    stmts.append(
        cst.parse_statement(
            f"steps_context[{step.stepId!r}] = {{'outputs': {outputs_dict_str}, 'response': response{meta_suffix}}}"
        )
    )

    return stmts


def emit_workflow_method(
    workflow: WorkflowObject,
    spec: Arazzo,
    sources: dict[str, OpenAPI | Arazzo | dict[str, Any]],
) -> cst.FunctionDef:
    """Emit a strongly typed Python method on the `Workflows` class for a `WorkflowObject`.

    Args:
        workflow: The `WorkflowObject` to compile into a method.
        spec: The containing `Arazzo` specification.
        sources: Resolved `sourceDescriptions` dictionary.

    Returns:
        A `libcst.FunctionDef` node representing the workflow method.
    """
    method_name = sanitize_name(workflow.workflowId) or "run_workflow"
    schema_dict = _get_json_schema_dict(workflow.inputs, spec)
    properties: dict[str, Any] = schema_dict.get("properties", {})
    required_fields: set[str] = set(schema_dict.get("required", []))

    req_params: list[cst.Param] = [cst.Param(name=cst.Name("self"))]
    opt_params: list[cst.Param] = []
    input_dict_items: list[str] = []

    for prop_name, prop_schema in properties.items():
        safe_param = sanitize_name(prop_name) or prop_name
        py_type = _json_type_to_python_type(
            prop_schema if isinstance(prop_schema, dict) else {}
        )
        input_dict_items.append(f"{prop_name!r}: {safe_param}")
        if prop_name in required_fields:
            req_params.append(
                cst.Param(
                    name=cst.Name(safe_param),
                    annotation=cst.Annotation(cst.parse_expression(py_type)),
                )
            )
        else:
            default_val = (
                prop_schema.get("default") if isinstance(prop_schema, dict) else None
            )
            opt_params.append(
                cst.Param(
                    name=cst.Name(safe_param),
                    annotation=cst.Annotation(
                        cst.parse_expression(f"{py_type} | None")
                    ),
                    default=cst.parse_expression(repr(default_val)),
                )
            )

    all_params = req_params + opt_params
    body_stmts: list[cst.BaseStatement] = []

    summary = workflow.summary or f"Execute workflow {workflow.workflowId}."
    desc = workflow.description or ""
    doc_lines = [summary]
    if desc:
        doc_lines.extend(["", desc])
    if properties:
        doc_lines.extend(["", "Args:"])
        for prop_name, prop_schema in properties.items():
            safe_param = sanitize_name(prop_name) or prop_name
            p_desc = (
                prop_schema.get("description", f"Workflow input {prop_name}.")
                if isinstance(prop_schema, dict)
                else f"Workflow input {prop_name}."
            )
            doc_lines.append(f"    {safe_param}: {p_desc}")
    doc_lines.extend(["", "Returns:", "    Dictionary of workflow outputs."])
    doc_text = chr(10).join(doc_lines)
    body_stmts.append(
        cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{doc_text}"""'))])
    )

    body_stmts.append(
        cst.parse_statement(
            f"inputs: dict[str, Any] = {{{', '.join(input_dict_items)}}}"
        )
    )
    body_stmts.append(
        cst.parse_statement("steps_context: dict[str, dict[str, Any]] = {}")
    )
    body_stmts.append(cst.parse_statement("workflow_outputs: dict[str, Any] = {}"))
    ctx_entries = [
        "'inputs': inputs",
        "'steps': steps_context",
        "'outputs': workflow_outputs",
        "'self': self.__self_uri__",
    ]
    if workflow.parameters:
        wf_params_dump = [
            p.model_dump(by_alias=True, exclude_none=True) for p in workflow.parameters
        ]
        ctx_entries.append(f"'workflow_parameters': {wf_params_dump!r}")
    if workflow.successActions:
        wf_sa_dump = [
            s.model_dump(by_alias=True, exclude_none=True)
            for s in workflow.successActions
        ]
        ctx_entries.append(f"'workflow_success_actions': {wf_sa_dump!r}")
    if workflow.failureActions:
        wf_fa_dump = [
            f.model_dump(by_alias=True, exclude_none=True)
            for f in workflow.failureActions
        ]
        ctx_entries.append(f"'workflow_failure_actions': {wf_fa_dump!r}")
    body_stmts.append(
        cst.parse_statement(f"context: dict[str, Any] = {{{', '.join(ctx_entries)}}}")
    )

    if workflow.dependsOn:
        for dep_wf in workflow.dependsOn:
            dep_method = sanitize_name(dep_wf)
            body_stmts.append(cst.parse_statement(f"self.{dep_method}()"))

    for step in workflow.steps:
        body_stmts.extend(_emit_step_statements(step, workflow, spec, sources))

    if workflow.outputs:
        for out_k, out_expr in workflow.outputs.items():
            if isinstance(out_expr, SelectorObject):
                sel_dict = out_expr.model_dump(by_alias=True, exclude_none=True)
                body_stmts.append(
                    cst.parse_statement(
                        f"workflow_outputs[{out_k!r}] = evaluate_selector(SelectorObject(**{sel_dict!r}), context)"
                    )
                )
            else:
                val_cst = compile_expression_to_cst(out_expr)
                val_code = cst.Module([]).code_for_node(val_cst)
                body_stmts.append(
                    cst.parse_statement(f"workflow_outputs[{out_k!r}] = {val_code}")
                )

    body_stmts.append(cst.parse_statement("return workflow_outputs"))
    return cst.FunctionDef(
        name=cst.Name(method_name),
        params=cst.Parameters(params=all_params),
        body=cst.IndentedBlock(body=body_stmts),
        returns=cst.Annotation(cst.parse_expression("dict[str, Any]")),
    )


def emit_workflows_module(
    spec: Arazzo,
    sources: dict[str, OpenAPI | Arazzo | dict[str, Any]] | None = None,
) -> cst.Module:
    """Emit a complete Python module containing the `Workflows` orchestrator class.

    Args:
        spec: The `Arazzo` specification model.
        sources: Optional resolved `sourceDescriptions` mapping.

    Returns:
        The generated `libcst.Module` node.
    """
    resolved_sources = sources or {}
    mod_summary = spec.info.summary or spec.info.title
    mod_desc = spec.info.description or "Generated Arazzo 1.1.0 workflow orchestrator."
    mod_doc = f'"""{mod_summary}{chr(10)}{chr(10)}{mod_desc}"""'

    header_code = chr(10).join(
        [
            mod_doc,
            "",
            "from __future__ import annotations",
            "",
            "import time",
            "from typing import Any",
            "",
            "from openapi_client.arazzo.expressions import (",
            "    apply_payload_replacements,",
            "    evaluate_criterion,",
            "    evaluate_runtime_expression,",
            "    evaluate_selector,",
            ")",
            "from openapi_client.arazzo_models import (",
            "    CriterionObject,",
            "    PayloadReplacement,",
            "    SelectorObject,",
            ")",
            "",
        ]
    )
    header_mod = cst.parse_module(header_code)

    init_code = chr(10).join(
        [
            "def __init__(self, client: Any = None, clients: dict[str, Any] | None = None) -> None:",
            '    """Initialize the Workflows orchestrator.',
            "",
            "    Args:",
            "        client: Default API client instance.",
            "        clients: Optional mapping of sourceDescription names to client instances.",
            '    """',
            "    self.client = client",
            "    self.clients = clients or ({'default': client} if client is not None else {})",
        ]
    )

    class_body: list[cst.BaseStatement] = [
        cst.SimpleStatementLine(
            [
                cst.Expr(
                    cst.SimpleString(
                        f'"""Workflows orchestrator for {spec.info.title} (v{spec.info.version})."""'
                    )
                )
            ]
        ),
        cst.parse_statement(f"__arazzo_version__: str = {spec.arazzo!r}"),
        cst.parse_statement(f"__self_uri__: str | None = {spec.self_!r}"),
        cst.parse_statement(
            f"__info__: dict[str, Any] = {spec.info.model_dump(by_alias=True, exclude_none=True)!r}"
        ),
        cst.parse_statement(
            f"__source_descriptions__: list[dict[str, Any]] = {[s.model_dump(by_alias=True, exclude_none=True) for s in spec.sourceDescriptions]!r}"
        ),
        cst.parse_statement(
            f"__components__: dict[str, Any] | None = {spec.components.model_dump(by_alias=True, exclude_none=True) if spec.components else None!r}"
        ),
        cst.parse_statement(init_code),
    ]

    for wf in spec.workflows:
        class_body.append(emit_workflow_method(wf, spec, resolved_sources))

    workflows_class = cst.ClassDef(
        name=cst.Name("Workflows"),
        body=cst.IndentedBlock(body=class_body),
    )

    full_body = list(header_mod.body) + [cst.EmptyLine(), workflows_class]
    return build_cst_module(full_body)


def emit_workflows_code(
    spec: Arazzo,
    sources: dict[str, OpenAPI | Arazzo | dict[str, Any]] | None = None,
) -> str:
    """Generate the Python source code string for an Arazzo `Workflows` module.

    Args:
        spec: The `Arazzo` specification model.
        sources: Optional resolved `sourceDescriptions` mapping.

    Returns:
        The generated Python code string.
    """
    return emit_workflows_module(spec, sources).code
