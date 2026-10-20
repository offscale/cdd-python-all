"""Module for extracting an Arazzo 1.1.0 specification from a Python CLI workflow runner AST."""

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


def _eval_arg_literal(node: cst.BaseExpression) -> Any:
    """Safely evaluate a LibCST argument expression into a Python literal.

    Args:
        node: The LibCST `BaseExpression` node.

    Returns:
        The evaluated literal value, or `None` if not a static literal.
    """
    code = cst.Module([]).code_for_node(node).strip()
    try:
        return ast.literal_eval(code)
    except (ValueError, SyntaxError):
        return None


class CLIArazzoExtractor(cst.CSTVisitor):
    """LibCST Visitor to extract Arazzo workflows and input flags from a CLI runner module."""

    def __init__(self) -> None:
        """Initialize the `CLIArazzoExtractor`."""
        self.info_dict: dict[str, Any] | None = None
        self.source_descriptions: list[dict[str, Any]] | None = None
        self.title: str = "CLI Workflows"
        self.description: str | None = None
        self.version: str = "1.0.0"
        self.parser_var_to_workflow: dict[str, dict[str, Any]] = {}

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        """Extract module-level `__arazzo_info__` and `__source_descriptions__` annotations.

        Args:
            node: The `libcst.AnnAssign` node being visited.
        """
        t_name = node.target.value if isinstance(node.target, cst.Name) else ""
        attr = {
            "__arazzo_info__": "info_dict",
            "__source_descriptions__": "source_descriptions",
        }.get(t_name)
        if attr and node.value is not None:
            setattr(self, attr, _eval_arg_literal(node.value))

    def visit_Assign(self, node: cst.Assign) -> None:
        """Extract `ArgumentParser(...)` and `subparsers.add_parser(...)` assignments.

        Args:
            node: The `libcst.Assign` node being visited.
        """
        if not isinstance(node.targets[0].target, cst.Name) or not isinstance(
            node.value, cst.Call
        ):
            return
        var_name = node.targets[0].target.value
        call = node.value
        func_code = cst.Module([]).code_for_node(call.func).strip()
        kwargs = {
            arg.keyword.value: _eval_arg_literal(arg.value)
            for arg in call.args
            if arg.keyword is not None
        }

        if func_code.endswith("ArgumentParser"):
            self.title = str(kwargs.get("prog", self.title))
            self.description = (
                str(kwargs["description"]) if "description" in kwargs else None
            )
        elif func_code.endswith(".add_parser") and call.args:
            wf_id = str(_eval_arg_literal(call.args[0].value))
            help_val = str(kwargs["help"]) if "help" in kwargs else None
            desc_val = str(kwargs["description"]) if "description" in kwargs else None
            self.parser_var_to_workflow[var_name] = {
                "workflowId": wf_id,
                "summary": None if help_val == f"Run workflow {wf_id}" else help_val,
                "description": None
                if desc_val in (help_val, f"Run workflow {wf_id}")
                else desc_val,
                "properties": {},
                "required": [],
                "steps": None,
            }

    def visit_Call(self, node: cst.Call) -> None:
        """Extract `.add_argument(...)` and `.set_defaults(...)` calls on workflow subparsers.

        Args:
            node: The `libcst.Call` node being visited.
        """
        func_code = cst.Module([]).code_for_node(node.func).strip()
        if func_code.endswith(".set_defaults"):
            owner_var = func_code[: -len(".set_defaults")]
            wf_entry = self.parser_var_to_workflow.get(owner_var)
            if wf_entry is not None:
                defaults_map = {
                    arg.keyword.value: _eval_arg_literal(arg.value)
                    for arg in node.args
                    if arg.keyword is not None
                }
                wf_entry["steps"] = [
                    StepObject(**s) for s in defaults_map.get("_steps", [])
                ] or wf_entry["steps"]
                wf_entry["summary"] = defaults_map.get("_summary", wf_entry["summary"])
                wf_entry["description"] = defaults_map.get(
                    "_description", wf_entry["description"]
                )
            return

        if not func_code.endswith(".add_argument") or not node.args:
            return
        owner_var = func_code[: -len(".add_argument")]
        flag_str = str(_eval_arg_literal(node.args[0].value) or "")

        if owner_var == "parser":
            for arg in node.args[1:]:
                if arg.keyword and arg.keyword.value == "version":
                    self.version = str(_eval_arg_literal(arg.value))
            return

        if owner_var not in self.parser_var_to_workflow or flag_str in (
            "--format",
            "--step",
            "-v",
            "--verbose",
        ):
            return

        wf_entry = self.parser_var_to_workflow[owner_var]
        prop_name = flag_str.lstrip("-").replace("-", "_")
        json_type = "string"
        is_req = False
        default_val: Any = None
        help_text: str | None = None

        for arg in node.args[1:]:
            kw = arg.keyword.value if arg.keyword else ""
            if kw == "dest":
                prop_name = str(_eval_arg_literal(arg.value))
            elif kw == "type":
                t_code = cst.Module([]).code_for_node(arg.value).strip()
                json_type = (
                    "integer"
                    if t_code == "int"
                    else ("number" if t_code == "float" else "string")
                )
            elif kw == "required":
                is_req = bool(_eval_arg_literal(arg.value))
            elif kw == "default":
                default_val = _eval_arg_literal(arg.value)
            else:
                help_text = str(_eval_arg_literal(arg.value))

        prop_schema: dict[str, Any] = {"type": json_type}
        if help_text and help_text != f"Input parameter {prop_name}":
            prop_schema["description"] = help_text
        if default_val is not None:
            prop_schema["default"] = default_val
        wf_entry["properties"][prop_name] = prop_schema
        if is_req:
            wf_entry["required"].append(prop_name)


def extract_arazzo_from_cli_ast(module: cst.Module) -> Arazzo:
    """Extract an `Arazzo` specification from a parsed CLI LibCST `Module`.

    Args:
        module: The parsed LibCST `Module` node.

    Returns:
        The extracted `Arazzo` specification model.
    """
    visitor = CLIArazzoExtractor()
    module.visit(visitor)

    workflows: list[WorkflowObject] = []
    for wf_data in visitor.parser_var_to_workflow.values():
        wf_id = wf_data["workflowId"]
        props = wf_data["properties"]
        req = wf_data["required"]
        inputs: dict[str, Any] | None = (
            {
                "type": "object",
                "properties": props,
                **({"required": req} if req else {}),
            }
            if props
            else None
        )
        steps = wf_data["steps"] or [StepObject(stepId="step_1", operationId=wf_id)]
        workflows.append(
            WorkflowObject(
                workflowId=wf_id,
                summary=wf_data["summary"],
                description=wf_data["description"],
                inputs=inputs,
                steps=steps,
            )
        )

    info_obj = (
        ArazzoInfo(**visitor.info_dict)
        if visitor.info_dict
        else ArazzoInfo(
            title=visitor.title,
            description=visitor.description,
            version=visitor.version,
        )
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
        workflows=workflows,
    )


def extract_arazzo_from_cli_code(code: str) -> Arazzo:
    """Extract an `Arazzo` specification from Python CLI source code.

    Args:
        code: Python CLI source code string.

    Returns:
        The extracted `Arazzo` specification model.
    """
    return extract_arazzo_from_cli_ast(cst.parse_module(code))
