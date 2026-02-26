"""
Module for extracting OpenAPI Schemas from Python class ASTs (Pydantic models).
"""

import libcst as cst
from openapi_client.models import OpenAPI, Schema, Components


class ClassExtractor(cst.CSTVisitor):
    """
    AST Visitor to extract Pydantic class definitions into OpenAPI Schemas.
    """

    def __init__(self, spec: OpenAPI):
        self.spec = spec
        if self.spec.components is None:
            self.spec.components = Components(schemas={})
        if getattr(self.spec.components, "schemas", None) is None:
            self.spec.components.schemas = {}

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        """
        Extract class structure to JSON Schema definitions inside components.schemas.
        """
        name = node.name.value
        if name == "Client":
            return  # Skip the main client class

        from openapi_client.docstrings.parse import parse_docstring

        summary, description = parse_docstring(node)

        schema = Schema(**{"ref": None})  # type: ignore
        schema.type = "object"
        schema.properties = {}
        if summary:
            schema.summary = summary
        if description:
            schema.description = description

        # Simple extraction of class attributes
        if isinstance(node.body, cst.IndentedBlock):
            for statement in node.body.body:
                if isinstance(statement, cst.SimpleStatementLine):
                    for body_element in statement.body:
                        if isinstance(body_element, cst.AnnAssign):
                            target = body_element.target
                            if isinstance(target, cst.Name):
                                prop_name = target.value
                                # Very basic type inference
                                prop_type = "string"  # default
                                if isinstance(
                                    body_element.annotation.annotation, cst.Subscript
                                ):
                                    # Optional[X]
                                    slice_elements = (
                                        body_element.annotation.annotation.slice
                                    )
                                    if slice_elements and isinstance(
                                        slice_elements[0].slice, cst.Index
                                    ):
                                        index_val = slice_elements[0].slice.value
                                        if isinstance(index_val, cst.Name):
                                            if index_val.value == "int":
                                                prop_type = "integer"
                                            elif index_val.value == "float":
                                                prop_type = "number"
                                            elif index_val.value == "bool":
                                                prop_type = "boolean"
                                if schema.properties is not None:
                                    s = Schema(**{"ref": None})  # type: ignore
                                    s.type = prop_type
                                    schema.properties[prop_name] = s

        if self.spec.components and self.spec.components.schemas is not None:
            self.spec.components.schemas[name] = schema


def extract_classes_from_ast(module: cst.Module, spec: OpenAPI) -> None:
    """
    Extract API schemas from a parsed module into an OpenAPI specification.

    Args:
        module (cst.Module): Parsed Python module.
        spec (OpenAPI): OpenAPI specification to update.
    """
    visitor = ClassExtractor(spec)
    module.visit(visitor)
