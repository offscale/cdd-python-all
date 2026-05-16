with open("tests/test_compliance_updates.py", "r") as f:
    content = f.read()

content = content.replace(
    '{"name": Schema(type="str"), "photoUrls": Schema(type="list[str]")}',
    '{"name": Schema(type="str"), "photoUrls": Schema(type="list[str]"), "other": Schema(type="str")}',
)

with open("tests/test_compliance_updates.py", "w") as f:
    f.write(content)

with open("tests/test_compliance_updates.py", "a") as f:
    f.write("""
def test_emit_tests_exception():
    from openapi_client.models import OpenAPI, Operation, RequestBody, PathItem
    from openapi_client.tests.emit import emit_tests

    # Bypass pydantic validation to force an exception in the try block
    rb = RequestBody.model_construct(content={"application/json": object()})
    op = Operation(operationId="err", requestBody=rb)

    spec = OpenAPI(
        openapi="3.2.0",
        info={"title": "test", "version": "1.0"},
        paths={"/err": PathItem(post=op)}
    )
    emit_tests(spec)
""")
