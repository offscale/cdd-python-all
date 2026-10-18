"""Module for parsing Arazzo 1.1.0 specifications and resolving linked sourceDescriptions."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from openapi_client.arazzo_models import (
    Arazzo,
    ArazzoParameter,
    FailureAction,
    ReusableObject,
    SuccessAction,
)
from openapi_client.models import OpenAPI, Operation
from openapi_client.openapi.parse import parse_openapi_dict


def decode_json_pointer_token(token: str) -> str:
    """Decode an RFC 6901 JSON Pointer reference token (`~1` -> `/`, `~0` -> `~`).

    Args:
        token: The encoded JSON Pointer token string.

    Returns:
        The decoded token string.
    """
    return token.replace("~1", "/").replace("~0", "~")


def resolve_reusable_parameter(
    item: ArazzoParameter | ReusableObject, spec: Arazzo
) -> ArazzoParameter:
    """Resolve a `ReusableObject` parameter reference against `spec.components.parameters`.

    Args:
        item: Either an inline `ArazzoParameter` or a `ReusableObject` reference.
        spec: The containing `Arazzo` specification.

    Returns:
        The resolved `ArazzoParameter` (with `item.value` override applied if present).
    """
    if isinstance(item, ArazzoParameter):
        return item
    ref = item.reference
    prefix = "$components.parameters."
    if (
        ref.startswith(prefix)
        and spec.components
        and spec.components.parameters
        and ref[len(prefix) :] in spec.components.parameters
    ):
        base_param = spec.components.parameters[ref[len(prefix) :]].model_copy(
            deep=True
        )
        if item.value is not None:
            base_param.value = item.value
        return base_param
    name = ref.split(".")[-1] if "." in ref else ref
    return ArazzoParameter(
        name=name,
        value=item.value if item.value is not None else ref,
    )


def resolve_reusable_success_action(
    item: SuccessAction | ReusableObject, spec: Arazzo
) -> SuccessAction:
    """Resolve a `ReusableObject` success action reference against `spec.components.successActions`.

    Args:
        item: Either an inline `SuccessAction` or a `ReusableObject` reference.
        spec: The containing `Arazzo` specification.

    Returns:
        The resolved `SuccessAction`.
    """
    if isinstance(item, SuccessAction):
        return item
    ref = item.reference
    prefix = "$components.successActions."
    if (
        ref.startswith(prefix)
        and spec.components
        and spec.components.successActions
        and ref[len(prefix) :] in spec.components.successActions
    ):
        return spec.components.successActions[ref[len(prefix) :]].model_copy(deep=True)
    name = ref.split(".")[-1] if "." in ref else ref
    return SuccessAction(name=name, type="end")


def resolve_reusable_failure_action(
    item: FailureAction | ReusableObject, spec: Arazzo
) -> FailureAction:
    """Resolve a `ReusableObject` failure action reference against `spec.components.failureActions`.

    Args:
        item: Either an inline `FailureAction` or a `ReusableObject` reference.
        spec: The containing `Arazzo` specification.

    Returns:
        The resolved `FailureAction`.
    """
    if isinstance(item, FailureAction):
        return item
    ref = item.reference
    prefix = "$components.failureActions."
    if (
        ref.startswith(prefix)
        and spec.components
        and spec.components.failureActions
        and ref[len(prefix) :] in spec.components.failureActions
    ):
        return spec.components.failureActions[ref[len(prefix) :]].model_copy(deep=True)
    name = ref.split(".")[-1] if "." in ref else ref
    return FailureAction(name=name, type="end")


def resolve_arazzo_components(spec_dict: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate an Arazzo dictionary prior to model instantiation.

    Args:
        spec_dict: Raw dictionary parsed from an Arazzo document.

    Returns:
        A deep copy of the Arazzo dictionary with normalized top-level defaults.
    """
    normalized = copy.deepcopy(spec_dict)
    if "arazzo" not in normalized:
        normalized["arazzo"] = "1.1.0"
    if "sourceDescriptions" not in normalized:
        normalized["sourceDescriptions"] = []
    if "workflows" not in normalized:
        normalized["workflows"] = []
    return normalized


