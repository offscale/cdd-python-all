"""Module for extracting OpenAPI elements from pytest test cases."""

from __future__ import annotations

import libcst as cst

from openapi_client.models import MediaType, OpenAPI, Operation, PathItem, Response
from openapi_client.openapi.keywords import HTTP_METHODS


class SSEChecker(cst.CSTVisitor):
    """Visitor to check for SSE (`text/event-stream`) media types inside a test function."""

    def __init__(self) -> None:
        """Initialize SSEChecker."""
        self.found: bool = False

    def visit_SimpleString(self, node: cst.SimpleString) -> None:
        """Visit strings to check for `text/event-stream` media type.

        Args:
            node: The LibCST SimpleString node being visited.
        """
        if "text/event-stream" in node.value:
            self.found = True


class ASTTestExtractor(cst.CSTVisitor):
    """AST Visitor to extract test methods into OpenAPI operations and SSE responses."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize ASTTestExtractor with an OpenAPI spec.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Extract SSE response media types from stream/sse test functions.

        Args:
            node: The LibCST FunctionDef node being visited.
        """
        name = node.name.value
        if "stream" in name.lower() or "sse" in name.lower():
            checker = SSEChecker()
            node.visit(checker)
            if checker.found:
                op_id = name.removeprefix("test_")
                if self.spec.paths is None:
                    self.spec.paths = {}
                matched_op: Operation | None = None
                for path_item in self.spec.paths.values():
                    for method in HTTP_METHODS:
                        op = getattr(path_item, method, None)
                        if op and op.operationId == op_id:
                            matched_op = op
                            break
                if matched_op is None:
                    route_path = f"/{op_id}"
                    path_item = self.spec.paths.setdefault(route_path, PathItem())
                    matched_op = Operation(operationId=op_id)
                    path_item.get = matched_op
                matched_op.responses = {
                    "200": Response(
                        description="Server-sent events stream",
                        content={"text/event-stream": MediaType()},
                    )
                }


def extract_tests_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract API test cases from a parsed module into an OpenAPI specification.

    Args:
        module: Parsed Python module.
        spec: OpenAPI specification to update.
    """
    visitor = ASTTestExtractor(spec)
    module.visit(visitor)
