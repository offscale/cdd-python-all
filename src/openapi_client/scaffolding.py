"""Package and GitHub Actions scaffolding utilities."""

from __future__ import annotations

import re
from pathlib import Path


def _sanitize_slug(raw: str, default: str = "generated_sdk") -> str:
    """Sanitize a string into a valid Python package/repository identifier.

    Args:
        raw: Raw name or title string.
        default: Fallback identifier if `raw` is empty after sanitization.

    Returns:
        Sanitized lowercase slug.
    """
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip()).strip("_").lower()
    if not slug or slug[0].isdigit():
        slug = f"pkg_{slug}" if slug else default
    return slug


def write_generated(
    code_obj: dict[str, str] | str,
    default_filename: str,
    base_dir: Path,
) -> None:
    """Write either a single generated string or a dictionary of relative files to disk.

    Args:
        code_obj: Either a dictionary mapping relative paths to code strings, or a single code string.
        default_filename: Target filename in `base_dir` when `code_obj` is a string.
        base_dir: Root directory where files should be written.
    """
    if isinstance(code_obj, dict):
        for rel_path, content in code_obj.items():
            file_path = base_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if content.strip():
                file_path.write_text(content, encoding="utf-8")
    elif isinstance(code_obj, str) and code_obj.strip():
        target = base_dir / default_filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code_obj, encoding="utf-8")