def resolve_source_descriptions(
    arazzo_spec: Arazzo,
    base_path: Path = Path("."),
    visited: frozenset[Path] = frozenset(),
) -> dict[str, OpenAPI | Arazzo | dict[str, Any]]:
    """Resolve and load external documents listed in `arazzo_spec.sourceDescriptions`.

    Args:
        arazzo_spec: The parsed `Arazzo` specification model.
        base_path: Base directory path for resolving relative `url` paths.
        visited: Set of already visited file paths to prevent circular resolution.

    Returns:
        A dictionary mapping each `sourceDescription.name` to its parsed `OpenAPI`,
        `Arazzo`, or raw `dict` representation.
    """
    resolved: dict[str, OpenAPI | Arazzo | dict[str, Any]] = {}
    effective_base = base_path
    if arazzo_spec.self_ and not arazzo_spec.self_.startswith(("http://", "https://")):
        self_path = (base_path / arazzo_spec.self_).resolve()
        effective_base = self_path.parent if self_path.is_file() else self_path

    for src in arazzo_spec.sourceDescriptions:
        if src.url.startswith(("http://", "https://")):
            continue
        try:
            target = (effective_base / src.url).resolve()
            if not target.exists() or target in visited:
                continue
            raw_data: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
            src_type = src.type
            if src_type is None:
                if "arazzo" in raw_data:
                    src_type = "arazzo"
                elif "openapi" in raw_data or "swagger" in raw_data:
                    src_type = "openapi"
                else:
                    src_type = "asyncapi"

            if src_type == "openapi":
                resolved[src.name] = parse_openapi_dict(raw_data, target.parent)
            elif src_type == "arazzo":
                nested = parse_arazzo_dict(raw_data, target.parent)
                resolved[src.name] = nested
            else:
                resolved[src.name] = raw_data
        except (OSError, json.JSONDecodeError, ValueError):
            continue

    return resolved


def resolve_operation_path(
    operation_path: str,
    sources: dict[str, OpenAPI | Arazzo | dict[str, Any]],
) -> tuple[str | None, str | None, str | None, Operation | None]:
    """Resolve an Arazzo `operationPath` expression to `(source_name, http_method, path, Operation)`.

    Supports formats like:
    - `"{$sourceDescriptions.petstore.url}#/paths/~1pet~1{petId}/get"`
    - `"petstore#/paths/~1pets/post"`
    - `"#/paths/~1pets/get"`

    Args:
        operation_path: The Arazzo `operationPath` string containing an RFC 6901 JSON Pointer.
        sources: Dictionary of resolved `sourceDescriptions` returned by `resolve_source_descriptions`.

    Returns:
        A 4-tuple of `(source_name, http_method, route_path, Operation)`. Unresolved components are `None`.
    """
    source_name: str | None = None
    pointer = operation_path

    if "#" in operation_path:
        prefix, pointer = operation_path.split("#", 1)
        if "$sourceDescriptions." in prefix:
            after = prefix.split("$sourceDescriptions.", 1)[1]
            source_name = after.split(".", 1)[0].rstrip("}")
        elif prefix in sources:
            source_name = prefix

    tokens = [decode_json_pointer_token(t) for t in pointer.strip("/").split("/") if t]
    route_path: str | None = None
    http_method: str | None = None
    if len(tokens) >= 3 and tokens[0] == "paths":
        route_path = tokens[1]
        http_method = tokens[2].lower()

    target_openapi: OpenAPI | None = None
    src_candidate = sources.get(source_name) if source_name else None
    if isinstance(src_candidate, OpenAPI):
        target_openapi = src_candidate
    else:
        for name, candidate_spec in sources.items():
            if isinstance(candidate_spec, OpenAPI):
                source_name = name
                target_openapi = candidate_spec
                break

    operation: Operation | None = None
    if (
        target_openapi is not None
        and target_openapi.paths
        and route_path is not None
        and http_method is not None
    ):
        path_item = target_openapi.paths.get(route_path)
        if path_item is not None:
            operation = getattr(path_item, http_method, None)

    return source_name, http_method, route_path, operation


def parse_arazzo_dict(spec_dict: dict[str, Any], base_path: Path = Path(".")) -> Arazzo:
    """Parse an Arazzo dictionary into a validated `Arazzo` model.

    Args:
        spec_dict: Raw dictionary parsed from an Arazzo JSON document.
        base_path: Base directory path for resolving external references.

    Returns:
        The validated `Arazzo` model instance.
    """
    _ = base_path
    normalized = resolve_arazzo_components(spec_dict)
    return Arazzo(**normalized)


def parse_arazzo_json(spec_text: str, base_path: Path = Path(".")) -> Arazzo:
    """Parse an Arazzo JSON string into a validated `Arazzo` model.

    Args:
        spec_text: Raw JSON string containing the Arazzo specification.
        base_path: Base directory path for resolving external references.

    Returns:
        The validated `Arazzo` model instance.
    """
    spec_dict: dict[str, Any] = json.loads(spec_text)
    return parse_arazzo_dict(spec_dict, base_path)
