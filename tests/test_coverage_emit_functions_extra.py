from openapi_client.models import (
    Operation,
    Parameter,
    Schema,
    OpenAPI,
    Components,
    Reference,
)
from openapi_client.functions.emit import emit_function
from openapi_client.tests.emit import (
    get_dummy_value_for_schema,
    get_stub_body,
    emit_operation_test,
)


def test_emit_function_formData_and_no_path_vars():
    # Test path without "{}"
    path = "/no/vars/here"
    method = "post"

    # Test param with in="formData"
    param = Parameter(
        name="my_form_param",
        in_="formData",
        required=True,
        schema=Schema(type="string"),
    )

    op = Operation(operationId="test_formData_op", parameters=[param])

    func_node = emit_function(method, path, op)
    assert func_node is not None
    assert func_node.name.value == "test_formData_op"


def test_get_dummy_value_for_file():
    schema = Schema(type="file")
    val = get_dummy_value_for_schema(schema)
    assert val.value == 'b"dummy_content"'


def test_get_stub_body_ref():
    ref_schema = Reference(ref="#/components/schemas/Target")
    target_schema = Schema(
        type="object", properties={"some_prop": Schema(type="string")}
    )
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={},
        components=Components(schemas={"Target": target_schema}),
    )
    val = get_stub_body(ref_schema, spec)
    assert val is not None


def test_get_stub_body_prop_ref():
    ref_schema = Reference(ref="#/components/schemas/Target")
    target_schema = Schema(
        type="object", properties={"some_prop": Schema(type="string")}
    )
    main_schema = Schema(
        type="object",
        properties={
            "my_ref": ref_schema,
            "my_obj": Schema(
                type="object", properties={"inner": Schema(type="string")}
            ),
        },
    )
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={},
        components=Components(schemas={"Target": target_schema}),
    )
    val = get_stub_body(main_schema, spec)
    assert val is not None


def test_emit_operation_test_param_no_schema():
    param = Parameter(name="p", in_="query", type="string")
    op = Operation(operationId="test_param_type", parameters=[param])
    node = emit_operation_test("get", "/test", op)
    assert node is not None


def test_emit_function_with_path_vars():
    path = "/users/{id}"
    method = "get"

    op = Operation(operationId="get_user", parameters=[])

    func_node = emit_function(method, path, op)
    assert func_node is not None
    assert func_node.name.value == "get_user"
