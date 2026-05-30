def test_coverage_emit_branches_4():
    from openapi_client.tests.emit import emit_tests
    from openapi_client.models import OpenAPI, PathItem, Operation, Parameter, Reference

    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "Test", "version": "1.0.0"},
        paths={
            "/good": PathItem(
                get=Operation(
                    operationId="get_good",
                    responses={"200": {"description": "ok"}},
                    parameters=[
                        Parameter(
                            name="status", in_="query", schema_={"type": "string"}
                        ),
                        # This param has no name, to test 108->107. We use Reference.
                        Reference(ref="#/components/parameters/mock"),
                    ],
                )
            ),
            # This path doesn't start with / to test 481->480
            "bad_path": PathItem(
                get=Operation(
                    operationId="get_bad", responses={"200": {"description": "ok"}}
                )
            ),
        },
    )

    emit_tests(spec)
