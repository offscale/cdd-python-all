"""
Module for emitting complete Python client module from OpenAPI schema.
"""

import libcst as cst
from openapi_client.models import OpenAPI
from openapi_client.classes.emit import emit_classes
from openapi_client.functions.emit import emit_functions

from typing import List


class ClientGenerator:
    """
    Generator class responsible for converting an OpenAPI object into a libcst.Module.
    """

    def __init__(self, spec: OpenAPI):
        self.spec = spec

    def generate(self) -> cst.Module:
        """
        Generate the AST module containing imports, Pydantic classes, and the Client class.

        Returns:
            cst.Module: The constructed Python syntax tree representing the client.
        """
        body: List[cst.BaseStatement | cst.EmptyLine] = []

        # Emit imports
        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("urllib3"),
                        names=[cst.ImportAlias(name=cst.Name("PoolManager"))],
                    )
                ]
            )
        )
        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("typing"),
                        names=[
                            cst.ImportAlias(name=cst.Name("Any")),
                            cst.ImportAlias(name=cst.Name("Dict")),
                            cst.ImportAlias(name=cst.Name("Optional")),
                            cst.ImportAlias(name=cst.Name("List")),
                        ],
                    )
                ]
            )
        )
        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("pydantic"),
                        names=[
                            cst.ImportAlias(name=cst.Name("BaseModel")),
                            cst.ImportAlias(name=cst.Name("Field")),
                        ],
                    )
                ]
            )
        )
        body.append(cst.EmptyLine())

        # Emit classes (Pydantic Models)
        if self.spec.components and self.spec.components.schemas:
            class_defs = emit_classes(self.spec.components.schemas)
            for class_def in class_defs:
                body.append(class_def)
                body.append(cst.EmptyLine())

        # Emit functions inside the Client class
        methods = emit_functions(self.spec)

        client_class = cst.ClassDef(
            name=cst.Name("Client"), body=cst.IndentedBlock(body=methods)
        )

        body.append(client_class)

        return cst.Module(body=body)  # type: ignore

    def generate_code(self) -> str:
        """
        Generate Python source code directly from the OpenAPI specification.

        Returns:
            str: The generated Python code as a string.
        """
        return self.generate().code
