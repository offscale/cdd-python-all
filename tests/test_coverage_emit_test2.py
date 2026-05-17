def test_emit_tests_other_param_exception_real():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, Parameter

    op = Operation(
        operationId="test_other_param_exception",
        parameters=[Parameter(name="other_param_3", in_="query")],
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_other_param_exception"


def test_emit_tests_body_param_exception_real():
    from openapi_client.tests.emit import emit_operation_test
    from openapi_client.models import Operation, Parameter

    op = Operation(
        operationId="test_body_param_exception_real",
        parameters=[Parameter(name="body_param_real", in_="body")],
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_body_param_exception_real"
