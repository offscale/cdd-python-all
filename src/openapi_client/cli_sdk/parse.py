"""Module for parsing an existing CLI application and updating an OpenAPI specification."""

from __future__ import annotations

import libcst as cst

from openapi_client.models import OpenAPI, Operation


class CLIExtractor(cst.CSTVisitor):
    """Visitor for extracting CLI arguments into an OpenAPI spec."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize the extractor.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec
        self.current_op_id: str | None = None
        self.current_op: Operation | None = None

    def _select_operation(self, op_id: str) -> None:
        """Set `self.current_op` by matching `op_id` across `self.spec.paths`.

        Args:
            op_id: Target operation identifier.
        """
        self.current_op_id = op_id
        self.current_op = None
        if self.spec.paths:
            for path_item in self.spec.paths.values():
                for method in ["get", "post", "put", "delete", "patch"]:
                    op = getattr(path_item, method, None)
                    if op and op.operationId == op_id:
                        self.current_op = op
                        return

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
                for arg in node.args:
                    if getattr(arg.keyword, "value", None) == "help" and isinstance(
                        arg.value, cst.SimpleString
                    ):
                        p_desc = str(arg.value.evaluated_value)

                if self.current_op.parameters:
                    for p in self.current_op.parameters:
                        if getattr(p, "name", "").replace("-", "_") == p_name:
                            p.description = p_desc


def extract_cli_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract CLI information from an AST module into an OpenAPI spec.

    Args:
        module: The parsed LibCST Module node.
        spec: The OpenAPI specification to update.
    """
    extractor = CLIExtractor(spec)
    module.visit(extractor)
