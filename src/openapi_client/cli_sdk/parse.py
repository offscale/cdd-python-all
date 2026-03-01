"""Module for parsing an existing CLI application and updating an OpenAPI specification."""

import libcst as cst
from openapi_client.models import OpenAPI, Operation, Parameter, Schema


class CLIExtractor(cst.CSTVisitor):
    """Visitor for extracting CLI arguments into an OpenAPI spec."""

    def __init__(self, spec: OpenAPI):
        """Initialize the extractor."""
        self.spec = spec
        self.current_op_id = None
        self.current_op = None

    def visit_Call(self, node: cst.Call):
        """Visit call nodes to extract argparse details."""
        if (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "add_parser"
        ):
            if node.args and isinstance(node.args[0].value, cst.SimpleString):
                op_id = node.args[0].value.value.strip("\"'")
                self.current_op_id = op_id

                # Try to find an existing operation in spec, or create a mock one
                # Actually mapping op_id back to path/method is hard without prior knowledge,
                # but we can try to guess or just let it update existing ones.
                found = False
                if self.spec.paths:
                    for path, path_item in self.spec.paths.items():
                        for method in ["get", "post", "put", "delete", "patch"]:
                            op = getattr(path_item, method, None)
                            if op and op.operationId == op_id:
                                self.current_op = op
                                found = True
                                break
                        if found:
                            break

                if self.current_op:
                    for arg in node.args:
                        if getattr(arg.keyword, "value", None) == "help" and isinstance(
                            arg.value, cst.SimpleString
                        ):
                            self.current_op.summary = arg.value.value.strip("\"'")

        elif (
            isinstance(node.func, cst.Attribute)
            and node.func.attr.value == "add_argument"
        ):
            if (
                self.current_op
                and node.args
                and isinstance(node.args[0].value, cst.SimpleString)
            ):
                arg_name = node.args[0].value.value.strip("\"'")
                if arg_name.startswith("--"):
                    p_name = arg_name[2:]

                    p_desc = ""
                    for arg in node.args:
                        if getattr(arg.keyword, "value", None) == "help" and isinstance(
                            arg.value, cst.SimpleString
                        ):
                            p_desc = arg.value.value.strip("\"'")

                    # Update parameter description
                    if self.current_op.parameters:
                        for p in self.current_op.parameters:
                            if getattr(p, "name", "").replace("-", "_") == p_name:
                                p.description = p_desc


def extract_cli_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract CLI information from an AST module into an OpenAPI spec."""
    extractor = CLIExtractor(spec)
    module.visit(extractor)
