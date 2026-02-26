"""
Module for extracting OpenAPI Operations from Python method ASTs.
"""

import libcst as cst
from openapi_client.models import OpenAPI, PathItem, Operation


class FunctionExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract method definitions into OpenAPI Path/Operation structures.
    """

    def __init__(self, spec: OpenAPI):
        self.spec = spec
        if not self.spec.paths:
            self.spec.paths = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """
        Extract operation based on function name convention (e.g., get_pets -> GET /pets).
        """
        name = node.name.value
        # Simple heuristic: split by first underscore
        if "_" in name:
            parts = name.split("_", 1)
            method = parts[0].lower()
            if method in ["get", "post", "put", "delete", "patch"]:
                path = "/" + parts[1].replace("_", "/")

                if self.spec.paths is not None and path not in self.spec.paths:
                    self.spec.paths[path] = PathItem(**{})  # type: ignore[call-arg]

                from openapi_client.docstrings.parse import parse_docstring

                summary, description = parse_docstring(node)

                operation = Operation(operationId=name)
                if summary:
                    operation.summary = summary
                if description:
                    operation.description = description

                if self.spec.paths is not None:
                    setattr(self.spec.paths[path], method, operation)


def extract_functions_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API operations from a parsed module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = FunctionExtractor(spec)
    module.visit(visitor)
