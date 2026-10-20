"""Module for emitting a Python CLI workflow runner from an Arazzo 1.1.0 specification."""

from __future__ import annotations

from typing import Any

import libcst as cst

from openapi_client.arazzo_models import Arazzo, WorkflowObject
from openapi_client.functions.utils import build_cst_module, sanitize_name
from openapi_client.workflows.emit import _get_json_schema_dict


def _schema_prop_to_argparse_type(prop_schema: dict[str, Any]) -> str:
    """Map a JSON Schema property type to an `argparse` `type=` identifier.

    Args:
        prop_schema: Property schema dictionary.

    Returns:
        Python built-in type name (`'int'`, `'float'`, or `'str'`).
    """
    t = prop_schema.get("type")
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    return "str"


def _emit_workflow_subparser_stmts(
    workflow: WorkflowObject, spec: Arazzo
) -> list[cst.BaseStatement]:
    """Emit LibCST statements registering an `argparse` subcommand for `workflow`.

    Args:
        workflow: The `WorkflowObject` to expose as a CLI subcommand.
        spec: The containing `Arazzo` specification.

    Returns:
        List of `libcst.BaseStatement` nodes configuring the workflow subparser.
    """
    stmts: list[cst.BaseStatement] = []
    wf_var = f"parser_{sanitize_name(workflow.workflowId) or 'wf'}"
    help_str = workflow.summary or f"Run workflow {workflow.workflowId}"
    desc_str = workflow.description or help_str

    stmts.append(
        cst.parse_statement(
            f"{wf_var} = subparsers.add_parser({workflow.workflowId!r}, help={help_str!r}, description={desc_str!r})"
        )
    )

    schema_dict = _get_json_schema_dict(workflow.inputs, spec)
    properties: dict[str, Any] = schema_dict.get("properties", {})
    required_set: set[str] = set(schema_dict.get("required", []))

    for prop_name, prop_schema in properties.items():
        p_dict = prop_schema if isinstance(prop_schema, dict) else {}
        arg_type = _schema_prop_to_argparse_type(p_dict)
        is_req = prop_name in required_set
        default_val = p_dict.get("default")
        p_help = p_dict.get("description", f"Input parameter {prop_name}")
        flag = f"--{prop_name.replace('_', '-')}"
        dest = sanitize_name(prop_name) or prop_name
        stmts.append(
            cst.parse_statement(
                f"{wf_var}.add_argument({flag!r}, dest={dest!r}, type={arg_type}, required={is_req!r}, default={default_val!r}, help={p_help!r})"
            )
        )

    step_choices = [s.stepId for s in workflow.steps]
    step_targets = [
        {"stepId": s.stepId, "operationId": s.operationId} for s in workflow.steps
    ]
    stmts.append(
        cst.parse_statement(
            f"{wf_var}.add_argument('--format', default='json', choices=['json', 'yaml', 'table'], help='Output format')"
        )
    )
    stmts.append(
        cst.parse_statement(
            f"{wf_var}.add_argument('--step', default=None, choices={step_choices!r}, help='Selective stepId to inspect')"
        )
    )
    stmts.append(
        cst.parse_statement(
            f"{wf_var}.set_defaults(_steps={step_targets!r}, _summary={workflow.summary!r}, _description={workflow.description!r})"
        )
    )
    stmts.append(
        cst.parse_statement(
            f"{wf_var}.add_argument('-v', '--verbose', action='store_true', help='Enable verbose step logging')"
        )
    )
    return stmts


def emit_arazzo_cli(spec: Arazzo) -> cst.Module:
    """Emit a complete Python CLI module (`cli_workflows.py` / `cli_main.py`) for an `Arazzo` spec.

    Args:
        spec: The `Arazzo` specification model.

    Returns:
        A `libcst.Module` node containing the generated CLI application.
    """
    desc = spec.info.description or spec.info.summary or spec.info.title
    sources_list = [
        s.model_dump(by_alias=True, exclude_none=True) for s in spec.sourceDescriptions
    ]

    header_code = chr(10).join(
        [
            f'"""CLI Workflow Runner for {spec.info.title} (v{spec.info.version})."""',
            "",
            "from __future__ import annotations",
            "",
            "import argparse",
            "import json",
            "import sys",
            "from typing import Any",
            "",
            "from client import Client",
            "from workflows import Workflows",
            "",
            f"__arazzo_info__: dict[str, Any] = {spec.info.model_dump(by_alias=True, exclude_none=True)!r}",
            f"__source_descriptions__: list[dict[str, Any]] = {sources_list!r}",
            "",
        ]
    )
    header_mod = cst.parse_module(header_code)

    main_doc = chr(10).join(
        [
            '"""Parse CLI workflow arguments and execute the selected Arazzo workflow.',
            "",
            "    Args:",
            "        argv: Optional list of CLI argument strings.",
            "",
            "    Returns:",
            "        Exit status code (0 for success, non-zero for error).",
            '    """',
        ]
    )

    main_stmts: list[cst.BaseStatement] = [
        cst.SimpleStatementLine([cst.Expr(cst.SimpleString(main_doc))]),
        cst.parse_statement(
            f"parser = argparse.ArgumentParser(prog={sanitize_name(spec.info.title) or 'arazzo-cli'!r}, description={desc!r})"
        ),
        cst.parse_statement(
            f"parser.add_argument('--version', action='version', version={spec.info.version!r})"
        ),
        cst.parse_statement(
            "parser.add_argument('--base-url', default='http://localhost:8080', help='Base API server URL')"
        ),
        cst.parse_statement(
            "subparsers = parser.add_subparsers(dest='workflow_id', required=True)"
        ),
    ]

    for wf in spec.workflows:
        main_stmts.extend(_emit_workflow_subparser_stmts(wf, spec))

    main_stmts.append(cst.parse_statement("args = parser.parse_args(argv)"))
    main_stmts.append(cst.parse_statement("client = Client(base_url=args.base_url)"))
    main_stmts.append(cst.parse_statement("runner = Workflows(client=client)"))

    for wf in spec.workflows:
        method_name = sanitize_name(wf.workflowId) or "run_workflow"
        schema_dict = _get_json_schema_dict(wf.inputs, spec)
        properties: dict[str, Any] = schema_dict.get("properties", {})
        kw_list: list[str] = []
        for prop_name in properties:
            dest = sanitize_name(prop_name) or prop_name
            kw_list.append(f"{dest}=getattr(args, {dest!r}, None)")
        call_str = f"runner.{method_name}({', '.join(kw_list)})"
        branch_code = chr(10).join(
            [
                f"if args.workflow_id == {wf.workflowId!r}:",
                f"    result = {call_str}",
                "    print(json.dumps(result, indent=2))",
                "    return 0",
            ]
        )
        main_stmts.append(cst.parse_statement(branch_code))

    main_stmts.append(cst.parse_statement("return 1"))

    main_fn = cst.FunctionDef(
        name=cst.Name("main"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("argv"),
                    annotation=cst.Annotation(cst.parse_expression("list[str] | None")),
                    default=cst.Name("None"),
                )
            ]
        ),
        body=cst.IndentedBlock(body=main_stmts),
        returns=cst.Annotation(cst.Name("int")),
    )

    body = list(header_mod.body) + [cst.EmptyLine(), main_fn]
    return build_cst_module(body)


def emit_arazzo_cli_code(spec: Arazzo) -> str:
    """Generate the Python source code string for an Arazzo CLI runner.

    Args:
        spec: The `Arazzo` specification model.

    Returns:
        The generated Python CLI source code string.
    """
    return emit_arazzo_cli(spec).code
