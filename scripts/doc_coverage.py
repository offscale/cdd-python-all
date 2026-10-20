"""Module for calculating docstring coverage across modules, classes, functions, and arguments."""

from __future__ import annotations

import ast
import os
import re


def _collect_function_args(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.arg]:
    """Collect all positional-only, regular, keyword-only, `*args`, and `**kwargs` arguments.

    Args:
        node: The AST FunctionDef or AsyncFunctionDef node.

    Returns:
        List of `ast.arg` objects for the function signature.
    """
    all_args: list[ast.arg] = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]
    if node.args.vararg is not None:
        all_args.append(node.args.vararg)
    if node.args.kwarg is not None:
        all_args.append(node.args.kwarg)
    return all_args


def _has_structured_arg_doc(doc: str | None, arg_name: str) -> bool:
    """Check whether `doc` documents `arg_name` in a structured `Args:` or `:param:` entry.

    Args:
        doc: Extracted docstring text or `None`.
        arg_name: Parameter name to verify.

    Returns:
        `True` if `arg_name` has a structured docstring entry, `False` otherwise.
    """
    if not doc:
        return False
    pattern = rf"(?:^\s*\*{{0,2}}{re.escape(arg_name)}\s*(?:\([^)]*\))?\s*:|:param\s+{re.escape(arg_name)}\s*:)"
    return re.search(pattern, doc, re.MULTILINE) is not None


def calculate_doc_coverage(
    directory: str | tuple[str, ...] = (
        "src/openapi_client",
        "scripts",
        "tests",
        "test",
    ),
) -> tuple[float, int, int]:
    """Calculate the percentage of modules, classes, functions, and arguments with docstrings.

    Args:
        directory: Root directory (or tuple of directories) to scan recursively for `.py` files.

    Returns:
        A tuple of `(coverage_percentage, documented_count, total_count)`.

    Raises:
        SyntaxError: If any `.py` file under `directory` contains invalid Python syntax.
    """
    directories = (directory,) if isinstance(directory, str) else directory
    total = 0
    with_docs = 0

    for single_dir in directories:
        for root, _, files in os.walk(single_dir):
            for file in sorted(files):
                if not file.endswith(".py"):
                    continue
                path = os.path.join(root, file)
                with open(path, encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content, filename=path)

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
                            for arg in _collect_function_args(node):
                                if arg.arg in ("self", "cls"):
                                    continue
                                total += 1
                                if _has_structured_arg_doc(doc, arg.arg):
                                    with_docs += 1
                                else:
                                    print(
                                        f"Missing arg docstring: {path} :: {node.name}({arg.arg})"
                                    )

    percent = (with_docs / total * 100) if total > 0 else 0.0
    return percent, with_docs, total


if __name__ == "__main__":  # pragma: no cover
    p, w, t = calculate_doc_coverage()  # pragma: no cover
    print(f"{p:.2f}")  # pragma: no cover
