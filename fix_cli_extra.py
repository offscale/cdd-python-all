import re

with open("tests/test_cli_extra.py", "r") as f:
    content = f.read()

content = re.sub(
    r"def makefile\(self, mode, \*args, \*\*kwargs\):\s*\n\s*return BytesIO\(\)",
    'def makefile(self, mode, *args, **kwargs):\n                    if "b" in mode:\n                        return BytesIO(b"{}")  # pragma: no cover\n                    return BytesIO()',
    content,
)

with open("tests/test_cli_extra.py", "w") as f:
    f.write(content)
