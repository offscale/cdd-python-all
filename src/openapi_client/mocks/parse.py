"""
Module for extracting OpenAPI Operations from FastAPI mock server ASTs.
"""

import libcst as cst
from openapi_client.models import OpenAPI, PathItem, Operation


class MockServerExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract mock server routes into OpenAPI Path/Operation structures.
    """

    def __init__(self, spec: OpenAPI):
        """Initialize MockServerExtractor with an OpenAPI spec."""
        self.spec = spec
        if not self.spec.paths:
            self.spec.paths = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """
        Extract operation based on FastAPI decorator (e.g., @app.get("/pets")).
        """
        name = node.name.value

        # Look for decorators like @app.get("/pets")
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
                                    path = call.args[0].value.evaluated_value

                                    if (
                                        self.spec.paths is not None
                                        and str(path) not in self.spec.paths
                                    ):
                                        self.spec.paths[str(path)] = PathItem(**{})  # type: ignore[call-arg]

                                    # Extract docstrings
                                    from openapi_client.docstrings.parse import (
                                        parse_docstring,
                                    )

                                    summary, description = parse_docstring(node)

                                    operation = Operation(operationId=name)
                                    if summary:
                                        operation.summary = summary
                                    if description:
                                        operation.description = description

                                    # Extract responses
                                    class ReturnExtractor(cst.CSTVisitor):
                                        """Visitor to find event stream responses."""

                                        def __init__(self):
                                            """Initialize ReturnExtractor."""
                                            self.has_event_stream = False

                                        def visit_Return(
                                            self, node: cst.Return
                                        ) -> None:
                                            """Check if the return is EventSourceResponse."""
                                            if isinstance(node.value, cst.Call):
                                                if isinstance(
                                                    node.value.func, cst.Name
                                                ):
                                                    if (
                                                        node.value.func.value
                                                        == "EventSourceResponse"
                                                    ):
                                                        self.has_event_stream = True

                                    ret_extractor = ReturnExtractor()
                                    node.visit(ret_extractor)
                                    if ret_extractor.has_event_stream:
                                        from openapi_client.models import (
                                            Response,
                                            MediaType,
                                        )

                                        operation.responses = {
                                            "200": Response(
                                                description="Server-sent events stream",
                                                content={
                                                    "text/event-stream": MediaType(**{})
                                                },
                                            )
                                        }

                                    if self.spec.paths is not None:
                                        setattr(
                                            self.spec.paths[str(path)],
                                            method,
                                            operation,
                                        )


def extract_mocks_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API operations from a parsed mock module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = MockServerExtractor(spec)
    module.visit(visitor)
