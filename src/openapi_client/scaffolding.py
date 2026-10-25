"""Package and GitHub Actions scaffolding utilities."""

from __future__ import annotations

from pathlib import Path


def write_generated(
    code_obj: dict[str, str] | str,
    default_filename: str,
    base_dir: Path,
) -> None:
    """Write generated code mapping or string to files.

    Args:
        code_obj: Either a mapping of relative filenames to code or a single code string.
        default_filename: Filename to use when `code_obj` is a single string.
        base_dir: Base output directory.
    """
    if isinstance(code_obj, dict):
        for filename, file_content in code_obj.items():
            if file_content:
                filepath = base_dir / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(file_content, encoding="utf-8")
    elif code_obj:
        (base_dir / default_filename).write_text(code_obj, encoding="utf-8")


def scaffold_package(out_dir: Path, is_server: bool = False) -> None:
    """Generate `pyproject.toml` scaffolding in the output directory.

    Args:
        out_dir: Target directory for the generated package.
        is_server: If True, include FastAPI, SQLAlchemy, and server dependencies.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    deps = [
        '    "pydantic==2.12.5",',
        '    "pydantic-core==2.41.5",',
        '    "urllib3",',
        '    "eval_type_backport",',
        '    "pytest",',
    ]

    if is_server:
        deps.extend(
            [
                '    "fastapi",',
                '    "uvicorn",',
                '    "sqlalchemy",',
                '    "faker",',
                '    "httpx",',
            ]
        )

    nl = chr(10)
    deps_str = nl.join(deps)
    testpaths_str = '["tests"]' if is_server else '["test"]'

    pyproject_toml = out_dir / "pyproject.toml"
    if not pyproject_toml.exists():
        pyproject_toml.write_text(
            f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "generated-project"
version = "0.0.4"
dependencies = [
{deps_str}
]

[project.optional-dependencies]
dev = [
    "pytest",
]

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
addopts = "-o addopts="
testpaths = {testpaths_str}
""",
            encoding="utf-8",
        )


def scaffold_github_actions(out_dir: Path, tests: bool = False) -> None:
    """Scaffold a GitHub Actions CI workflow file.

    Args:
        out_dir: Target directory for the generated repository.
        tests: If True, include a pytest execution step in the workflow.
    """
    workflows_dir = out_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    ci_yml = workflows_dir / "ci.yml"
    if not ci_yml.exists():
        test_step = ""
        if tests:
            test_step = """
      - name: Run tests
        run: pytest test/"""

        ci_yml.write_text(
            f"""name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[dev]{test_step}
""",
            encoding="utf-8",
        )
