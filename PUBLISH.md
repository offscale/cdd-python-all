# Publishing cdd-python-client

## Publishing to PyPI
This project should be published to PyPI (the standard Python package index).
1. Build the distribution: `make build`
2. Publish using twine: `twine upload dist/*`

## Publishing Docs
Docs can be generated using `make build_docs`.
To host them via GitHub Pages:
1. Generate docs: `make build_docs`
2. Push the `docs/` folder to the `gh-pages` branch.
