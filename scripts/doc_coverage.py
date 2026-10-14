"""Module for calculating docstring coverage across modules, classes, functions, and arguments."""

from __future__ import annotations

import ast
import os


def calculate_doc_coverage(directory: str) -> tuple[float, int, int]:
    """Calculate the percentage of modules, classes, functions, and arguments with docstrings.

    Args:
        directory: Root directory to scan recursively for `.py` files.

    Returns:
        A tuple of `(coverage_percentage, documented_count, total_count)`.
    """
    total = 0
    with_docs = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            total += 1
            if ast.get_docstring(tree):
                with_docs += 1
            else:
                print(f"Missing docstring: Module {path}")

            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    if node.name.startswith("__") and node.name != "__init__":
                        continue
                    total += 1
                    doc = ast.get_docstring(node)
                    if doc:
                        with_docs += 1
                    else:
                        print(f"Missing docstring: {path} :: {node.name}")

                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for arg in node.args.args:
                            if arg.arg in ("self", "cls"):
                                continue
                            total += 1
                            if doc and arg.arg in doc:
                                with_docs += 1
                            else:
                                print(
                                    f"Missing arg docstring: {path} :: {node.name}({arg.arg})"
                                )

    percent = (with_docs / total * 100) if total > 0 else 0.0
    return percent, with_docs, total


if __name__ == "__main__":  # pragma: no cover
    p, w, t = calculate_doc_coverage("src/openapi_client")  # pragma: no cover
    print(f"{p:.2f}")  # pragma: no cover
