import ast
import os


def calculate_doc_coverage(directory):
    total = 0
    with_docs = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                tree = ast.parse(content)
            except Exception:
                continue

            # Check module docstring
            total += 1
            if ast.get_docstring(tree):
                with_docs += 1
            else:
                pass  # print(f"Missing docstring: Module {path}")

            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    # skip private methods but keep __init__
                    if node.name.startswith("__") and node.name != "__init__":
                        continue
                    # Actually let's just ignore __init__ or count it if the class has a docstring?
                    # Let's count __init__ as requiring a docstring.
                    total += 1
                    if ast.get_docstring(node):
                        with_docs += 1
                    else:
                        pass  # print(f"Missing docstring: {node.name} in {path}")

    percent = (with_docs / total * 100) if total > 0 else 0
    return percent, with_docs, total


if __name__ == "__main__":
    p, w, t = calculate_doc_coverage("src/openapi_client")
    print(f"{p:.2f}")
