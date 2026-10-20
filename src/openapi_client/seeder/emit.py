"""Emit fake data seeder module using LibCST AST construction."""

from __future__ import annotations

import keyword
from typing import Any

import libcst as cst

from openapi_client.dao.emit import _doc_stmt
from openapi_client.functions.utils import (
    build_cst_module,
    sanitize_class_name,
    sanitize_name,
)
from openapi_client.models import OpenAPI


def _find_fk_target(
    prop_name: str,
    prop: Any,
    schemas: dict[str, Any],
    current_model: str,
) -> str | None:
    """Detect whether a schema property references another model in `schemas`.

    Args:
        prop_name: The property name on `current_model`.
        prop: The Schema or Reference object for the property.
        schemas: Dictionary of all component schemas.
        current_model: Name of the schema being inspected.

    Returns:
        The referenced parent model name if detected, otherwise `None`.
    """
    ref_str = getattr(prop, "ref", None)
    if isinstance(ref_str, str) and "/" in ref_str:
        target = ref_str.split("/")[-1]
        if target in schemas and target != current_model:
            return target

    lower_prop = prop_name.lower()
    if lower_prop.endswith("_id") and len(lower_prop) > 3:
        prefix = lower_prop[:-3]
        for candidate in schemas:
            if candidate != current_model and sanitize_name(candidate) == prefix:
                return candidate
    return None


def _topological_sort_models(schemas: dict[str, Any]) -> list[str]:
    """Order model names topologically so parent models precede dependent models.

    Args:
        schemas: Mapping of model names to OpenAPI Schema/Reference objects.

    Returns:
        Topologically sorted list of model names.
    """
    model_names = list(schemas.keys())
    deps: dict[str, list[str]] = {name: [] for name in model_names}

    for name, schema in schemas.items():
        props = getattr(schema, "properties", None)
        if isinstance(props, dict):
            for prop_name, prop in props.items():
                target = _find_fk_target(prop_name, prop, schemas, name)
                if target is not None and target not in deps[name]:
                    deps[name].append(target)

    visited: set[str] = set()
    ordered: list[str] = []

    def visit(node: str, visiting: set[str]) -> None:
        """Depth-first topological visit with cycle breaking.

        Args:
            node: Model name currently being visited.
            visiting: Active recursion stack for cycle detection.
        """
        if node in visited or node in visiting:
            return
        visiting.add(node)
        for parent in deps.get(node, []):
            visit(parent, visiting)
        visiting.remove(node)
        visited.add(node)
        ordered.append(node)

    for name in model_names:
        visit(name, set())

    return ordered


