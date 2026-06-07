"""Tests for test_coverage_parse_tests.py."""


def test_parse_tests_coverage():
    """Test test_parse_tests_coverage."""
    from openapi_client.tests.parse import extract_tests_from_ast
    from openapi_client.models import OpenAPI
    import libcst as cst

    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0.0"})

    code = '''
def test_stream_something():
    """Test stream something."""
    response = "text/event-stream"

def test_stream_but_no_event_stream():
    """Test stream but no event stream."""
    response = "application/json"

def test_normal_function():
    pass
'''
    module = cst.parse_module(code)
    extract_tests_from_ast(module, spec)
