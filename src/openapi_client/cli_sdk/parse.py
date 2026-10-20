"""Module for parsing an existing CLI application and updating an OpenAPI specification."""

from __future__ import annotations

import libcst as cst

from openapi_client.models import (
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    RequestBody,
    Response,
    Schema,
)
from openapi_client.openapi.keywords import HTTP_METHODS

_BUILTIN_CLI_SUBCOMMANDS = frozenset({"mcp", "mcp_sse"})

_PY_TYPE_TO_OPENAPI: dict[str, str] = {
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "str": "string",
    "list": "array",
    "dict": "object",
}


def _infer_method_and_path(op_id: str) -> tuple[str, str]:
    """Infer an HTTP method and route path from a CLI operation identifier.

    Args:
        op_id: The operation identifier string (e.g. `'get_pets'` or `'test'`).

    Returns:
        A tuple of `(http_method, route_path)`.
    """
    if "_" in op_id:
        prefix, rest = op_id.split("_", 1)
        if prefix.lower() in HTTP_METHODS and rest:
            return prefix.lower(), f"/{rest}"
    return "get", f"/{op_id}"


class CLIExtractor(cst.CSTVisitor):
    """Visitor for extracting CLI arguments into an OpenAPI spec."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize the extractor.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec
        self._standalone: bool = not bool(spec.paths)
        self.current_op_id: str | None = None
        self.current_op: Operation | None = None

    def _select_operation(self, op_id: str) -> None:
        """Set `self.current_op` by matching or synthesizing `op_id` in `self.spec.paths`.

        Args:
            op_id: Target operation identifier.
        """
        self.current_op_id = op_id
        self.current_op = None
        if op_id in _BUILTIN_CLI_SUBCOMMANDS:
            return
        if self.spec.paths:
            for path_item in self.spec.paths.values():
                for method in HTTP_METHODS:
                    op = getattr(path_item, method, None)
                    if op and op.operationId == op_id:
                        self.current_op = op
                        return
        if self._standalone:
            if self.spec.paths is None:
                self.spec.paths = {}
            method, route_path = _infer_method_and_path(op_id)
            path_item = self.spec.paths.setdefault(route_path, PathItem())
            op = Operation(
                operationId=op_id,
                parameters=[],
                responses={"200": Response(description="Successful Response")},
            )
            setattr(path_item, method, op)
            self.current_op = op

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit helper functions `def set_cli_args_<op_id>(...)` to bind `self.current_op`.

        Args:
            node: The LibCST `FunctionDef` node being visited.
        """
        if node.name.value.startswith("set_cli_args_"):
            op_id = node.name.value[len("set_cli_args_") :]
            self._select_operation(op_id)

    def visit_Call(self, node: cst.Call) -> None:
        """Visit call nodes to extract argparse details.

        Args:
            node: The LibCST Call node being visited.
        """
        if (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "add_parser"
        ):
            if node.args and isinstance(node.args[0].value, cst.SimpleString):
                op_id = str(node.args[0].value.evaluated_value)
                self._select_operation(op_id)

                if self.current_op:
                    for arg in node.args:
                        if getattr(arg.keyword, "value", None) == "help" and isinstance(
                            arg.value, cst.SimpleString
                        ):
                            self.current_op.summary = str(arg.value.evaluated_value)

        elif (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "add_argument"
            and self.current_op
            and node.args
            and isinstance(node.args[0].value, cst.SimpleString)
        ):
            arg_name = str(node.args[0].value.evaluated_value)
            if arg_name.startswith("--"):
                p_name = arg_name[2:]

                p_desc = ""
                p_req = False
                p_schema_type = "string"
                for arg in node.args:
                    kw_name = getattr(arg.keyword, "value", None)
                    if kw_name == "help" and isinstance(arg.value, cst.SimpleString):
                        p_desc = str(arg.value.evaluated_value)
                    elif kw_name == "required" and isinstance(arg.value, cst.Name):
                        p_req = arg.value.value == "True"
                    elif kw_name == "type" and isinstance(arg.value, cst.Name):
                        p_schema_type = _PY_TYPE_TO_OPENAPI.get(
                            arg.value.value, "string"
                        )
                    elif (
                        kw_name == "action"
                        and isinstance(arg.value, cst.SimpleString)
                        and str(arg.value.evaluated_value)
                        in ("store_true", "store_false")
                    ):
                        p_schema_type = "boolean"

                if p_name == "body" and self._standalone:
                    self.current_op.requestBody = RequestBody(
                        description=p_desc or None,
                        required=p_req or None,
                        content={
                            "application/json": MediaType(schema=Schema(type="object"))
                        },
                    )
                    return

                matched = False
                if self.current_op.parameters:
                    for p in self.current_op.parameters:
                        if getattr(p, "name", "").replace("-", "_") == p_name:
                            p.description = p_desc
                            matched = True
                if not matched and self._standalone:
                    if self.current_op.parameters is None:
                        self.current_op.parameters = []
                    self.current_op.parameters.append(
                        Parameter(
                            name=p_name,
                            description=p_desc or None,
                            required=p_req or None,
                            **{
                                "in": "query",
                                "schema": Schema(type=p_schema_type),
                            },
                        )
                    )


def extract_cli_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract CLI information from an AST module into an OpenAPI spec.

    Args:
        module: The parsed LibCST Module node.
        spec: The OpenAPI specification to update.
    """
    extractor = CLIExtractor(spec)
    module.visit(extractor)
