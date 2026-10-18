"""Module for emitting complete Python client module from OpenAPI schema."""

from __future__ import annotations

import libcst as cst

from openapi_client.arazzo_models import Arazzo
from openapi_client.functions.emit import emit_functions
from openapi_client.models import OpenAPI
from openapi_client.workflows.emit import emit_workflows_code


class ClientGenerator:
    """Generator class responsible for converting an OpenAPI object into a libcst.Module."""

    def __init__(self, spec: OpenAPI, arazzo_spec: Arazzo | None = None) -> None:
        """Initialize ClientGenerator with an OpenAPI spec and optional Arazzo spec.

        Args:
            spec: The OpenAPI specification model.
            arazzo_spec: Optional Arazzo 1.1.0 workflow specification model.
        """
        self.spec = spec
        self.arazzo_spec = arazzo_spec

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

    def generate_workflows_code(self) -> str | None:
        """Generate Python workflow orchestrator code if an Arazzo specification is bound.

        Returns:
            The generated `workflows.py` source code string, or `None` if no Arazzo spec is bound.
        """
        if self.arazzo_spec is None:
            return None
        return emit_workflows_code(self.arazzo_spec, {"default": self.spec})
