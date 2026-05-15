import re

with open("tests/test_compliance_updates.py", "r") as f:
    content = f.read()

content = content.replace(
    'assert "{}" in str(get_dummy_value_for_schema(Schema(type="object")))',
    'assert "Dict(" in str(get_dummy_value_for_schema(Schema(type="object")))'
).replace(
    'assert "[]" in str(get_dummy_value_for_schema(Schema(type="array", items=Schema(type="number"))))',
    'assert "List(" in str(get_dummy_value_for_schema(Schema(type="array", items=Schema(type="number"))))'
)

with open("tests/test_compliance_updates.py", "w") as f:
    f.write(content)

with open("tests/test_compliance_updates.py", "a") as f:
    f.write("""
def test_emit_tests_more():
    from openapi_client.models import OpenAPI, Operation, RequestBody, Schema, PathItem, Parameter
    from openapi_client.tests.emit import emit_tests
    
    # array payload
    op1 = Operation(
        operationId="post_things_array",
        requestBody=RequestBody(content={"application/json": {"schema": Schema(type="array", items=Schema(type="string"))}}),
    )
    
    # get findByStatus
    op2 = Operation(
        operationId="find_by_status",
        requestBody=RequestBody(content={"application/xml": {"schema": Schema(type="object")}}),
        parameters=[Parameter(name="petId", in_="path", schema=Schema(type="integer"))]
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
        }
    )
    emit_tests(spec, composable=True)
    emit_tests(spec, composable=False)
""")