def _emit_pool_module() -> cst.Module:
    """Construct the LibCST Module for `mocks/pool.py`.

    Returns:
        A LibCST Module defining `EntityPool`.
    """
    cls_def = cst.ClassDef(
        name=cst.Name("EntityPool"),
        body=cst.IndentedBlock(
            body=[
                _doc_stmt(
                    """Entity Pool to cache IDs of successfully generated records.
    Ensures referential integrity by providing valid parent IDs."""
                ),
                cst.FunctionDef(
                    name=cst.Name("__init__"),
                    params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
                    body=cst.IndentedBlock(
                        body=[
                            _doc_stmt("Initialize the entity pool."),
                            cst.parse_statement(
                                "self.pools: Dict[str, List[Any]] = {}"
                            ),
                        ]
                    ),
                ),
                cst.FunctionDef(
                    name=cst.Name("add"),
                    params=cst.Parameters(
                        params=[
                            cst.Param(name=cst.Name("self")),
                            cst.Param(
                                name=cst.Name("model_name"),
                                annotation=cst.Annotation(cst.Name("str")),
                            ),
                            cst.Param(
                                name=cst.Name("entity_id"),
                                annotation=cst.Annotation(cst.Name("Any")),
                            ),
                        ]
                    ),
                    returns=cst.Annotation(cst.Name("None")),
                    body=cst.IndentedBlock(
                        body=[
                            _doc_stmt("Add an entity ID to the pool."),
                            cst.If(
                                test=cst.parse_expression(
                                    "model_name not in self.pools"
                                ),
                                body=cst.IndentedBlock(
                                    body=[
                                        cst.parse_statement(
                                            "self.pools[model_name] = []"
                                        )
                                    ]
                                ),
                            ),
                            cst.parse_statement(
                                "self.pools[model_name].append(entity_id)"
                            ),
                        ]
                    ),
                ),
                cst.FunctionDef(
                    name=cst.Name("get_random"),
                    params=cst.Parameters(
                        params=[
                            cst.Param(name=cst.Name("self")),
                            cst.Param(
                                name=cst.Name("model_name"),
                                annotation=cst.Annotation(cst.Name("str")),
                            ),
                        ]
                    ),
                    returns=cst.Annotation(cst.Name("Any")),
                    body=cst.IndentedBlock(
                        body=[
                            _doc_stmt("Get a random entity ID from the pool."),
                            cst.If(
                                test=cst.parse_expression(
                                    "model_name not in self.pools or not self.pools[model_name]"
                                ),
                                body=cst.IndentedBlock(
                                    body=[cst.parse_statement("return None")]
                                ),
                            ),
                            cst.parse_statement("import random"),
                            cst.parse_statement(
                                "return random.choice(self.pools[model_name])"
                            ),
                        ]
                    ),
                ),
            ]
        ),
    )
    return build_cst_module(
        [
            cst.parse_statement("from typing import Any, Dict, List"),
            cst.EmptyLine(),
            cls_def,
        ]
    )


def _assign_prop_stmt(prop_name: str, val_expr: str) -> cst.BaseStatement:
    """Create an attribute assignment or `setattr` statement for a model property.

    Args:
        prop_name: Property key from the OpenAPI schema.
        val_expr: Python expression string for the generated fake value.

    Returns:
        A LibCST statement assigning `val_expr` to `obj.<prop_name>`.
    """
    if prop_name.isidentifier() and not keyword.iskeyword(prop_name):
        return cst.parse_statement(f"obj.{prop_name} = {val_expr}")
    return cst.parse_statement(f"setattr(obj, {prop_name!r}, {val_expr})")


