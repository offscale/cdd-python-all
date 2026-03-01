import pytest
import libcst as cst
from openapi_client.models import OpenAPI, Operation, Parameter, Schema
from openapi_client.functions.emit import emit_function
from openapi_client.mocks.parse import MockServerExtractor
from openapi_client.tests.parse import ASTTestExtractor


def test_emit_complex_query_parameter():
    # spaceDelimited, pipeDelimited
    op = Operation(
        operationId="get_things",
        parameters=[
            Parameter(
                name="things",
                **{"in": "query"},
                style="spaceDelimited",
                schema=Schema(type="array", items=Schema(type="string")),
            ),
            Parameter(
                name="others",
                **{"in": "query"},
                style="pipeDelimited",
                schema=Schema(type="array", items=Schema(type="string")),
            ),
        ],
    )
    node = emit_function("get", "/things", op)
    code = cst.Module(body=[node]).code
    assert "things" in code
    assert "List[str]" in code
    assert "spaceDelimited" in code or "' '" in code
    assert "pipeDelimited" in code or "'|'" in code


def test_mock_streaming_extraction():
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = MockServerExtractor(spec)
    module = cst.parse_module(
        "@app.get('/stream')\ndef my_stream():\n    return EventSourceResponse()\n"
    )
    module.visit(extractor)
    op = spec.paths["/stream"].get
    assert op.responses is not None
    assert "text/event-stream" in op.responses["200"].content
