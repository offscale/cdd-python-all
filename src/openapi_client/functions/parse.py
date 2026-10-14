"""Module for extracting OpenAPI Operations from Python method ASTs."""

from __future__ import annotations

import re

import libcst as cst

from openapi_client.docstrings.parse import parse_docstring
from openapi_client.models import (
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
)


def _extract_schema_from_annotation(
    annotation: cst.Annotation,
) -> Schema | Reference:
    """Convert a LibCST annotation node to an OpenAPI Schema or Reference.

    Args:
        annotation: The LibCST Annotation node.

    Returns:
        The mapped OpenAPI Schema or Reference.
    """
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
        elif type_str == "Any":
            return Schema(type="string")
        else:
            return Reference(**{"$ref": f"#/components/schemas/{type_str}"})
    elif isinstance(ann_node, cst.Subscript):
        base_name = getattr(ann_node.value, "value", None)
        if base_name in ("List", "list"):
            slice_node = ann_node.slice[0].slice
            if isinstance(slice_node, cst.Index):
                item_ann = cst.Annotation(annotation=slice_node.value)
                item_schema = _extract_schema_from_annotation(item_ann)
                return Schema(type="array", items=item_schema)
        elif base_name in ("Dict", "dict"):
            return Schema(type="object")
    return Schema(type="string")


def _extract_method_and_path_from_body(
    node: cst.FunctionDef,
) -> tuple[str | None, str | None]:
    """Inspect a function body for `self.base_url + ...` and `self.http.request(...)`.

    Args:
        node: The LibCST FunctionDef node.

    Returns:
        A tuple of `(http_method, route_path)` if detected in the body, else `(None, None)`.
    """
    found_method: str | None = None
    found_path: str | None = None

    class BodyInspector(cst.CSTVisitor):
        """Visitor to extract URL path and HTTP verb from client method body."""

        def visit_Assign(self, assign_node: cst.Assign) -> None:
            """Inspect `url = self.base_url + ...` assignments.

            Args:
                assign_node: The LibCST Assign node being visited.
            """
            nonlocal found_path
            for target in assign_node.targets:
                if (
                    isinstance(target.target, cst.Name)
                    and target.target.value == "url"
                    and isinstance(assign_node.value, cst.BinaryOperation)
                ):
                    expr = assign_node.value
                    if isinstance(expr.left, cst.BinaryOperation):
                        expr = expr.left
                    right = expr.right
                    if isinstance(right, cst.SimpleString):
                        found_path = str(right.evaluated_value)
                    elif isinstance(right, cst.FormattedString):
                        parts = [
                            part.value
                            if isinstance(part, cst.FormattedStringText)
                            else "{"
                            + str(getattr(part.expression, "value", "param"))
                            + "}"
                            for part in right.parts
                        ]
                        found_path = "".join(parts)

        def visit_Call(self, call_node: cst.Call) -> None:
            """Inspect `self.http.request("GET", ...)` calls.

            Args:
                call_node: The LibCST Call node being visited.
            """
            nonlocal found_method
            if (
                isinstance(call_node.func, cst.Attribute)
                and call_node.func.attr.value == "request"
                and call_node.args
                and isinstance(call_node.args[0].value, cst.SimpleString)
            ):
                found_method = str(call_node.args[0].value.evaluated_value).lower()

    node.body.visit(BodyInspector())
    return found_method, found_path


class FunctionExtractor(cst.CSTVisitor):
    """AST Visitor to extract method definitions into OpenAPI Path/Operation structures."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize FunctionExtractor with an OpenAPI spec.

        Args:
            spec: The OpenAPI specification to update in-place.
        """
        self.spec = spec
        if not self.spec.paths:
            self.spec.paths = {}

    def _extract_decorators(self, node: cst.FunctionDef, operation: Operation) -> None:
        """Extract metadata from function decorators.

        Args:
            node: The LibCST FunctionDef node.
            operation: The OpenAPI Operation to populate.
        """
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
        """Extract parameters and request body from function arguments.

        Args:
            node: The LibCST FunctionDef node.
            operation: The OpenAPI Operation to populate.
            path: The route path string.
        """
        parameters: list[Parameter] = []
        path_vars = set(re.findall(r"\{([^}]+)\}", path))

        for param in node.params.params:
            name = param.name.value
            if name == "self":
                continue

            schema = None
            if param.annotation:
                schema = _extract_schema_from_annotation(param.annotation)

            in_path = (name in path_vars) or (
                (param.default is None)
                and not path_vars
                and not (
                    name in ("body", "data", "payload")
                    or (schema and isinstance(schema, Reference))
                )
            )

            if name in ("body", "data", "payload") or (
                schema and isinstance(schema, Reference)
            ):
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
                    required=in_path or (param.default is None),
                    **({"schema": schema} if schema else {}),
                )
                parameters.append(p)

        if parameters:
            operation.parameters = parameters

    def _extract_returns(self, node: cst.FunctionDef, operation: Operation) -> None:
        """Extract responses from the return annotation.

        Args:
            node: The LibCST FunctionDef node.
            operation: The OpenAPI Operation to populate.
        """
        if node.returns:
            schema = _extract_schema_from_annotation(node.returns)
            operation.responses = {
                "200": Response(
                    description="Successful Response",
                    content={"application/json": MediaType(**{"schema": schema})},
                )
            }

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        """Extract operation from a function definition via body inspection or name convention.

        Args:
            node: The LibCST FunctionDef node being visited.
        """
        name = node.name.value
        if name.startswith("__"):
            return

        method, path = _extract_method_and_path_from_body(node)
        if not method or not path:
            if "_" in name:
                parts = name.split("_", 1)
                candidate = parts[0].lower()
                if candidate in ("get", "post", "put", "delete", "patch"):
                    method = method or candidate
                    path = path or ("/" + parts[1].replace("_", "/"))

        if method and path:
            if self.spec.paths is not None and path not in self.spec.paths:
                self.spec.paths[path] = PathItem()

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
    """Extract API operations from a parsed module into an OpenAPI specification.

    Args:
        module: Parsed Python module.
        spec: OpenAPI specification to update.
    """
    visitor = FunctionExtractor(spec)
    module.visit(visitor)
