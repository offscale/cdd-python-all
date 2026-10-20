"""Module for extracting an Arazzo 1.1.0 specification from Python SDK workflow code."""

from __future__ import annotations

import ast
import re
from typing import Any

import libcst as cst

from openapi_client.arazzo.expressions import extract_expression_from_cst
from openapi_client.arazzo_models import (
    Arazzo,
    ArazzoComponents,
    ArazzoInfo,
    ArazzoParameter,
    ArazzoRequestBody,
    CriterionObject,
    FailureAction,
    PayloadReplacement,
    SelectorObject,
    SourceDescription,
    StepObject,
    SuccessAction,
    WorkflowObject,
)
from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import OpenAPI


def _python_type_to_json_type(annotation_code: str) -> str:
    """Convert a Python type annotation string into a JSON Schema primitive type.

    Args:
        annotation_code: Python type annotation string (e.g. `'int | None'`, `'str'`).

    Returns:
        JSON Schema type string (`'string'`, `'integer'`, `'number'`, `'boolean'`, `'array'`, `'object'`).
    """
    clean = annotation_code.replace("| None", "").strip()
    if clean in ("int",):
        return "integer"
    if clean in ("float",):
        return "number"
    if clean in ("bool",):
        return "boolean"
    if clean.startswith("list"):
        return "array"
    if clean.startswith("dict"):
        return "object"
    return "string"


def _safe_literal_eval(code_str: str) -> Any:
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


def _extract_step_from_call(
    call_node: cst.Call,
    step_index: int,
    step_body_expr: Any | None,
    step_replacements: list[PayloadReplacement] | None,
    depends_on: list[str],
    retry_limit: int | None = None,
    retry_after: float | None = None,
) -> StepObject:
    """Construct a `StepObject` from a `self.client.<op>(...)` or `self.<workflow>(...)` call.

    Args:
        call_node: The LibCST `Call` node representing the step invocation.
        step_index: 1-based step index used as fallback `stepId`.
        step_body_expr: Optional request body payload expression captured prior to the call.
        step_replacements: Optional list of `PayloadReplacement` objects captured prior to the call.
        depends_on: List of prerequisite `stepId`s captured for this step.
        retry_limit: Optional retry limit from an enclosing retry loop.
        retry_after: Optional retry delay from an enclosing retry loop.

    Returns:
        A reconstructed `StepObject`.
    """
    func_code = cst.Module([]).code_for_node(call_node.func).strip()
    operation_id: str | None = None
    operation_path: str | None = None
    workflow_id: str | None = None
    channel_path: str | None = None

    if func_code.startswith("self.client."):
        method_name = func_code[len("self.client.") :]
        if method_name == "request":
            verb = str(extract_expression_from_cst(call_node.args[0].value)).lower()
            route = str(extract_expression_from_cst(call_node.args[1].value))
            encoded = route.replace("~", "~0").replace("/", "~1")
            operation_path = f"#/paths/{encoded}/{verb}"
        elif method_name == "channel":
            channel_path = str(extract_expression_from_cst(call_node.args[0].value))
        elif method_name != "call_step":
            operation_id = method_name
    elif func_code.startswith("self.clients["):
        m_cli = re.match(
            r"""^self\.clients\[\s*(['"])([^'"]+)\1\s*\]\.([A-Za-z0-9_]+)$""", func_code
        )
        operation_id = (
            f"$sourceDescriptions.{m_cli.group(2)}.{m_cli.group(3)}" if m_cli else None
        )
    else:
        workflow_id = func_code[len("self.") :]

    params: list[ArazzoParameter] = []
    timeout_val: int | None = None
    action_val: Any = None
    corr_val: str | None = None
    content_type_val: str | None = None
    req_body: ArazzoRequestBody | None = None

    for arg in call_node.args:
        if arg.keyword is None:
            continue
        kw = arg.keyword.value
        val = extract_expression_from_cst(arg.value)
        if kw == "operation_path" and isinstance(val, str):
            operation_path = val
            operation_id = None
        elif kw == "content_type" and isinstance(val, str):
            content_type_val = val
        elif kw == "body":
            payload_val = step_body_expr if step_body_expr is not None else val
            req_body = ArazzoRequestBody(
                contentType=content_type_val,
                payload=payload_val,
                replacements=step_replacements,
            )
        elif kw == "timeout" and isinstance(val, int):
            timeout_val = val
        elif kw == "action" and val in ("send", "receive"):
            action_val = val
        elif kw == "correlation_id" and isinstance(val, str):
            corr_val = val
        else:
            params.append(ArazzoParameter(name=kw, in_="query", value=val))

    on_failure: list[FailureAction] | None = None
    if retry_limit is not None or retry_after is not None:
        on_failure = [
            FailureAction(
                name="retry_on_failure",
                type="retry",
                retryLimit=retry_limit,
                retryAfter=retry_after,
            )
        ]

    step_id = f"step_{step_index}"
    return StepObject(
        stepId=step_id,
        operationId=operation_id,
        operationPath=operation_path,
        channelPath=channel_path,
        workflowId=workflow_id,
        parameters=params if params else None,
        requestBody=req_body,
        onFailure=on_failure,
        timeout=timeout_val,
        correlationId=corr_val,
        action=action_val,
        dependsOn=list(depends_on) if depends_on else None,
    )


