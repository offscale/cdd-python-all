def test_emit_tests_xml_array():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, RequestBody, MediaType, Schema

    op = Operation(
        operationId="test_xml",
        requestBody=RequestBody(
            content={"application/xml": MediaType(schema_=Schema(type="array", items=Schema(type="string")))}
        )
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_xml"

def test_emit_tests_empty_content():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, RequestBody

    op = Operation(
        operationId="test_empty",
        requestBody=RequestBody(content={})
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_empty"

def test_emit_tests_other_content():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, RequestBody, MediaType, Schema

    op = Operation(
        operationId="test_other",
        requestBody=RequestBody(
            content={"text/plain": MediaType(schema_=Schema(type="string"))}
        )
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_other"


def test_get_stub_body_array_of_objects():
    from openapi_client.tests.emit import get_stub_body
    from openapi_client.models import Schema

    schema = Schema(
        type="array",
        items=Schema(
            type="object",
            properties={
                "id": Schema(type="integer")
            }
        )
    )
    val = get_stub_body(schema)
    assert len(val.elements) == 1
    assert val.elements[0].value.elements[0].key.value == '"id"'

def test_emit_tests_exception_content():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, RequestBody

    class BadDict(dict):
        def keys(self):
            raise Exception("Mock error")

    op = Operation(
        operationId="test_exception",
        requestBody=RequestBody(content=BadDict())
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_exception"


def test_emit_tests_body_param_exception():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, Parameter

    class BadParameter(Parameter):
        @property
        def schema_(self):
            raise Exception("Mock error")
        @property
        def schema(self):
            raise Exception("Mock error")

    op = Operation(
        operationId="test_body_param_exception",
        parameters=[BadParameter(name="body_param", in_="body")]
    )
    try:
        func = emit_operation_test("post", "/test", op)
    except Exception:
        pass

def test_emit_tests_other_param():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, Parameter, Schema

    op = Operation(
        operationId="test_other_param",
        parameters=[Parameter(name="other_param", in_="query", schema_=Schema(type="string"))]
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_other_param"


def test_emit_tests_request_body_exception():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, RequestBody

    class BadRequestBody(RequestBody):
        @property
        def content(self):
            raise Exception("Mock error")

    op = Operation(
        operationId="test_request_body_exception",
        requestBody=BadRequestBody()
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_request_body_exception"


def test_emit_tests_body_param_exception_schema():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, Parameter

    class BadParameter2(Parameter):
        @property
        def schema(self):
            raise Exception("Mock error")

    op = Operation(
        operationId="test_body_param_exception_2",
        parameters=[BadParameter2(name="body_param_2", in_="body")]
    )
    try:
        func = emit_operation_test("post", "/test", op)
    except Exception:
        pass

def test_emit_tests_other_param_exception():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, Parameter

    class BadParameter3(Parameter):
        @property
        def schema(self):
            raise Exception("Mock error")
            
        @property
        def schema_(self):
            raise Exception("Mock error")

    op = Operation(
        operationId="test_other_param_exception",
        parameters=[BadParameter3(name="other_param_3", in_="query")]
    )
    try:
        func = emit_operation_test("post", "/test", op)
    except Exception:
        pass

