with open("tests/test_compliance_updates.py", "r") as f:
    content = f.read()

content = content.replace(
    'rb = RequestBody.model_construct(content={"application/json": object()})',
    "class Bad:\n        def __bool__(self): return True\n    rb = RequestBody.model_construct(content=Bad())",
)

with open("tests/test_compliance_updates.py", "w") as f:
    f.write(content)
