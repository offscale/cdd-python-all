# Publishing the CDD Python Client

This document outlines how to publish the `cdd-python-client` library and CLI to Python's official package repository, as well as how to generate and host the project's documentation.

## 1. Publishing to PyPI (Python Package Index)

PyPI is the standard and most popular package registry for Python. Publishing there makes the library installable via `pip install cdd-python-client`.

### Prerequisites
- Create an account on [PyPI](https://pypi.org/) and [TestPyPI](https://test.pypi.org/).
- Generate an API token from your PyPI account settings.
- Install the build and publish tools:
  ```bash
  pip install build twine
  ```

### Build and Upload
1. **Clean previous builds** (optional but recommended):
   ```bash
   rm -rf dist/ build/
   ```
2. **Build the wheel and sdist**:
   ```bash
   python -m build
   ```
   *This uses `hatchling` as configured in the `pyproject.toml` to generate files in the `dist/` directory.*
3. **Upload to PyPI**:
   ```bash
   python -m twine upload dist/*
   ```
   *When prompted, use `__token__` as the username and your generated API token as the password.*

---

## 2. Generating Local Documentation (Static Serving)

To generate static HTML documentation directly from the source code and docstrings, we recommend `pdoc` (or `mkdocs`/`sphinx`). `pdoc` requires zero configuration and produces a ready-to-serve static HTML folder.

### Generate HTML
```bash
pip install pdoc
pdoc src/openapi_client -o docs_html
```

### Serve Locally
You can preview the generated static documentation by serving the `docs_html` directory:
```bash
python -m http.server -d docs_html 8000
```
Visit `http://localhost:8000` in your browser. This `docs_html` folder can be uploaded to any static web host (e.g., AWS S3, GitHub Pages, Vercel).

---

## 3. Publishing Documentation to Read the Docs

[Read the Docs (RTD)](https://readthedocs.org/) is the most popular hosting platform for open-source Python documentation.

### Setup Steps
1. **Create a `.readthedocs.yaml` file** in the root of the repository:
   ```yaml
   version: 2
   build:
     os: ubuntu-22.04
     tools:
       python: "3.12"
   python:
     install:
       - requirements: requirements.txt
       - method: pip
         path: .
   sphinx:
     configuration: docs/conf.py
   ```
2. **Initialize Sphinx** (if not already done):
   ```bash
   pip install sphinx sphinx-rtd-theme
   mkdir docs && cd docs
   sphinx-quickstart
   ```
   *Update `docs/conf.py` to use `html_theme = 'sphinx_rtd_theme'` and configure the `sys.path` to point to `../src`.*
3. **Connect to Read the Docs**:
   - Log in to [readthedocs.org](https://readthedocs.org/).
   - Click **Import a Project**.
   - Connect your GitHub repository. RTD will automatically hook into your git pushes and build/host the documentation whenever the `main` branch is updated.
