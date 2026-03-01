"""
Module for extracting OpenAPI Operations from Python method ASTs.
"""

from typing import List, Dict, Union, Any, cast
import libcst as cst
from openapi_client.models import (
    OpenAPI,
    PathItem,
    Operation,
    Parameter,
    RequestBody,
    MediaType,
    Response,
    Schema,
    Reference,
)


def _extract_schema_from_annotation(
    annotation: cst.Annotation,
) -> Union[Schema, Reference]:
    """Helper to convert CST annotation node to OpenAPI Schema/Reference."""
    # Extremely basic mapping logic. Ideally calls `get_schema_for_annotation`
    ann_node = annotation.annotation
    if isinstance(ann_node, cst.Name):
        type_str = ann_node.value
        if type_str == "int":
            return Schema(type="integer")
        elif type_str == "str":
            return Schema(type="string")
        elif type_str == "bool":
            return Schema(type="boolean")
        elif type_str == "float":
            return Schema(type="number")
        else:
            return Reference(**{"$ref": f"#/components/schemas/{type_str}"})
    elif isinstance(ann_node, cst.Subscript):
        # Handling List[Type] or Dict[str, Type]
        base_name = getattr(ann_node.value, "value", None)
        if base_name in ("List", "list"):
            slice_node = ann_node.slice[0].slice
            if isinstance(slice_node, cst.Index):
                item_ann = cst.Annotation(annotation=slice_node.value)
                item_schema = _extract_schema_from_annotation(item_ann)
                return Schema(type="array", items=item_schema)
        elif base_name in ("Dict", "dict"):
            return Schema(type="object")
    return Schema(type="string")  # Default


class FunctionExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract method definitions into OpenAPI Path/Operation structures.
    """

    def __init__(self, spec: OpenAPI):
        """Initialize FunctionExtractor with an OpenAPI spec."""
        self.spec = spec
        if not self.spec.paths:
            self.spec.paths = {}

    def _extract_decorators(self, node: cst.FunctionDef, operation: Operation) -> None:
        """Extract information from decorators."""
        for decorator in node.decorators:
            if isinstance(decorator.decorator, cst.Name):
                name = decorator.decorator.value
                if name == "deprecated":
                    operation.deprecated = True
            elif isinstance(decorator.decorator, cst.Call):
                func = decorator.decorator.func
                if isinstance(func, cst.Name) and func.value == "tags":
                    args = decorator.decorator.args
                    if args and isinstance(args[0].value, cst.List):
                        tags_list = []
                        for el in args[0].value.elements:
                            if isinstance(el.value, cst.SimpleString):
                                tags_list.append(el.value.value.strip("'\""))
                        if tags_list:
                            operation.tags = tags_list

    def _extract_parameters(
        self, node: cst.FunctionDef, operation: Operation, path: str
    ) -> None:
        """Extract parameters and request body from function arguments."""
        parameters = []

        for param in node.params.params:
            name = param.name.value
            if name == "self":
                continue

            schema = None
            if param.annotation:
                schema = _extract_schema_from_annotation(param.annotation)

            # Check if this is a path parameter
            # Heuristic: if it has no default and is a simple type, it's a path param.
            # If it has a default, it's a query param.

            in_path = (param.default is None) and not (
                name in ("body", "data", "payload")
                or (schema and isinstance(schema, Reference))
            )

            if name in ("body", "data", "payload") or (
                schema and isinstance(schema, Reference)
            ):
                # Assume RequestBody
                if operation.requestBody is None:
                    operation.requestBody = RequestBody(
                        content={
                            "application/json": MediaType(
                                **{"schema": schema or Schema(type="object")}
                            )
                        },
                        required=param.default is None,
                    )
            else:
                p = Parameter(
                    name=name,
                    **{"in": "path" if in_path else "query"},
                    required=param.default is None,
                    **{"schema": schema} if schema else {},
                )
                parameters.append(p)

        if parameters:
            operation.parameters = parameters

    def _extract_returns(self, node: cst.FunctionDef, operation: Operation) -> None:
        """Extract responses from the return annotation."""
        if node.returns:
            schema = _extract_schema_from_annotation(node.returns)
            operation.responses = {
                "200": Response(
                    description="Successful Response",
                    content={"application/json": MediaType(**{"schema": schema})},
                )
            }

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """
        Extract operation based on function name convention (e.g., get_pets -> GET /pets).
        """
        name = node.name.value
        # Simple heuristic: split by first underscore
        if "_" in name:
            parts = name.split("_", 1)
            method = parts[0].lower()
            if method in ["get", "post", "put", "delete", "patch"]:
                path = "/" + parts[1].replace("_", "/")

                if self.spec.paths is not None and path not in self.spec.paths:
                    self.spec.paths[path] = PathItem(**{})  # type: ignore[call-arg]

                from openapi_client.docstrings.parse import parse_docstring

                summary, description = parse_docstring(node)

                operation = Operation(operationId=name)
                if summary:
                    operation.summary = summary
                if description:
                    operation.description = description

                self._extract_decorators(node, operation)
                self._extract_parameters(node, operation, path)
                self._extract_returns(node, operation)

                if self.spec.paths is not None:
                    setattr(self.spec.paths[path], method, operation)


def extract_functions_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API operations from a parsed module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = FunctionExtractor(spec)
    module.visit(visitor)
