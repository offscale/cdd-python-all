# Publishing `cdd-python-client`

## 1. Uploading the Package to PyPI

The most popular location to publish Python packages is [PyPI (Python Package Index)](https://pypi.org/).

### Build the Package
First, generate the distribution archives (wheel and source distribution):
```sh
make build
```
This generates `.whl` and `.tar.gz` files inside the `dist/` directory.

### Upload with Twine
Install `twine`:
```sh
python -m pip install --upgrade twine
```

Upload the package to PyPI:
```sh
twine upload dist/*
```

## 2. Publishing the Documentation

### Generating a Local Folder for Static Serving
To produce a local folder that can be statically served (e.g., using `python -m http.server`):
```sh
make build_docs
```
This drops the generated HTML documentation into the `docs/` directory.

### Uploading to the Most Popular Location (Read the Docs)
[Read the Docs (RTD)](https://readthedocs.org/) is the standard documentation host for Python.
1. Connect your GitHub/GitLab repository to your Read the Docs account.
2. In the RTD dashboard, configure the build to point to your `docs/` directory or `docs/conf.py` (if using Sphinx or MkDocs).
3. Push to your main branch, and RTD will automatically build and publish your docs online.

Alternatively, for **GitHub Pages**:
1. Commit the `docs/` folder to a `gh-pages` branch, or configure GitHub Actions to deploy the `docs/` directory automatically upon merge.
