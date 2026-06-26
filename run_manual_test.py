"""Manual test script for AST test extraction."""

import libcst as cst
from openapi_client.tests.parse import ASTTestExtractor
from openapi_client.models import OpenAPI

spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0.0"})

code = """
def test_stream_something():
    response = "text/event-stream"

def test_stream_but_no_event_stream():
    response = "application/json"

def test_normal_function():
    pass
"""
module = cst.parse_module(code)
visitor = ASTTestExtractor(spec)
module.visit(visitor)
