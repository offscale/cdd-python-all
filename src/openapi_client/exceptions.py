"""Unified, strongly-typed exception hierarchy for cdd-python-all."""

from __future__ import annotations


class CDDError(Exception):
    """Base exception for all cdd-python-all errors."""


class SpecificationParseError(CDDError, ValueError):
    """Raised when an OpenAPI or Arazzo specification cannot be parsed or validated."""


class ReferenceResolutionError(SpecificationParseError):
    """Raised when an external or internal `$ref` pointer fails to resolve or escapes the allowed root."""


class CodeEmissionError(CDDError, RuntimeError):
    """Raised when emitting Python AST or source code from an IR model fails."""


class ASTExtractionError(CDDError, ValueError):
    """Raised when extracting an OpenAPI or Arazzo IR model from Python AST fails."""


class RuntimeExpressionError(CDDError, ValueError):
    """Raised when evaluating or compiling an Arazzo 1.1.0 runtime expression fails."""


class MCPProtocolError(CDDError, ValueError, RuntimeError):
    """Raised when an MCP tool, resource, or prompt request or response is invalid or unknown."""


SchemaValidationError = SpecificationParseError
CodeExtractionError = ASTExtractionError
ArazzoExpressionError = RuntimeExpressionError
