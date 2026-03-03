"""Parse FastAPI code into an OpenAPI specification."""

import libcst as cst
from openapi_client.models import OpenAPI, Info, Components


class FastAPIExtractor(cst.CSTVisitor):
    """Visitor for extracting FastAPI routes into an OpenAPI spec."""

    def __init__(self, spec: OpenAPI):
        """Initialize the extractor."""
        self.spec = spec

    def visit_Decorator(self, node: cst.Decorator):
        """Visit decorators to extract app.get('/path') etc."""
        if isinstance(node.decorator, cst.Call):
            if isinstance(node.decorator.func, cst.Attribute):
                if (
                    isinstance(node.decorator.func.value, cst.Name)
                    and node.decorator.func.value.value == "app"
                ):
                    method = node.decorator.func.attr.value
                    if method in ["get", "post", "put", "delete", "patch"]:
                        if node.decorator.args and isinstance(
                            node.decorator.args[0].value, cst.SimpleString
                        ):
                            path = node.decorator.args[0].value.value.strip("\"'")

                            if not self.spec.paths:
                                self.spec.paths = {}
                            if path not in self.spec.paths:
                                self.spec.paths[path] = {}
                            self.spec.paths[path][method] = {
                                "operationId": f"{method}_{path.replace('/', '_').strip('_')}",
                                "responses": {
                                    "200": {"description": "Successful Response"}
                                },
                            }


def extract_fastapi_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """Extract FastAPI information from an AST module into an OpenAPI spec."""
    extractor = FastAPIExtractor(spec)
    module.visit(extractor)
