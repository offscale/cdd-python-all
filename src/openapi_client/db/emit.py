"""Emit database connection module using LibCST AST construction."""

from __future__ import annotations

import libcst as cst

from openapi_client.dao.emit import _doc_stmt
from openapi_client.functions.utils import build_cst_module
from openapi_client.models import OpenAPI


def emit_db(spec: OpenAPI) -> str:
    """Generate database connection configuration for the server using LibCST AST.

    This generates:
    1. Database Connection configuration struct/class (`DBConfig`).
    2. Connection factory reading `DATABASE_URL` or `EPHEMERAL_DB`/flags (`get_engine`).
    3. Initialization routine for DB schema migrations (`init_db`, `setup_database`, `get_db_session`).

    Args:
        spec: The OpenAPI specification model.

    Returns:
        The generated `db.py` Python source code string.
    """
    _ = spec

    db_config_init = cst.FunctionDef(
        name=cst.Name("__init__"),
        params=cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(
                    name=cst.Name("database_url"),
                    annotation=cst.Annotation(
                        annotation=cst.parse_expression("Optional[str]")
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
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    """Initialize configuration.
        :param database_url: The URL to the database.
        :param ephemeral: If True, override URL to use an ephemeral SQLite database."""
                ),
                cst.parse_statement(
                    "self.ephemeral = ephemeral or os.environ.get('EPHEMERAL_DB', '').lower() in ('true', '1', 'yes')"
                ),
                cst.If(
                    test=cst.parse_expression("self.ephemeral"),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement(
                                "self.database_url = 'sqlite:///:memory:'"
                            )
                        ]
                    ),
                    orelse=cst.Else(
                        body=cst.IndentedBlock(
                            body=[
                                cst.parse_statement(
                                    "self.database_url = database_url or os.environ.get('DATABASE_URL', '')"
                                )
                            ]
                        )
                    ),
                ),
            ]
        ),
    )

    db_config_cls = cst.ClassDef(
        name=cst.Name("DBConfig"),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt("Database Connection configuration class."),
                db_config_init,
            ]
        ),
    )

    get_engine_fn = cst.FunctionDef(
        name=cst.Name("get_engine"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("config"),
                    annotation=cst.Annotation(annotation=cst.Name("DBConfig")),
                )
            ]
        ),
        returns=cst.Annotation(annotation=cst.Name("Engine")),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    """Implement the connection factory.
    Reads the configuration and yields the appropriate SQLAlchemy engine."""
                ),
                cst.If(
                    test=cst.parse_expression("not config.database_url"),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement(
                                "raise ValueError('No database URL configured and not running in ephemeral mode.')"
                            )
                        ]
                    ),
                ),
                cst.If(
                    test=cst.parse_expression("config.ephemeral"),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement(
                                "from sqlalchemy.pool import StaticPool"
                            ),
                            cst.parse_statement(
                                "return create_engine(config.database_url, connect_args={'check_same_thread': False}, poolclass=StaticPool)"
                            ),
                        ]
                    ),
                ),
                cst.parse_statement("return create_engine(config.database_url)"),
            ]
        ),
    )

    init_db_fn = cst.FunctionDef(
        name=cst.Name("init_db"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("engine"),
                    annotation=cst.Annotation(annotation=cst.Name("Engine")),
                )
            ]
        ),
        returns=cst.Annotation(annotation=cst.Name("None")),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    """Implement an initialization routine that programmatically executes DB schema migrations."""
                ),
                cst.parse_statement("Base.metadata.create_all(bind=engine)"),
            ]
        ),
    )

    setup_database_fn = cst.FunctionDef(
        name=cst.Name("setup_database"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name("database_url"),
                    annotation=cst.Annotation(
                        annotation=cst.parse_expression("Optional[str]")
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
        returns=cst.Annotation(annotation=cst.Name("None")),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    "Set up the global database connection and run migrations if needed."
                ),
                cst.parse_statement("global engine, SessionLocal"),
                cst.parse_statement(
                    "config = DBConfig(database_url=database_url, ephemeral=ephemeral)"
                ),
                cst.If(
                    test=cst.parse_expression(
                        "not config.database_url and not config.ephemeral"
                    ),
                    body=cst.IndentedBlock(body=[cst.parse_statement("return")]),
                ),
                cst.If(
                    test=cst.parse_expression("engine is not None"),
                    body=cst.IndentedBlock(
                        body=[cst.parse_statement("engine.dispose()")]
                    ),
                ),
                cst.parse_statement("engine = get_engine(config)"),
                cst.parse_statement(
                    "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)"
                ),
                cst.parse_statement("init_db(engine)"),
            ]
        ),
    )

    get_db_session_fn = cst.FunctionDef(
        name=cst.Name("get_db_session"),
        params=cst.Parameters(),
        returns=cst.Annotation(
            annotation=cst.parse_expression("Generator[Session, None, None]")
        ),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt("Get a database session generator."),
                cst.parse_statement("global SessionLocal"),
                cst.If(
                    test=cst.parse_expression("SessionLocal is None"),
                    body=cst.IndentedBlock(
                        body=[
                            cst.parse_statement(
                                "raise RuntimeError('Database is not configured. Call setup_database() first.')"
                            )
                        ]
                    ),
                ),
                cst.parse_statement("db = SessionLocal()"),
                cst.Try(
                    body=cst.IndentedBlock(body=[cst.parse_statement("yield db")]),
                    finalbody=cst.Finally(
                        body=cst.IndentedBlock(body=[cst.parse_statement("db.close()")])
                    ),
                ),
            ]
        ),
    )

    mod = build_cst_module(
        [
            _doc_stmt("Database connection and ephemeral configuration."),
            cst.EmptyLine(),
            cst.parse_statement("import os"),
            cst.parse_statement("from typing import Generator, Optional"),
            cst.parse_statement("from sqlalchemy import create_engine, Engine"),
            cst.parse_statement("from sqlalchemy.orm import sessionmaker, Session"),
            cst.parse_statement("from models import Base"),
            cst.EmptyLine(),
            db_config_cls,
            cst.EmptyLine(),
            get_engine_fn,
            cst.EmptyLine(),
            init_db_fn,
            cst.EmptyLine(),
            cst.parse_statement("engine = None"),
            cst.parse_statement("SessionLocal = None"),
            cst.EmptyLine(),
            setup_database_fn,
            cst.EmptyLine(),
            get_db_session_fn,
        ]
    )
    return mod.code
