from openapi_client.models import OpenAPI, PathItem, Operation, Parameter, Schema
from openapi_client.cli_sdk_cdd.emit import emit_cli_sdk


def test_cli_sdk_cdd_emit_branches():
    spec = OpenAPI(openapi="3.1.0", info={"title": "Test", "version": "1.0.0"})

    # test1: no parameters (58->78)
    # test2: parameter with no schema (64->69)
    # test3: parameter with schema but type is not list (66->69)
    spec.paths = {
        "/test1": PathItem(
            get=Operation(operationId="test1", responses={}, parameters=[])
        ),
        "/test2": PathItem(
            get=Operation(
                operationId="test2",
                responses={},
                parameters=[
                    Parameter(name="param1", **{"in": "query", "schema_": None})
                ],
            )
        ),
        "/test3": PathItem(
            get=Operation(
                operationId="test3",
                responses={},
                parameters=[
                    Parameter(
                        name="param2",
                        **{
                            "in": "query",
                            "schema_": Schema(type="integer", **{"ref": None}),
                        },
                    )
                ],
            )
        ),
    }

    # We also need python-cdd to emit something valid or catch an exception.
    # We can just run emit_cli_sdk.
    emit_cli_sdk(spec)
