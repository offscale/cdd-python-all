import re

with open("tests/test_compliance_updates.py", "r") as f:
    content = f.read()

content = content.replace(
    "from openapi_client.models import OpenAPI, Operation, RequestBody, Schema, PathItem",
    "from openapi_client.models import OpenAPI, Operation, RequestBody, Schema, PathItem, Parameter"
)

with open("tests/test_compliance_updates.py", "w") as f:
    f.write(content)
