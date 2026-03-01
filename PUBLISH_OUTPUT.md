# Publishing the Output (Generated SDK)

When you generate a client SDK using `cdd-python from_openapi to_sdk`, the generated directory will contain a `pyproject.toml` and GitHub Actions workflow.

To automate SDK updates:
1. Schedule a GitHub Action to fetch the latest OpenAPI spec (e.g., via cron).
2. Run `cdd-python from_openapi to_sdk` on the fetched spec.
3. Compare `client.py` using `git status`. If changed, commit and bump the version in `pyproject.toml`.
4. Run `python3 -m build` and upload to PyPI or your internal package registry.