def emit_seeder(spec: OpenAPI) -> dict[str, str]:
    """Generate the data seeder for the server using Faker and LibCST AST construction.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        A dictionary mapping relative file paths to generated Python code strings.
    """
    if not spec.components or not spec.components.schemas:
        return {}

    files: dict[str, str] = {}
    files["mocks/pool.py"] = _emit_pool_module().code

    schemas = spec.components.schemas
    ordered_models = _topological_sort_models(schemas)

    factories_body: list[cst.BaseStatement | cst.EmptyLine] = [
        cst.parse_statement("import random"),
        cst.parse_statement("from faker import Faker"),
        cst.parse_statement("from .pool import EntityPool"),
        cst.parse_statement("from models import *"),
        cst.EmptyLine(),
        cst.parse_statement("fake = Faker('en_US')"),
        cst.EmptyLine(),
    ]

    for name in ordered_models:
        class_name = sanitize_class_name(name)
        fn_stmts: list[cst.BaseStatement] = [
            _doc_stmt(
                f"""Create a mapping dictionary for {name} using Faker.
    Uses pool to randomly select valid foreign keys if needed."""
            ),
            cst.parse_statement(f"obj = {class_name}()"),
        ]

        schema = schemas[name]
        if hasattr(schema, "properties") and schema.properties:
            for prop_name, prop in schema.properties.items():
                fk_target = _find_fk_target(prop_name, prop, schemas, name)
                if fk_target is not None:
                    fn_stmts.append(
                        _assign_prop_stmt(prop_name, f"pool.get_random({fk_target!r})")
                    )
                    continue

                p_type = getattr(prop, "type", "string")
                if isinstance(p_type, list):
                    p_type = p_type[0]

                if p_type == "string":
                    if "email" in prop_name.lower():
                        fn_stmts.append(_assign_prop_stmt(prop_name, "fake.email()"))
                    elif "name" in prop_name.lower():
                        fn_stmts.append(_assign_prop_stmt(prop_name, "fake.name()"))
                    elif "phone" in prop_name.lower():
                        fn_stmts.append(
                            _assign_prop_stmt(prop_name, "fake.phone_number()")
                        )
                    else:
                        fn_stmts.append(_assign_prop_stmt(prop_name, "fake.word()"))
                elif p_type == "integer":
                    if prop_name.lower() != "id":
                        fn_stmts.append(
                            _assign_prop_stmt(prop_name, "random.randint(1, 1000)")
                        )
                elif p_type == "number":
                    fn_stmts.append(
                        _assign_prop_stmt(prop_name, "random.random() * 100")
                    )
                elif p_type == "boolean":
                    fn_stmts.append(
                        _assign_prop_stmt(prop_name, "random.choice([True, False])")
                    )
                else:
                    fn_stmts.append(_assign_prop_stmt(prop_name, "'mock_value'"))

        fn_stmts.append(cst.parse_statement("return obj"))
        factories_body.append(
            cst.FunctionDef(
                name=cst.Name(f"factory_{class_name}"),
                params=cst.Parameters(
                    params=[
                        cst.Param(
                            name=cst.Name("pool"),
                            annotation=cst.Annotation(cst.Name("EntityPool")),
                        )
                    ]
                ),
                returns=cst.Annotation(cst.Name(class_name)),
                body=cst.IndentedBlock(body=fn_stmts),
            )
        )
        factories_body.append(cst.EmptyLine())

    files["mocks/factories.py"] = build_cst_module(factories_body).code

    seed_stmts: list[cst.BaseStatement] = [
        _doc_stmt(
            """Batch insertion function to seed the database.
    Maintains topological order and generation ratios."""
        ),
        cst.parse_statement("pool = EntityPool()"),
    ]

    for name in ordered_models:
        class_name = sanitize_class_name(name)
        loop_stmt = cst.For(
            target=cst.Name("_"),
            iter=cst.parse_expression("range(10)"),
            body=cst.IndentedBlock(
                body=[
                    cst.parse_statement(f"obj = factory_{class_name}(pool)"),
                    cst.parse_statement("session.add(obj)"),
                    cst.parse_statement("session.commit()"),
                    cst.parse_statement("session.refresh(obj)"),
                    cst.If(
                        test=cst.parse_expression("hasattr(obj, 'id')"),
                        body=cst.IndentedBlock(
                            body=[cst.parse_statement(f"pool.add({name!r}, obj.id)")]
                        ),
                    ),
                ]
            ),
        )
        seed_stmts.append(loop_stmt)

    seeder_mod = build_cst_module(
        [
            cst.parse_statement("from sqlalchemy.orm import Session"),
            cst.parse_statement("from .pool import EntityPool"),
            cst.parse_statement("from .factories import *"),
            cst.EmptyLine(),
            cst.FunctionDef(
                name=cst.Name("seed_database"),
                params=cst.Parameters(
                    params=[
                        cst.Param(
                            name=cst.Name("session"),
                            annotation=cst.Annotation(cst.Name("Session")),
                        )
                    ]
                ),
                returns=cst.Annotation(cst.Name("None")),
                body=cst.IndentedBlock(body=seed_stmts),
            ),
        ]
    )
    files["mocks/seeder.py"] = seeder_mod.code

    files["mocks/__init__.py"] = cst.Module(
        body=[
            cst.parse_statement("from .pool import EntityPool"),
            cst.parse_statement("from .seeder import seed_database"),
        ]
    ).code
    files["seeder.py"] = cst.Module(
        body=[
            cst.parse_statement("from mocks.pool import EntityPool"),
            cst.parse_statement("from mocks.seeder import seed_database"),
        ]
    ).code

    return files
