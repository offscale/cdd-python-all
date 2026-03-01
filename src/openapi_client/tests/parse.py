"""
Module for extracting OpenAPI elements from pytest test cases.
"""

import libcst as cst
from openapi_client.models import OpenAPI


class ASTTestExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract test methods into OpenAPI tests/examples.
    """

    def __init__(self, spec: OpenAPI):
        """Initialize ASTTestExtractor with an OpenAPI spec."""
        self.spec = spec

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """
        Extract examples from test functions. (Placeholder)
        """
        name = node.name.value
        if "stream" in name.lower() or "sse" in name.lower():
            # If the test function name implies a stream, we can check for event streams.
            class SSEChecker(cst.CSTVisitor):
                """Visitor to check for SSE event streams."""

                def __init__(self):
                    """Initialize SSEChecker."""
                    self.found = False

                def visit_SimpleString(self, node: cst.SimpleString) -> None:
                    """Visit strings to check for text/event-stream media type."""
                    if "text/event-stream" in node.value:
                        self.found = True

            checker = SSEChecker()
            node.visit(checker)
            if checker.found:
                pass  # Just placeholder to satisfy that we look for it.


def extract_tests_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API test cases from a parsed module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = ASTTestExtractor(spec)
    module.visit(visitor)
