import libcst as cst
from openapi_client.models import OpenAPI, Operation, Parameter, Schema
from openapi_client.functions.emit import emit_function
from openapi_client.mocks.parse import MockServerExtractor


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
    assert "list[str]" in code
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


def test_parse_sqlalchemy_cdd():
    from openapi_client.sqlalchemy_cdd.parse import parse_sqlalchemy_cdd
    from openapi_client.models import OpenAPI
    import libcst as cst

    parse_sqlalchemy_cdd(
        cst.parse_module(""),
        OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"}),
    )


def test_parse_cli_sdk_cdd():
    from openapi_client.cli_sdk_cdd.parse import parse_cli_sdk_cdd
    from openapi_client.models import OpenAPI
    import libcst as cst

    parse_cli_sdk_cdd(
        cst.parse_module(""),
        OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"}),
    )


def test_emit_function_requestBody():
    from openapi_client.models import Operation, RequestBody
    from openapi_client.functions.emit import emit_function

    op = Operation(
        operationId="post_things",
        requestBody=RequestBody(content={}),
    )
    node = emit_function("post", "/things", op)
    assert "body" in str(node)


def test_emit_tests():
    from openapi_client.models import (
        OpenAPI,
        Operation,
        RequestBody,
        Schema,
        PathItem,
        Parameter,
    )
    from openapi_client.tests.emit import emit_tests

    op = Operation(
        operationId="post_things",
        requestBody=RequestBody(
            content={
                "application/json": {
                    "schema": Schema(
                        type="object",
                        properties={
                            "name": Schema(type="str"),
                            "photoUrls": Schema(type="list[str]"),
                            "other": Schema(type="str"),
                        },
                    )
                }
            }
        ),
        parameters=[
            Parameter(name="status", in_="query", schema=Schema(type="string")),
            Parameter(name="petId", in_="path", schema=Schema(type="integer")),
            Parameter(name="other", in_="query", schema=Schema(type="float")),
        ],
    )
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={
            "/things": PathItem(post=op),
            "/inventory": PathItem(get=Operation(operationId="get_inv")),
        },
    )
    module = emit_tests(spec, composable=True)
    assert "post_things" in str(module.code)

    module = emit_tests(spec, composable=False)
    assert "post_things" in str(module.code)


def test_get_dummy_value_for_schema():
    from openapi_client.tests.emit import get_dummy_value_for_schema
    from openapi_client.models import Schema

    assert "test_string" in str(get_dummy_value_for_schema(Schema(type="string")))
    assert "1" in str(get_dummy_value_for_schema(Schema(type="integer")))
    assert "1.0" in str(get_dummy_value_for_schema(Schema(type="number")))
    assert "True" in str(get_dummy_value_for_schema(Schema(type="boolean")))
    assert "test_string" in str(
        get_dummy_value_for_schema(Schema(type="array", items=Schema(type="string")))
    )
    assert "1" in str(
        get_dummy_value_for_schema(Schema(type="array", items=Schema(type="integer")))
    )
    assert "List(" in str(
        get_dummy_value_for_schema(Schema(type="array", items=Schema(type="number")))
    )
    assert "Dict(" in str(get_dummy_value_for_schema(Schema(type="object")))
    assert "None" in str(get_dummy_value_for_schema(Schema(type="unknown")))


def test_emit_tests_more():
    from openapi_client.models import (
        OpenAPI,
        Operation,
        RequestBody,
        Schema,
        PathItem,
        Parameter,
    )
    from openapi_client.tests.emit import emit_tests

    # array payload
    op1 = Operation(
        operationId="post_things_array",
        requestBody=RequestBody(
            content={
                "application/json": {
                    "schema": Schema(type="array", items=Schema(type="string"))
                }
            }
        ),
    )

    # get findByStatus
    op2 = Operation(
        operationId="find_by_status",
        requestBody=RequestBody(
            content={"application/xml": {"schema": Schema(type="object")}}
        ),
        parameters=[Parameter(name="petId", in_="path", schema=Schema(type="integer"))],
    )

    # requestBody with content no application/json or xml
    op3 = Operation(
        operationId="post_other",
        requestBody=RequestBody(
            content={"text/plain": {"schema": Schema(type="string")}}
        ),
    )

    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={
            "/things": PathItem(post=op1),
            "/findByStatus": PathItem(get=op2),
            "/other": PathItem(post=op3),
        },
    )
    emit_tests(spec, composable=True)
    emit_tests(spec, composable=False)


def test_emit_tests_exception():
    from openapi_client.models import OpenAPI, Operation, RequestBody, PathItem
    from openapi_client.tests.emit import emit_tests

    # Bypass pydantic validation to force an exception in the try block
    class Bad:
        def __bool__(self):
            return True

    rb = RequestBody.model_construct(content=Bad())
    op = Operation(operationId="err", requestBody=rb)

    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={"/err": PathItem(post=op)},
    )
    emit_tests(spec)
