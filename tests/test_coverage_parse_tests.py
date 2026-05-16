def test_parse_tests_coverage():
    from openapi_client.tests.parse import ASTTestExtractor, extract_tests_from_ast
    from openapi_client.models import OpenAPI
    import libcst as cst

    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0.0"})
    
    code = """
def test_stream_something():
    response = "text/event-stream"
"""
    module = cst.parse_module(code)
    extract_tests_from_ast(module, spec)