class WorkflowExtractor(cst.CSTVisitor):
    """LibCST Visitor to extract an `Arazzo` specification from a Python `Workflows` module."""

    def __init__(self, openapi_spec: OpenAPI | None = None) -> None:
        """Initialize the `WorkflowExtractor`.

        Args:
            openapi_spec: Optional companion `OpenAPI` specification for enriching metadata.
        """
        self.openapi_spec = openapi_spec
        self.arazzo_version: str = "1.1.0"
        self.self_uri: str | None = None
        self.info_dict: dict[str, Any] = {
            "title": openapi_spec.info.title if openapi_spec else "Extracted Workflows",
            "version": openapi_spec.info.version if openapi_spec else "1.0.0",
        }
        self.source_descriptions: list[dict[str, Any]] = [
            {"name": "default", "url": "openapi.json", "type": "openapi"}
        ]
        self.components_dict: dict[str, Any] | None = None
        self.extracted_workflows: list[WorkflowObject] = []

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """Visit class definitions to extract Arazzo metadata and workflow methods.

        Args:
            node: The `libcst.ClassDef` node being visited.
        """
        for stmt in node.body.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                item = stmt.body[0]
                target_name: str | None = None
                val_node: cst.BaseExpression | None = None
                if isinstance(item, cst.AnnAssign) and isinstance(
                    item.target, cst.Name
                ):
                    target_name = item.target.value
                    val_node = item.value
                elif isinstance(item, cst.Assign) and isinstance(
                    item.targets[0].target, cst.Name
                ):
                    target_name = item.targets[0].target.value
                    val_node = item.value

                if target_name and val_node is not None:
                    val_code = cst.Module([]).code_for_node(val_node).strip()
                    lit = _safe_literal_eval(val_code)
                    attr_map = {
                        "__arazzo_version__": ("arazzo_version", str(lit or "1.1.0")),
                        "__self_uri__": (
                            "self_uri",
                            lit if isinstance(lit, str) else None,
                        ),
                        "__info__": (
                            "info_dict",
                            lit if isinstance(lit, dict) else self.info_dict,
                        ),
                        "__source_descriptions__": (
                            "source_descriptions",
                            lit if isinstance(lit, list) else self.source_descriptions,
                        ),
                        "__components__": (
                            "components_dict",
                            lit if isinstance(lit, dict) else None,
                        ),
                    }
                    attr_key, attr_val = attr_map.get(target_name, ("_ignored", None))
                    setattr(self, attr_key, attr_val)

            elif isinstance(stmt, cst.FunctionDef) and not stmt.name.value.startswith(
                "_"
            ):
                self.extracted_workflows.append(
                    self._extract_workflow_from_method(stmt)
                )

    def _extract_workflow_from_method(self, node: cst.FunctionDef) -> WorkflowObject:
        """Extract a `WorkflowObject` from a workflow method `FunctionDef`.

        Args:
            node: The `libcst.FunctionDef` node representing a workflow method.

        Returns:
            The extracted `WorkflowObject`.
        """
        wf_id = node.name.value
        summary, description = parse_docstring(node)
        param_docs: dict[str, str] = {}
        if description and "Args:" in description:
            args_part = description.split("Args:", 1)[1].split("Returns:", 1)[0]
            for line in args_part.splitlines():
                if ":" in line:
                    k_p, v_p = line.split(":", 1)
                    param_docs[k_p.strip()] = v_p.strip()
        description = (
            description.split("Args:", 1)[0].split("Returns:", 1)[0].strip() or None
            if description
            else None
        )
        summary = (
            summary.split("Returns:", 1)[0].strip() or None
            if summary and summary != f"Execute workflow {wf_id}."
            else None
        )

        props: dict[str, Any] = {}
        required: list[str] = []
        for param in node.params.params:
            p_name = param.name.value
            if p_name in ("self", "cls"):
                continue
            ann_code = (
                cst.Module([]).code_for_node(param.annotation.annotation).strip()
                if param.annotation
                else "str"
            )
            prop_entry: dict[str, Any] = {"type": _python_type_to_json_type(ann_code)}
            if param_docs.get(p_name, f"Workflow input {p_name}.") != (
                f"Workflow input {p_name}."
            ):
                prop_entry["description"] = param_docs[p_name]
            if param.default is None:
                required.append(p_name)
            else:
                def_code = cst.Module([]).code_for_node(param.default).strip()
                prop_entry["default"] = _safe_literal_eval(def_code)
            props[p_name] = prop_entry

        inputs_schema: dict[str, Any] | None = (
            {
                "type": "object",
                "properties": props,
                **({"required": required} if required else {}),
            }
            if props
            else None
        )

        depends_on_workflows: list[str] = []
        steps: list[StepObject] = []
        wf_outputs: dict[str, str | SelectorObject] = {}
        wf_parameters: list[ArazzoParameter] | None = None
        wf_success_actions: list[SuccessAction] | None = None
        wf_failure_actions: list[FailureAction] | None = None

        pending_step_deps: list[str] = []
        pending_body_expr: Any | None = None
        pending_replacements: list[PayloadReplacement] | None = None
        pending_retry_limit: int | None = None
        current_step: StepObject | None = None

        for stmt in node.body.body:
            stmt_code = cst.Module([]).code_for_node(stmt).strip()

            m_dep_wf = re.match(r"^self\.([A-Za-z0-9_]+)\(\)$", stmt_code)
            if m_dep_wf and not steps:
                depends_on_workflows.append(m_dep_wf.group(1))
                continue

            m_step_dep = re.match(
                r"""^assert\s+(['"])([^'"]+)\1\s+in\s+steps_context""", stmt_code
            )
            if m_step_dep:
                pending_step_deps.append(m_step_dep.group(2))
                continue

            m_retries = re.match(r"^_retries_left\s*=\s*(\d+)$", stmt_code)
            if m_retries:
                pending_retry_limit = int(m_retries.group(1))
                continue

            if isinstance(stmt, cst.SimpleStatementLine):
                inner = stmt.body[0]
                if (
                    isinstance(inner, cst.AnnAssign)
                    and isinstance(inner.target, cst.Name)
                    and inner.target.value == "context"
                    and isinstance(inner.value, cst.Dict)
                ):
                    ctx_map = {
                        _safe_literal_eval(
                            cst.Module([]).code_for_node(el.key).strip()
                        ): _safe_literal_eval(
                            cst.Module([]).code_for_node(el.value).strip()
                        )
                        for el in inner.value.elements
                        if isinstance(el, cst.DictElement)
                    }
                    if isinstance(ctx_map.get("workflow_parameters"), list):
                        wf_parameters = [
                            ArazzoParameter(**p) for p in ctx_map["workflow_parameters"]
                        ]
                    if isinstance(ctx_map.get("workflow_success_actions"), list):
                        wf_success_actions = [
                            SuccessAction(**s)
                            for s in ctx_map["workflow_success_actions"]
                        ]
                    if isinstance(ctx_map.get("workflow_failure_actions"), list):
                        wf_failure_actions = [
                            FailureAction(**f)
                            for f in ctx_map["workflow_failure_actions"]
                        ]
                    continue

                if isinstance(inner, cst.Assign):
                    t_code = (
                        cst.Module([]).code_for_node(inner.targets[0].target).strip()
                    )
                    if t_code == "step_body":
                        val_code = cst.Module([]).code_for_node(inner.value).strip()
                        if val_code.startswith(
                            "apply_payload_replacements("
                        ) and isinstance(inner.value, cst.Call):
                            base_code = (
                                cst.Module([])
                                .code_for_node(inner.value.args[0].value)
                                .strip()
                            )
                            pending_body_expr = _safe_literal_eval(base_code)
                            reps_code = (
                                cst.Module([])
                                .code_for_node(inner.value.args[1].value)
                                .strip()
                            )
                            m_reps = re.search(r"for\s+r\s+in\s+(\[.*\])\]$", reps_code)
                            raw_reps = (
                                _safe_literal_eval(m_reps.group(1)) if m_reps else []
                            )
                            pending_replacements = [
                                PayloadReplacement(**r)
                                for r in (
                                    raw_reps if isinstance(raw_reps, list) else []
                                )
                            ]
                        else:
                            lit_body = _safe_literal_eval(val_code)
                            pending_body_expr = (
                                lit_body
                                if isinstance(lit_body, (dict, list))
                                else extract_expression_from_cst(inner.value)
                            )
                        continue

                    if t_code == "response" and isinstance(inner.value, cst.Call):
                        step_obj = _extract_step_from_call(
                            inner.value,
                            len(steps) + 1,
                            pending_body_expr,
                            pending_replacements,
                            pending_step_deps,
                        )
                        steps.append(step_obj)
                        current_step = step_obj
                        pending_body_expr = None
                        pending_replacements = None
                        pending_step_deps = []
                        continue

                    m_sc = re.match(
                        r"""^steps_context\[\s*(['"])([^'"]+)\1\s*\]$""", t_code
                    )
                    if (
                        m_sc
                        and current_step is not None
                        and isinstance(inner.value, cst.Dict)
                    ):
                        current_step.stepId = m_sc.group(2)
                        first_elem = inner.value.elements[0]
                        out_dict_node = (
                            first_elem.value
                            if isinstance(first_elem, cst.DictElement)
                            and isinstance(first_elem.value, cst.Dict)
                            else cst.Dict([])
                        )
                        out_map: dict[str, str | SelectorObject] = {}
                        for out_el in [
                            e
                            for e in out_dict_node.elements
                            if isinstance(e, cst.DictElement)
                        ]:
                            k_str = str(
                                _safe_literal_eval(
                                    cst.Module([]).code_for_node(out_el.key).strip()
                                )
                            )
                            el_code = cst.Module([]).code_for_node(out_el.value).strip()
                            m_sel_dict = re.search(
                                r"SelectorObject\(\*\*(\{.*?\})\)", el_code
                            )
                            if m_sel_dict and isinstance(
                                (s_d := _safe_literal_eval(m_sel_dict.group(1))),
                                dict,
                            ):
                                out_map[k_str] = SelectorObject(**s_d)
                            else:
                                ov = extract_expression_from_cst(out_el.value)
                                out_map[k_str] = (
                                    ov
                                    if isinstance(ov, (str, SelectorObject))
                                    else str(ov)
                                )
                        if out_map:
                            current_step.outputs = out_map

                        sc_elems = {
                            _safe_literal_eval(
                                cst.Module([]).code_for_node(el.key).strip()
                            ): _safe_literal_eval(
                                cst.Module([]).code_for_node(el.value).strip()
                            )
                            for el in inner.value.elements
                            if isinstance(el, cst.DictElement)
                        }
                        meta_dict = sc_elems.get("meta") or {}
                        has_meta_params = "parameters" in meta_dict
                        has_meta_success = "onSuccess" in meta_dict
                        has_meta_failure = "onFailure" in meta_dict
                        if has_meta_params:
                            current_step.parameters = [
                                ArazzoParameter(**p) for p in meta_dict["parameters"]
                            ]
                        if has_meta_success:
                            current_step.onSuccess = [
                                SuccessAction(**s) for s in meta_dict["onSuccess"]
                            ]
                        if has_meta_failure:
                            current_step.onFailure = [
                                FailureAction(**f) for f in meta_dict["onFailure"]
                            ]
                        if not has_meta_params and wf_parameters:
                            wf_param_names = {p.name for p in wf_parameters}
                            rem_params = [
                                p
                                for p in (current_step.parameters or [])
                                if p.name not in wf_param_names
                            ]
                            current_step.parameters = rem_params or None
                        if not has_meta_success and wf_success_actions:
                            current_step.onSuccess = None
                        if not has_meta_failure and wf_failure_actions:
                            current_step.onFailure = None
                        continue

                    m_wo = re.match(
                        r"""^workflow_outputs\[\s*(['"])([^'"]+)\1\s*\]$""", t_code
                    )
                    if m_wo:
                        out_name = m_wo.group(2)
                        val_code = cst.Module([]).code_for_node(inner.value).strip()
                        m_sel_dict = re.search(
                            r"SelectorObject\(\*\*(\{.*?\})\)", val_code
                        )
                        if m_sel_dict and isinstance(
                            (s_d := _safe_literal_eval(m_sel_dict.group(1))), dict
                        ):
                            wf_outputs[out_name] = SelectorObject(**s_d)
                        else:
                            out_val = extract_expression_from_cst(inner.value)
                            wf_outputs[out_name] = (
                                out_val
                                if isinstance(out_val, (str, SelectorObject))
                                else str(out_val)
                            )
                        continue

                if isinstance(inner, cst.Assert) and current_step is not None:
                    test_code = cst.Module([]).code_for_node(inner.test).strip()
                    m_crit = re.search(r"CriterionObject\(\*\*(\{.*?\})\)", test_code)
                    c_dict = _safe_literal_eval(m_crit.group(1)) if m_crit else None
                    crit_obj = (
                        CriterionObject(**c_dict)
                        if isinstance(c_dict, dict)
                        else CriterionObject(condition=test_code)
                    )
                    current_step.successCriteria = (
                        current_step.successCriteria or []
                    ) + [crit_obj]
                    continue

            if isinstance(stmt, cst.While):
                while_code = cst.Module([]).code_for_node(stmt).strip()
                m_sleep = re.search(r"time\.sleep\(([0-9.]+)\)", while_code)
                s_val = m_sleep.group(1) if m_sleep else "0"
                retry_delay: float | int = float(s_val) if "." in s_val else int(s_val)
                first_stmt = stmt.body.body[0]
                call_val = (
                    first_stmt.body[0].value
                    if isinstance(first_stmt, cst.SimpleStatementLine)
                    and isinstance(first_stmt.body[0], cst.Assign)
                    and isinstance(first_stmt.body[0].value, cst.Call)
                    else cst.Call(func=cst.Name("noop"))
                )
                step_obj = _extract_step_from_call(
                    call_val,
                    len(steps) + 1,
                    pending_body_expr,
                    pending_replacements,
                    pending_step_deps,
                    retry_limit=pending_retry_limit,
                    retry_after=retry_delay,
                )
                steps.append(step_obj)
                current_step = step_obj
                pending_body_expr = None
                pending_replacements = None
                pending_step_deps = []
                pending_retry_limit = None
                continue

            if isinstance(stmt, cst.If) and current_step is not None:
                if_code = cst.Module([]).code_for_node(stmt).strip()
                m_goto = re.search(r"return\s+self\.([A-Za-z0-9_]+)\(\)", if_code)
                if m_goto:
                    action_obj = SuccessAction(
                        name=f"goto_{m_goto.group(1)}",
                        type="goto",
                        workflowId=m_goto.group(1),
                    )
                else:
                    m_crit = re.search(r"CriterionObject\(\*\*(\{.*?\})\)", if_code)
                    cd = _safe_literal_eval(m_crit.group(1)) if m_crit else None
                    crit_list = (
                        [CriterionObject(**cd)] if isinstance(cd, dict) else None
                    )
                    action_obj = SuccessAction(
                        name="end_workflow",
                        type="end",
                        criteria=crit_list,
                    )
                current_step.onSuccess = (current_step.onSuccess or []) + [action_obj]

        if not steps:
            steps = [StepObject(stepId="step_1", operationId=wf_id)]

        return WorkflowObject(
            workflowId=wf_id,
            summary=summary,
            description=description,
            inputs=inputs_schema,
            dependsOn=depends_on_workflows if depends_on_workflows else None,
            parameters=wf_parameters,
            steps=steps,
            successActions=wf_success_actions,
            failureActions=wf_failure_actions,
            outputs=wf_outputs if wf_outputs else None,
        )


