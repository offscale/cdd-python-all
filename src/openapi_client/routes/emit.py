"""Module for emitting complete Python client module from OpenAPI schema."""

from __future__ import annotations

import libcst as cst

from openapi_client.functions.emit import emit_functions
from openapi_client.models import OpenAPI


class ClientGenerator:
    """Generator class responsible for converting an OpenAPI object into a libcst.Module."""

    def __init__(self, spec: OpenAPI) -> None:
        """Initialize ClientGenerator with an OpenAPI spec.

        Args:
            spec: The OpenAPI specification model.
        """
        self.spec = spec

    def generate(self) -> cst.Module:
        """Generate the AST module containing imports and the Client class.

        Returns:
            The constructed Python syntax tree representing the client.
        """
        body: list[cst.BaseStatement | cst.EmptyLine] = []

        body.append(
            cst.SimpleStatementLine(
                [
                    cst.ImportFrom(
                        module=cst.Name("__future__"),
                        names=[
                            cst.ImportAlias(name=cst.Name("annotations")),
                        ],
                    )
                ]
            )
        )
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
                        ],
                    )
                ]
            )
        )
        body.append(cst.EmptyLine())

        if self.spec.components and self.spec.components.schemas:
            body.append(
                cst.SimpleStatementLine(
                    [
                        cst.ImportFrom(
                            module=cst.Name("models"),
                            names=cst.ImportStar(),
                        )
                    ]
                )
            )
            body.append(cst.EmptyLine())

        methods = emit_functions(self.spec)

        client_class = cst.ClassDef(
            name=cst.Name("Client"), body=cst.IndentedBlock(body=methods)
        )

        body.append(client_class)

        return cst.Module(body=body)

    def generate_code(self) -> str:
        """Generate Python source code directly from the OpenAPI specification.

        Returns:
            The generated Python code as a string.
        """
        return self.generate().code