def scaffold_package(
    out_dir: Path,
    server: bool = False,
    cli: bool = False,
    mcp: bool = False,
    github_org: str | None = None,
    repo_name: str | None = None,
    doc_host: str = "readthedocs",
    package_name: str | None = None,
    version: str = "0.1.0",
    description: str = "Generated Python SDK",
    license_id: str = "Apache-2.0 OR MIT",
    is_server: bool = False,
) -> None:
    """Write `pyproject.toml`, `.readthedocs.yaml`, and `docs/conf.py` into `out_dir` if absent.

    Args:
        out_dir: Output package directory.
        server: If True, include FastAPI/Uvicorn/SQLAlchemy/Faker server dependencies.
        cli: If True, include `[project.scripts]` CLI entrypoint.
        mcp: If True, include `[project.scripts]` MCP server entrypoint.
        github_org: Optional GitHub organization or user name for URLs and docs.
        repo_name: Optional repository name for URLs and docs.
        doc_host: Documentation hosting target (`'official'`, `'readthedocs'`, `'github_pages'`, `'github-pages'`, or `'none'`).
        package_name: Optional package name override.
        version: Package version string.
        description: Package summary description string.
        license_id: SPDX license expression string.
        is_server: Legacy alias for `server`.
    """
    nl = chr(10)
    server = server or is_server
    org = github_org or "offscale"
    raw_pkg = package_name or repo_name or f"{org}-sdk-python"
    pkg_slug = _sanitize_slug(raw_pkg)
    repo = repo_name or (
        f"{org}-sdk-python" if github_org else pkg_slug.replace("_", "-")
    )

    norm_host = doc_host.replace("-", "_").lower()
    if norm_host == "readthedocs":
        docs_url = f"https://{repo}.readthedocs.io/"
    elif norm_host in ("github_pages", "official"):
        docs_url = f"https://{org}.github.io/{repo}/"
    else:
        docs_url = f"https://github.com/{org}/{repo}#readme"

    pyproject = out_dir / "pyproject.toml"
    if not pyproject.exists():
        deps = (
            '["urllib3>=2.0.0", "pydantic>=2.0.0", "fastapi>=0.100.0", "uvicorn>=0.23.0", "sqlalchemy>=2.0.0", "faker>=19.0.0"]'
            if server
            else '["urllib3>=2.0.0", "pydantic>=2.0.0"]'
        )
        script_lines: list[str] = []
        base_cmd = pkg_slug.replace("_", "-")
        if cli:
            script_lines.append(f'{base_cmd} = "cli_main:main"')
        elif server:
            script_lines.append(f'{base_cmd}-server = "main:main"')
        if mcp:
            script_lines.append(f'{base_cmd}-mcp = "mcp_server:start_mcp_server"')
        scripts_section = (
            f"{nl}[project.scripts]{nl}" + nl.join(script_lines) + nl
            if script_lines
            else ""
        )

        safe_desc = (
            description.replace('"', "'").splitlines()[0]
            if description
            else "Generated Python SDK"
        )
        pyproject.write_text(
            f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{pkg_slug}"
version = "{version}"
description = "{safe_desc}"
license = {{text = "{license_id}"}}
requires-python = ">=3.11"
dependencies = {deps}

[project.urls]
Homepage = "https://github.com/{org}/{repo}"
Repository = "https://github.com/{org}/{repo}.git"
Documentation = "{docs_url}"
{scripts_section}
[project.optional-dependencies]
dev = ["pytest>=7.0.0", "httpx>=0.24.0", "sphinx>=7.0.0", "build>=1.0.0", "twine>=5.0.0"]

[tool.pytest.ini_options]
pythonpath = ["src", "."]
testpaths = ["test"]
addopts = "-o addopts="

[tool.hatch.build.targets.wheel]
packages = ["src"]
""",
            encoding="utf-8",
        )

    if norm_host != "none":
        docs_dir = out_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        conf_py = docs_dir / "conf.py"
        if not conf_py.exists():
            conf_py.write_text(
                f'''"""Sphinx configuration for {pkg_slug}."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

project = {pkg_slug!r}
author = {org!r}
release = {version!r}
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
html_theme = "alabaster"
''',
                encoding="utf-8",
            )
        index_rst = docs_dir / "index.rst"
        if not index_rst.exists():
            title_bar = "=" * len(pkg_slug)
            index_rst.write_text(
                f"""{pkg_slug}
{title_bar}

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
""",
                encoding="utf-8",
            )

        rtd_yaml = out_dir / ".readthedocs.yaml"
        if not rtd_yaml.exists():
            rtd_yaml.write_text(
                """version: 2

build:
  os: ubuntu-24.04
  tools:
    python: "3.11"

sphinx:
  configuration: docs/conf.py

python:
  install:
    - method: pip
      path: .
      extra_requirements:
        - dev
""",
                encoding="utf-8",
            )


def scaffold_github_actions(
    out_dir: Path,
    tests: bool = False,
    doc_host: str = "readthedocs",
) -> None:
    """Write `.github/workflows/ci.yml` into `out_dir` if absent.

    Args:
        out_dir: Output package directory.
        tests: If True, include a `pytest` execution step in the workflow.
        doc_host: Documentation hosting target (`'official'`, `'readthedocs'`, `'github_pages'`, `'github-pages'`, or `'none'`).
    """
    nl = chr(10)
    gh_dir = out_dir / ".github" / "workflows"
    gh_dir.mkdir(parents=True, exist_ok=True)
    ci_file = gh_dir / "ci.yml"
    norm_host = doc_host.replace("-", "_").lower()
    if not ci_file.exists():
        test_step = (
            nl.join(["", "      - name: Run tests", "        run: pytest"])
            if tests
            else ""
        )
        docs_step = (
            nl.join(
                [
                    "",
                    "      - name: Build Sphinx docs",
                    "        run: sphinx-build -b html docs docs/_build/html",
                    "      - name: Deploy docs to GitHub Pages",
                    "        if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master')",
                    "        uses: peaceiris/actions-gh-pages@v4",
                    "        with:",
                    "          github_token: ${{ secrets.GITHUB_TOKEN }}",
                    "          publish_dir: ./docs/_build/html",
                ]
            )
            if norm_host != "none"
            else ""
        )
        ci_file.write_text(
            f"""name: CI

on:
  push:
    branches: [ main, master ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main, master ]

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  test-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[dev]{test_step}
      - name: Build distribution
        run: python -m build
      - name: Sign distributions with GPG
        if: startsWith(github.ref, 'refs/tags/v') && env.GPG_PRIVATE_KEY != ''
        env:
          GPG_PRIVATE_KEY: ${{{{ secrets.GPG_PRIVATE_KEY }}}}
          GPG_PASSPHRASE: ${{{{ secrets.GPG_PASSPHRASE }}}}
        run: |
          echo "$GPG_PRIVATE_KEY" | gpg --batch --import
          for f in dist/*.whl dist/*.tar.gz; do
            gpg --batch --yes --pinentry-mode loopback --passphrase "$GPG_PASSPHRASE" --detach-sign --armor "$f"
          done
      - name: Publish to PyPI
        if: startsWith(github.ref, 'refs/tags/v')
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{{{ secrets.PYPI_TOKEN }}}}
        run: twine upload dist/*{docs_step}
""",
            encoding="utf-8",
        )
