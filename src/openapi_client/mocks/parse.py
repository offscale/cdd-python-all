"""Module for extracting OpenAPI Operations from FastAPI mock server ASTs."""

from __future__ import annotations

import libcst as cst

from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import MediaType, OpenAPI, Operation, PathItem, Response


class ReturnExtractor(cst.CSTVisitor):
    """Visitor to find event stream responses in function bodies."""

    def __init__(self) -> None:
        """Initialize ReturnExtractor."""
        self.has_event_stream: bool = False

    def visit_Return(self, node: cst.Return) -> None:
        """Check if the return statement returns an EventSourceResponse.

        Args:
            node: The LibCST Return node being visited.
        """
        if isinstance(node.value, cst.Call):
            if isinstance(node.value.func, cst.Name):
                if node.value.func.value == "EventSourceResponse":
                    self.has_event_stream = True


class MockServerExtractor(cst.CSTVisitor):
    """AST Visitor to extract mock server routes into OpenAPI Path/Operation structures."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize MockServerExtractor with an OpenAPI spec.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec
        if not self.spec.paths:
            self.spec.paths = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Extract operation based on FastAPI decorator (e.g., `@app.get("/pets")`).

        Args:
            node: The LibCST FunctionDef node being visited.
        """
        name = node.name.value

        if node.decorators:
            for decorator in node.decorators:
                if isinstance(decorator.decorator, cst.Call):
                    call = decorator.decorator
                    if isinstance(call.func, cst.Attribute) and isinstance(
                        call.func.value, cst.Name
                    ):
                        if call.func.value.value == "app":
                            method = call.func.attr.value
                            if method in ["get", "post", "put", "delete", "patch"]:
                                if call.args and isinstance(
                                    call.args[0].value, cst.SimpleString
                                ):
                                    path = str(call.args[0].value.evaluated_value)

                                    if (
                                        self.spec.paths is not None
                                        and path not in self.spec.paths
                                    ):
                                        self.spec.paths[path] = PathItem()

                                    summary, description = parse_docstring(node)

                                    operation = Operation(operationId=name)
                                    if summary:
                                        operation.summary = summary
                                    if description:
                                        operation.description = description

                                    ret_extractor = ReturnExtractor()
                                    node.visit(ret_extractor)
                                    if ret_extractor.has_event_stream:
                                        operation.responses = {
                                            "200": Response(
                                                description="Server-sent events stream",
                                                content={
                                                    "text/event-stream": MediaType()
                                                },
                                            )
                                        }

                                    if self.spec.paths is not None:
                                        setattr(
                                            self.spec.paths[path],
                                            method,
                                            operation,
                                        )


def extract_mocks_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract API operations from a parsed mock module into an OpenAPI specification.

    Args:
        module: Parsed Python module.
        spec: OpenAPI specification to update.
    """
    visitor = MockServerExtractor(spec)
    module.visit(visitor)
