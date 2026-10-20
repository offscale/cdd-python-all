"""Emit DAO module using LibCST AST construction."""

from __future__ import annotations

import libcst as cst

from openapi_client.functions.utils import (
    build_cst_module,
    sanitize_class_name,
    sanitize_name,
)
from openapi_client.models import OpenAPI


def _doc_stmt(text: str) -> cst.SimpleStatementLine:
    """Create a docstring SimpleStatementLine node.

    Args:
        text: The docstring text content.

    Returns:
        A LibCST SimpleStatementLine containing the triple-quoted docstring.
    """
    bs = chr(92)
    safe_text = text.replace(bs, bs + bs).replace('"""', bs + '"' + bs + '"' + bs + '"')
    return cst.SimpleStatementLine([cst.Expr(cst.SimpleString(f'"""{safe_text}"""'))])


def _emit_abstract_dao_module(name: str, class_name: str) -> cst.Module:
    """Construct the LibCST Module for an abstract DAO file.

    Args:
        name: Raw schema name from OpenAPI.
        class_name: Sanitized Python class identifier.

    Returns:
        A LibCST Module representing `dao/abstract_<name>.py`.
    """
    abs_decorator = cst.Decorator(
        decorator=cst.Attribute(value=cst.Name("abc"), attr=cst.Name("abstractmethod"))
    )
    methods: list[cst.BaseStatement] = [
        _doc_stmt(f"Abstract interface for {name} data access."),
        cst.FunctionDef(
            name=cst.Name("get_all"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            returns=cst.Annotation(annotation=cst.parse_expression("List[Any]")),
            decorators=[abs_decorator],
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Get all {name}s."),
                    cst.SimpleStatementLine([cst.Pass()]),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("get_by_id"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("id"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.parse_expression("Optional[Any]")),
            decorators=[abs_decorator],
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Get {name} by ID."),
                    cst.SimpleStatementLine([cst.Pass()]),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("create"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("data"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.Name("Any")),
            decorators=[abs_decorator],
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Create a new {name}."),
                    cst.SimpleStatementLine([cst.Pass()]),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("delete"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("id"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.Name("bool")),
            decorators=[abs_decorator],
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Delete a {name} by ID."),
                    cst.SimpleStatementLine([cst.Pass()]),
                ]
            ),
        ),
    ]
    cls_def = cst.ClassDef(
        name=cst.Name(f"Abstract{class_name}DAO"),
        bases=[
            cst.Arg(value=cst.Attribute(value=cst.Name("abc"), attr=cst.Name("ABC")))
        ],
        body=cst.IndentedBlock(body=methods),
    )
    return build_cst_module(
        [
            _doc_stmt(f"Abstract DAO for {name}."),
            cst.EmptyLine(),
            cst.parse_statement("import abc"),
            cst.parse_statement("from typing import Any, List, Optional"),
            cst.EmptyLine(),
            cls_def,
        ]
    )


def _emit_stub_dao_module(name: str, class_name: str, lower_name: str) -> cst.Module:
    """Construct the LibCST Module for a stub DAO file.

    Args:
        name: Raw schema name from OpenAPI.
        class_name: Sanitized Python class identifier.
        lower_name: Sanitized snake_case module suffix.

    Returns:
        A LibCST Module representing `dao/stub_<name>.py`.
    """
    raise_not_impl = cst.SimpleStatementLine(
        [cst.Raise(exc=cst.Call(func=cst.Name("NotImplementedError")))]
    )
    methods: list[cst.BaseStatement] = [
        _doc_stmt(f"Stub implementation for {name} data access."),
        cst.FunctionDef(
            name=cst.Name("get_all"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            returns=cst.Annotation(annotation=cst.parse_expression("List[Any]")),
            body=cst.IndentedBlock(
                body=[_doc_stmt(f"Get all {name}s."), raise_not_impl]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("get_by_id"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("id"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.parse_expression("Optional[Any]")),
            body=cst.IndentedBlock(
                body=[_doc_stmt(f"Get {name} by ID."), raise_not_impl]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("create"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("data"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.Name("Any")),
            body=cst.IndentedBlock(
                body=[_doc_stmt(f"Create a new {name}."), raise_not_impl]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("delete"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("id"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.Name("bool")),
            body=cst.IndentedBlock(
                body=[_doc_stmt(f"Delete a {name} by ID."), raise_not_impl]
            ),
        ),
    ]
    cls_def = cst.ClassDef(
        name=cst.Name(f"Stub{class_name}DAO"),
        bases=[cst.Arg(value=cst.Name(f"Abstract{class_name}DAO"))],
        body=cst.IndentedBlock(body=methods),
    )
    return build_cst_module(
        [
            _doc_stmt(f"Stub DAO for {name}."),
            cst.EmptyLine(),
            cst.parse_statement("from typing import Any, List, Optional"),
            cst.parse_statement(
                f"from .abstract_{lower_name} import Abstract{class_name}DAO"
            ),
            cst.EmptyLine(),
            cls_def,
        ]
    )


def _emit_concrete_dao_module(
    name: str, class_name: str, lower_name: str
) -> cst.Module:
    """Construct the LibCST Module for a concrete SQLAlchemy 2.0 DAO file.

    Args:
        name: Raw schema name from OpenAPI.
        class_name: Sanitized Python class identifier.
        lower_name: Sanitized snake_case module suffix.

    Returns:
        A LibCST Module representing `dao/concrete_<name>.py`.
    """
    methods: list[cst.BaseStatement] = [
        _doc_stmt(f"Concrete SQLAlchemy implementation for {name} data access."),
        cst.FunctionDef(
            name=cst.Name("__init__"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("session"),
                        annotation=cst.Annotation(annotation=cst.Name("Session")),
                    ),
                ]
            ),
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Initialize the concrete {name} DAO."),
                    cst.parse_statement("self.session = session"),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("get_all"),
            params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
            returns=cst.Annotation(annotation=cst.parse_expression("List[Any]")),
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Get all {name}s."),
                    cst.parse_statement(
                        f"return list(self.session.scalars(select({class_name})).all())"
                    ),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("get_by_id"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("id"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.parse_expression("Optional[Any]")),
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Get {name} by ID."),
                    cst.parse_statement(f"return self.session.get({class_name}, id)"),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("create"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("data"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.Name("Any")),
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Create a new {name}."),
                    cst.parse_statement("self.session.add(data)"),
                    cst.parse_statement("self.session.commit()"),
                    cst.parse_statement("self.session.refresh(data)"),
                    cst.parse_statement("return data"),
                ]
            ),
        ),
        cst.FunctionDef(
            name=cst.Name("delete"),
            params=cst.Parameters(
                params=[
                    cst.Param(name=cst.Name("self")),
                    cst.Param(
                        name=cst.Name("id"),
                        annotation=cst.Annotation(annotation=cst.Name("Any")),
                    ),
                ]
            ),
            returns=cst.Annotation(annotation=cst.Name("bool")),
            body=cst.IndentedBlock(
                body=[
                    _doc_stmt(f"Delete a {name} by ID."),
                    cst.parse_statement("obj = self.get_by_id(id)"),
                    cst.If(
                        test=cst.Name("obj"),
                        body=cst.IndentedBlock(
                            body=[
                                cst.parse_statement("self.session.delete(obj)"),
                                cst.parse_statement("self.session.commit()"),
                                cst.parse_statement("return True"),
                            ]
                        ),
                    ),
                    cst.parse_statement("return False"),
                ]
            ),
        ),
    ]
    cls_def = cst.ClassDef(
        name=cst.Name(f"Concrete{class_name}DAO"),
        bases=[cst.Arg(value=cst.Name(f"Abstract{class_name}DAO"))],
        body=cst.IndentedBlock(body=methods),
    )
    return build_cst_module(
        [
            _doc_stmt(f"Concrete DAO for {name}."),
            cst.EmptyLine(),
            cst.parse_statement("from typing import Any, List, Optional"),
            cst.parse_statement("from sqlalchemy import select"),
            cst.parse_statement("from sqlalchemy.orm import Session"),
            cst.parse_statement(
                f"from .abstract_{lower_name} import Abstract{class_name}DAO"
            ),
            cst.parse_statement(f"from models import {class_name}"),
            cst.EmptyLine(),
            cls_def,
        ]
    )


def _build_dao_dispatch_chain(
    model_entries: list[tuple[str, str]], concrete: bool
) -> cst.If:
    """Build an `if / elif / else` LibCST chain dispatching `model_name` to a DAO class.

    Args:
        model_entries: List of `(raw_name, sanitized_class_name)` pairs.
        concrete: If True, instantiate `Concrete<Class>DAO(session)`, else `Stub<Class>DAO()`.

    Returns:
        The constructed LibCST If statement node.
    """
    else_block = cst.Else(
        body=cst.IndentedBlock(
            body=[
                cst.parse_statement("raise ValueError(f'Unknown model: {model_name}')")
            ]
        )
    )
    current_orelse: cst.If | cst.Else = else_block
    for raw_name, class_name in reversed(model_entries):
        if raw_name == class_name:
            cond = cst.parse_expression(f"model_name == {raw_name!r}")
        else:
            cond = cst.parse_expression(f"model_name in ({raw_name!r}, {class_name!r})")
        ret_stmt = (
            cst.parse_statement(f"return Concrete{class_name}DAO(session)")
            if concrete
            else cst.parse_statement(f"return Stub{class_name}DAO()")
        )
        current_orelse = cst.If(
            test=cond,
            body=cst.IndentedBlock(body=[ret_stmt]),
            orelse=current_orelse,
        )
    assert isinstance(current_orelse, cst.If)
    return current_orelse


def emit_dao(spec: OpenAPI) -> dict[str, str]:
    """Generate Data Access Object (DAO) classes from an OpenAPI specification.

    This generates composable files using LibCST AST construction:
    1. Abstract DAO interfaces.
    2. Stub DAOs (raising NotImplementedError).
    3. Concrete DAOs (using SQLAlchemy 2.0 `select` and `Session.get`).
    4. A Dependency Injection/Factory routine (`dao/__init__.py`).

    Args:
        spec: The OpenAPI specification model.

    Returns:
        A dictionary mapping relative file paths to generated Python code.
    """
    if not spec.components or not spec.components.schemas:
        return {}

    files: dict[str, str] = {}
    init_body: list[cst.BaseStatement | cst.EmptyLine] = [
        _doc_stmt("DAO factory module."),
        cst.EmptyLine(),
        cst.parse_statement("import os"),
        cst.parse_statement("from typing import Any, Optional"),
        cst.parse_statement("from sqlalchemy.orm import Session"),
        cst.EmptyLine(),
    ]

    schemas = spec.components.schemas
    model_entries: list[tuple[str, str]] = []

    for name in schemas:
        class_name = sanitize_class_name(name)
        lower_name = sanitize_name(name) or name.lower()
        model_entries.append((name, class_name))

        files[f"dao/abstract_{lower_name}.py"] = _emit_abstract_dao_module(
            name, class_name
        ).code
        files[f"dao/stub_{lower_name}.py"] = _emit_stub_dao_module(
            name, class_name, lower_name
        ).code
        files[f"dao/concrete_{lower_name}.py"] = _emit_concrete_dao_module(
            name, class_name, lower_name
        ).code

        init_body.append(
            cst.parse_statement(f"from .stub_{lower_name} import Stub{class_name}DAO")
        )
        init_body.append(
            cst.parse_statement(
                f"from .concrete_{lower_name} import Concrete{class_name}DAO"
            )
        )

    stub_chain = _build_dao_dispatch_chain(model_entries, concrete=False)
    concrete_chain = _build_dao_dispatch_chain(model_entries, concrete=True)

    get_dao_fn = cst.FunctionDef(
        name=cst.Name("get_dao"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("model_name"),
                    annotation=cst.Annotation(annotation=cst.Name("str")),
                ),
                cst.Param(
                    name=cst.Name("session"),
                    annotation=cst.Annotation(
                        annotation=cst.parse_expression("Optional[Session]")
                    ),
                    default=cst.Name("None"),
                ),
                cst.Param(
                    name=cst.Name("ephemeral"),
                    annotation=cst.Annotation(annotation=cst.Name("bool")),
                    default=cst.Name("False"),
                ),
            ]
        ),
        returns=cst.Annotation(annotation=cst.Name("Any")),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    """Factory routine to resolve the correct DAO.
    Fallback: If no DATABASE_URL and no --ephemeral, return Stub DAOs.
    Active: Otherwise, return Concrete DAOs."""
                ),
                cst.parse_statement(
                    "has_db = bool(os.environ.get('DATABASE_URL')) or ephemeral"
                ),
                cst.If(
                    test=cst.parse_expression("not has_db"),
                    body=cst.IndentedBlock(body=[stub_chain]),
                    orelse=cst.Else(
                        body=cst.IndentedBlock(
                            body=[
                                cst.If(
                                    test=cst.parse_expression("session is None"),
                                    body=cst.IndentedBlock(
                                        body=[
                                            cst.parse_statement(
                                                "raise ValueError('Session is required for Concrete DAOs')"
                                            )
                                        ]
                                    ),
                                ),
                                concrete_chain,
                            ]
                        )
                    ),
                ),
            ]
        ),
    )

    init_body.append(cst.EmptyLine())
    init_body.append(get_dao_fn)
    files["dao/__init__.py"] = build_cst_module(init_body).code

    return files
