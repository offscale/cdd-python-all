"""Tests for client test emission, server test emission, and test AST parsing."""

from __future__ import annotations

import libcst as cst
import pytest
from openapi_client.functions.emit import emit_function
from openapi_client.mocks.parse import MockServerExtractor
from openapi_client.models import (
    Components,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    Schema,
)
from openapi_client.tests.emit import emit_tests
from openapi_client.tests.emit_server_tests import emit_server_tests


def test_emit_server_tests_empty() -> None:
    """Test emit_server_tests with empty spec."""
    spec = OpenAPI(info={"title": "Test", "version": "1.0"}, openapi="3.2.0")
    assert emit_server_tests(spec) == {}


def test_emit_server_tests_with_models() -> None:
    """Test emit_server_tests with models."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "User": Schema(type="object", properties={}),
            }
        ),
        paths={"/users": PathItem(get=Operation(operationId="get_users"))},
    )
    code = emit_server_tests(spec)

    assert "def test_db_config_ephemeral():" in code["test_unit.py"]
    assert "def test_dao_factory_stub():" in code["test_unit.py"]
    assert "def test_dao_factory_concrete():" in code["test_unit.py"]
    assert "def test_seeder_referential_integrity():" in code["test_unit.py"]
    assert "test_stub.py" in code
    assert "client.get('/users')" in code["test_stub.py"]
    assert "def test_ephemeral_clean_state(ephemeral_client):" in code["test_ephemeral.py"]
    assert "def test_seeded_state(seeded_client):" in code["test_seeded.py"]
    assert "def test_cors_preflight():" in code["test_advanced.py"]
    assert "def test_strict_validation_mock():" in code["test_advanced.py"]
    assert "def test_auth_enforcement_mock():" in code["test_advanced.py"]
    assert "def test_trigger_webhook():" in code["test_advanced.py"]
    assert "def test_auth_endpoints_mock():" in code["test_advanced.py"]


def test_emit_server_tests_no_paths() -> None:
    """Test emit_server_tests with models but no paths."""
    spec = OpenAPI(
        info={"title": "Test", "version": "1.0"},
        openapi="3.2.0",
        components=Components(
            schemas={
                "User": Schema(type="object", properties={}),
            }
        ),
    )
    code = emit_server_tests(spec)

    assert "test_stub.py" in code
    assert "pass # No GET endpoints found in spec" in code["test_stub.py"]


def test_emit_tests_xml_array() -> None:
    """Test test_emit_tests_xml_array."""
    from openapi_client.models import MediaType, Operation, RequestBody, Schema
    from openapi_client.tests.emit import emit_operation_test

    op = Operation(
        operationId="test_xml",
        requestBody=RequestBody(
            content={"application/xml": MediaType(schema_=Schema(type="array", items=Schema(type="string")))}
        ),
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_xml"


def test_emit_tests_empty_content() -> None:
    """Test test_emit_tests_empty_content."""
    from openapi_client.models import Operation, RequestBody
    from openapi_client.tests.emit import emit_operation_test

    op = Operation(operationId="test_empty", requestBody=RequestBody(content={}))
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_empty"


def test_emit_tests_other_content() -> None:
    """Test test_emit_tests_other_content."""
    from openapi_client.models import MediaType, Operation, RequestBody, Schema
    from openapi_client.tests.emit import emit_operation_test

    op = Operation(
        operationId="test_other",
        requestBody=RequestBody(content={"text/plain": MediaType(schema_=Schema(type="string"))}),
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_other"


def test_get_stub_body_array_of_objects() -> None:
    """Test test_get_stub_body_array_of_objects."""
    from openapi_client.models import Schema
    from openapi_client.tests.emit import get_stub_body

    schema = Schema(
        type="array",
        items=Schema(type="object", properties={"id": Schema(type="integer")}),
    )
    val = get_stub_body(schema)
    assert isinstance(val, cst.List)
    assert len(val.elements) == 1
    first_dict = val.elements[0].value
    assert isinstance(first_dict, cst.Dict)
    first_el = first_dict.elements[0]
    assert isinstance(first_el, cst.DictElement)
    assert getattr(first_el.key, "value", None) == '"id"'


def test_emit_tests_exception_content() -> None:
    """Test test_emit_tests_exception_content."""
    from typing import Any

    from openapi_client.models import Operation, RequestBody
    from openapi_client.tests.emit import emit_operation_test

    class BadDict:
        """Test BadDict."""

        def __contains__(self, item: object) -> bool:
            """Test __contains__.

            Args:
                item: Key to check.
            """
            raise RuntimeError("Mock error")

    bad_content: Any = BadDict()
    op = Operation.model_construct(
        operationId="test_exception",
        requestBody=RequestBody.model_construct(content=bad_content),
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_exception"


def test_emit_tests_body_param_exception() -> None:
    """Test test_emit_tests_body_param_exception."""
    from typing import Any

    from openapi_client.models import Operation
    from openapi_client.tests.emit import emit_operation_test

    class BadParameter:
        """Test BadParameter."""

        name = "body_param"
        in_ = "body"

        @property
        def schema_(self) -> None:
            """Test schema_."""
            raise RuntimeError("Mock error")

    bad_params: Any = [BadParameter()]
    op = Operation.model_construct(operationId="test_body_param_exception", parameters=bad_params)
    with pytest.raises(RuntimeError, match="Mock error"):
        emit_operation_test("post", "/test", op)


def test_emit_tests_other_param() -> None:
    """Test test_emit_tests_other_param."""
    from openapi_client.models import Operation, Parameter, Schema
    from openapi_client.tests.emit import emit_operation_test

    op = Operation(
        operationId="test_other_param",
        parameters=[Parameter(name="other_param", in_="query", schema_=Schema(type="string"))],
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_other_param"


def test_emit_tests_request_body_reference() -> None:
    """Test emit_operation_test when requestBody is a Reference without content."""
    from openapi_client.models import Operation, Reference
    from openapi_client.tests.emit import emit_operation_test

    op = Operation.model_construct(
        operationId="test_request_body_reference",
        requestBody=Reference(**{"$ref": "#/components/requestBodies/MyBody"}),
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_request_body_reference"


def test_emit_tests_other_param_exception() -> None:
    """Test test_emit_tests_other_param_exception."""
    from typing import Any

    from openapi_client.models import Operation
    from openapi_client.tests.emit import emit_operation_test

    class BadParameter3:
        """Test BadParameter3."""

        name = "other_param_3"
        in_ = "query"

        @property
        def schema_(self) -> None:
            """Test schema_."""
            raise RuntimeError("Mock error")

    bad_params: Any = [BadParameter3()]
    op = Operation.model_construct(operationId="test_other_param_exception", parameters=bad_params)
    with pytest.raises(RuntimeError, match="Mock error"):
        emit_operation_test("post", "/test", op)


def test_emit_tests_other_param_exception_real() -> None:
    """Test test_emit_tests_other_param_exception_real."""
    from openapi_client.models import Operation, Parameter
    from openapi_client.tests.emit import emit_operation_test

    op = Operation(
        operationId="test_other_param_exception",
        parameters=[Parameter(name="other_param_3", in_="query")],
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_other_param_exception"


def test_emit_tests_body_param_exception_real() -> None:
    """Test test_emit_tests_body_param_exception_real."""
    from openapi_client.models import Operation, Parameter
    from openapi_client.tests.emit import emit_operation_test

    op = Operation(
        operationId="test_body_param_exception_real",
        parameters=[Parameter(name="body_param_real", in_="body")],
    )
    func = emit_operation_test("post", "/test", op)
    assert func.name.value == "test_test_body_param_exception_real"


def test_coverage_emit_branches_4() -> None:
    """Test emit_tests with Reference parameters and non-slash path keys."""
    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "Test", "version": "1.0.0"},
        paths={
            "/good": PathItem(
                get=Operation(
                    operationId="get_good",
                    responses={"200": {"description": "ok"}},
                    parameters=[
                        Parameter(name="status", in_="query", schema_={"type": "string"}),
                        Reference(ref="#/components/parameters/mock"),
                    ],
                )
            ),
            "bad_path": PathItem(get=Operation(operationId="get_bad", responses={"200": {"description": "ok"}})),
        },
    )

    mod = emit_tests(spec)
    assert "def test_get_good" in mod.code
    assert "test_get_bad" not in mod.code


def test_parse_tests_coverage() -> None:
    """Test test_parse_tests_coverage."""
    import libcst as cst
    from openapi_client.models import OpenAPI
    from openapi_client.tests.parse import extract_tests_from_ast

    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0.0"})

    code = '''
def test_stream_something() -> None:
    """Test stream something."""
    response = "text/event-stream"

def test_stream_but_no_event_stream() -> None:
    """Test stream but no event stream."""
    response = "application/json"

def test_normal_function() -> None:
    pass
'''
    module = cst.parse_module(code)
    extract_tests_from_ast(module, spec)


def test_emit_complex_query_parameter() -> None:
    # spaceDelimited, pipeDelimited
    """Test test_emit_complex_query_parameter."""
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


def test_mock_streaming_extraction() -> None:
    """Test test_mock_streaming_extraction."""
    spec = OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"})
    extractor = MockServerExtractor(spec)
    module = cst.parse_module("@app.get('/stream')\ndef my_stream():\n    return EventSourceResponse()\n")
    module.visit(extractor)
    assert spec.paths is not None
    op = spec.paths["/stream"].get
    assert op is not None
    assert op.responses is not None
    resp_200 = op.responses["200"]
    resp_content = getattr(resp_200, "content", None)
    assert resp_content is not None
    assert "text/event-stream" in resp_content


def test_parse_sqlalchemy_cdd() -> None:
    """Test test_parse_sqlalchemy_cdd."""
    import libcst as cst
    from openapi_client.models import OpenAPI
    from openapi_client.sqlalchemy_cdd.parse import parse_sqlalchemy_cdd

    parse_sqlalchemy_cdd(
        cst.parse_module(""),
        OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"}),
    )


def test_parse_cli_sdk_cdd() -> None:
    """Test test_parse_cli_sdk_cdd."""
    import libcst as cst
    from openapi_client.cli_sdk_cdd.parse import parse_cli_sdk_cdd
    from openapi_client.models import OpenAPI

    parse_cli_sdk_cdd(
        cst.parse_module(""),
        OpenAPI(openapi="3.2.0", info={"title": "test", "version": "1.0"}),
    )


def test_emit_function_requestBody() -> None:
    """Test test_emit_function_requestBody."""
    from openapi_client.functions.emit import emit_function
    from openapi_client.models import Operation, RequestBody

    op = Operation(
        operationId="post_things",
        requestBody=RequestBody(content={}),
    )
    node = emit_function("post", "/things", op)
    assert "body" in str(node)


def test_emit_tests() -> None:
    """Test test_emit_tests."""
    from openapi_client.models import (
        OpenAPI,
        Operation,
        Parameter,
        PathItem,
        RequestBody,
        Schema,
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


def test_get_dummy_value_for_schema() -> None:
    """Test test_get_dummy_value_for_schema."""
    from openapi_client.models import Schema
    from openapi_client.tests.emit import get_dummy_value_for_schema

    assert "test_string" in str(get_dummy_value_for_schema(Schema(type="string")))
    assert "1" in str(get_dummy_value_for_schema(Schema(type="integer")))
    assert "1.0" in str(get_dummy_value_for_schema(Schema(type="number")))
    assert "True" in str(get_dummy_value_for_schema(Schema(type="boolean")))
    assert "test_string" in str(get_dummy_value_for_schema(Schema(type="array", items=Schema(type="string"))))
    assert "1" in str(get_dummy_value_for_schema(Schema(type="array", items=Schema(type="integer"))))
    assert "List(" in str(get_dummy_value_for_schema(Schema(type="array", items=Schema(type="number"))))
    assert "Dict(" in str(get_dummy_value_for_schema(Schema(type="object")))
    assert "None" in str(get_dummy_value_for_schema(Schema(type="unknown")))


def test_emit_tests_more() -> None:
    """Test test_emit_tests_more."""
    from openapi_client.models import (
        OpenAPI,
        Operation,
        Parameter,
        PathItem,
        RequestBody,
        Schema,
    )
    from openapi_client.tests.emit import emit_tests

    # array payload
    op1 = Operation(
        operationId="post_things_array",
        requestBody=RequestBody(
            content={"application/json": {"schema": Schema(type="array", items=Schema(type="string"))}}
        ),
    )

    # get findByStatus
    op2 = Operation(
        operationId="find_by_status",
        requestBody=RequestBody(content={"application/xml": {"schema": Schema(type="object")}}),
        parameters=[Parameter(name="petId", in_="path", schema=Schema(type="integer"))],
    )

    # requestBody with content no application/json or xml
    op3 = Operation(
        operationId="post_other",
        requestBody=RequestBody(content={"text/plain": {"schema": Schema(type="string")}}),
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


def test_emit_tests_exception() -> None:
    """Test test_emit_tests_exception."""
    from typing import Any

    from openapi_client.models import OpenAPI, Operation, PathItem, RequestBody
    from openapi_client.tests.emit import emit_tests

    # Bypass pydantic validation to force an exception in the try block
    class Bad:
        """Test Bad."""

        def __contains__(self, item: object) -> bool:
            """Test __contains__.

            Args:
                item: Key to check.
            """
            raise RuntimeError("Mock error")

    bad_content: Any = Bad()
    rb = RequestBody.model_construct(content=bad_content)
    op = Operation(operationId="err", requestBody=rb)

    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={"/err": PathItem(post=op)},
    )
    mod = emit_tests(spec)
    assert "def test_err():" in mod.code
    assert "response = client.err(" in mod.code


def test_sdk_test_suite_and_base_path_resolution() -> None:
    """Test basePath/server URL prefix resolution, positional body args, and emit_api_tests."""
    from openapi_client.functions.utils import (
        get_default_server_url,
        get_server_base_path,
        get_test_base_url,
    )
    from openapi_client.models import Server
    from openapi_client.tests.emit import emit_api_tests, emit_operation_test

    spec_v2 = OpenAPI(
        openapi="2.0",
        info={"title": "Petstore V2", "version": "1.0"},
        basePath="/v2",
        paths={
            "/pet": PathItem(
                post=Operation(
                    operationId="addPet",
                    parameters=[
                        Parameter(
                            name="body",
                            in_="body",
                            required=True,
                            schema=Schema(type="object"),
                        ),
                        Parameter(
                            name="opt_q",
                            in_="query",
                            schema=Schema(type="string", default="avail"),
                        ),
                    ],
                )
            ),
            "non_slash": PathItem(get=Operation(operationId="ignored")),
        },
    )
    assert get_server_base_path(spec_v2) == "/v2"
    assert get_default_server_url(spec_v2) == "http://localhost:8080/v2"
    assert get_test_base_url(spec_v2) == "http://localhost:8080/v2"

    spec_root = OpenAPI(
        openapi="2.0",
        info={"title": "Root API", "version": "1.0"},
        basePath="/",
    )
    assert get_server_base_path(spec_root) == "/"
    assert get_test_base_url(spec_root) == "http://localhost:8080"

    spec_oas3 = OpenAPI(
        openapi="3.0.4",
        info={"title": "Petstore V3", "version": "1.0"},
        servers=[Server(url="https://petstore3.swagger.io/api/v3")],
        paths={"/pet": PathItem(get=Operation(operationId="getPets"))},
    )
    assert get_server_base_path(spec_oas3) == "/api/v3"
    assert get_test_base_url(spec_oas3) == "http://localhost:8080/api/v3"

    spec_rel_server = OpenAPI(
        openapi="3.0.4",
        info={"title": "Rel Server", "version": "1.0"},
        servers=[Server(url="/api/v3/")],
    )
    assert get_default_server_url(spec_rel_server, fallback="relative_only") == "http://localhost:8080/api/v3"

    spec_local_server = OpenAPI(
        openapi="3.0.4",
        info={"title": "Local Server", "version": "1.0"},
        servers=[Server(url="http://localhost:9090/custom/")],
    )
    assert get_test_base_url(spec_local_server) == "http://localhost:9090/custom"

    spec_root_server = OpenAPI(
        openapi="3.0.4",
        info={"title": "Root Server", "version": "1.0"},
        servers=[Server(url="https://example.com/")],
    )
    assert get_server_base_path(spec_root_server, default_prefix="/v2") == "/v2"

    spec_empty_server = OpenAPI(
        openapi="3.0.4",
        info={"title": "Empty Server", "version": "1.0"},
        servers=[Server(url="")],
    )
    assert get_server_base_path(spec_empty_server, default_prefix="/v2") == "/v2"
    assert get_test_base_url(spec_empty_server, default_prefix="/v2") == "http://localhost:8080/v2"

    assert spec_v2.paths is not None
    add_pet_op = spec_v2.paths["/pet"].post
    assert add_pet_op is not None
    fn_node = emit_operation_test("post", "/pet", add_pet_op, composable=True, spec=spec_v2)
    fn_code = cst.Module(body=[fn_node]).code
    assert 'client.add_pet({}, "avail")' in fn_code
    assert "body=" not in fn_code

    api_mod_v2 = emit_api_tests(spec_v2)
    assert 'API_URL = os.getenv("API_URL", "http://localhost:8080/v2")' in api_mod_v2.code
    assert '"add_pet"' in api_mod_v2.code

    api_mod_oas3 = emit_api_tests(spec_oas3)
    assert 'API_URL = os.getenv("API_URL", "http://localhost:8080/api/v3")' in api_mod_oas3.code
    assert '"get_pets"' in api_mod_oas3.code
