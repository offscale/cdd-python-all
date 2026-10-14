"""Parse FastAPI code into an OpenAPI specification."""

from __future__ import annotations

import libcst as cst

from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import OpenAPI, Operation, PathItem, Response


class FastAPIExtractor(cst.CSTVisitor):
    """Visitor for extracting FastAPI routes into an OpenAPI spec."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize the extractor.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Visit function definitions to extract decorated FastAPI routes.

        Args:
            node: The LibCST FunctionDef node being visited.
        """
        for decorator in node.decorators:
            if isinstance(decorator.decorator, cst.Call):
                if isinstance(decorator.decorator.func, cst.Attribute):
                    if isinstance(
                        decorator.decorator.func.value, cst.Name
                    ) and decorator.decorator.func.value.value in ("app", "router"):
                        method = decorator.decorator.func.attr.value
                        if method in ["get", "post", "put", "delete", "patch"]:
                            if decorator.decorator.args and isinstance(
                                decorator.decorator.args[0].value, cst.SimpleString
                            ):
                                path = decorator.decorator.args[0].value.value.strip(
                                    "\"'"
                                )

                                if not self.spec.paths:
                                    self.spec.paths = {}
                                if path not in self.spec.paths:
                                    self.spec.paths[path] = PathItem()

                                summary, description = parse_docstring(node)
                                op = Operation(
                                    operationId=node.name.value,
                                    summary=summary,
                                    description=description,
                                    responses={
                                        "200": Response(
                                            description="Successful Response"
                                        )
                                    },
                                )
                                setattr(self.spec.paths[path], method, op)


def extract_fastapi_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract FastAPI information from an AST module into an OpenAPI spec.

    Args:
        module: The parsed LibCST Module node.
        spec: The OpenAPI specification to update.
    """
    extractor = FastAPIExtractor(spec)
    module.visit(extractor)