def extract_arazzo_from_ast(
    module: cst.Module, openapi_spec: OpenAPI | None = None
) -> Arazzo:
    """Extract an `Arazzo` 1.1.0 specification from a parsed LibCST `Module`.

    Args:
        module: The parsed LibCST `Module` node.
        openapi_spec: Optional companion `OpenAPI` model for metadata fallback.

    Returns:
        The extracted `Arazzo` specification model.
    """
    visitor = WorkflowExtractor(openapi_spec)
    module.visit(visitor)

    return Arazzo(
        arazzo=visitor.arazzo_version,
        self_=visitor.self_uri,
        info=ArazzoInfo(**visitor.info_dict),
        sourceDescriptions=[
            SourceDescription(**sd) for sd in visitor.source_descriptions
        ],
        workflows=visitor.extracted_workflows,
        components=(
            ArazzoComponents(**visitor.components_dict)
            if visitor.components_dict
            else None
        ),
    )


def extract_arazzo_from_code(code: str, openapi_spec: OpenAPI | None = None) -> Arazzo:
    """Extract an `Arazzo` 1.1.0 specification from a Python source code string.

    Args:
        code: Python source code containing a `Workflows` class.
        openapi_spec: Optional companion `OpenAPI` model.

    Returns:
        The extracted `Arazzo` specification model.
    """
    module = cst.parse_module(code)
    return extract_arazzo_from_ast(module, openapi_spec)
