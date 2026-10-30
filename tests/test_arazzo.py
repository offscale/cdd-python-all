"""Tests for Arazzo 1.1.0 models, parser, emitter, runtime expressions, SDK, CLI, Server, and Tests."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import libcst as cst
import pytest

from openapi_client import cli, mcp, sdk
from openapi_client.arazzo.emit import emit_arazzo_dict, emit_arazzo_json
from openapi_client.arazzo.expressions import (
    _evaluate_simple_condition,
    _lookup_case_insensitive,
    _parse_literal_or_expr,
    _traverse_subpath,
    apply_payload_replacements,
    compile_expression_to_cst,
    evaluate_criterion,
    evaluate_json_pointer,
    evaluate_jsonpath,
    evaluate_runtime_expression,
    evaluate_selector,
    evaluate_xpath,
    extract_expression_from_cst,
)
from openapi_client.arazzo.keywords import (
    ARAZZO_1_1_0_FIELDS,
    ARAZZO_RUNTIME_EXPRESSIONS,
)
from openapi_client.arazzo.parse import (
    decode_json_pointer_token,
    resolve_arazzo_components,
    resolve_operation_path,
    resolve_reusable_failure_action,
    resolve_reusable_parameter,
    resolve_reusable_success_action,
    resolve_source_descriptions,
)
from openapi_client.arazzo_models import (
    Arazzo,
    ArazzoComponents,
    ArazzoInfo,
    ArazzoParameter,
    ArazzoRequestBody,
    CriterionObject,
    ExpressionTypeObject,
    FailureAction,
    PayloadReplacement,
    ReusableObject,
    SelectorObject,
    SourceDescription,
    StepObject,
    SuccessAction,
    WorkflowObject,
)
from openapi_client.cli_sdk.emit_arazzo import (
    _schema_prop_to_argparse_type,
    emit_arazzo_cli_code,
)
from openapi_client.cli_sdk.parse_arazzo import (
    _eval_arg_literal,
    extract_arazzo_from_cli_code,
)
from openapi_client.fastapi.emit_arazzo import emit_fastapi_arazzo_routes
from openapi_client.fastapi.parse_arazzo import extract_arazzo_from_fastapi_code
from openapi_client.models import Info, OpenAPI, Operation, PathItem, Reference, Schema
from openapi_client.openapi.emit import emit_openapi_json
from openapi_client.routes.emit import ClientGenerator
from openapi_client.tests.emit_arazzo_tests import (
    _default_input_for_prop,
    emit_arazzo_tests_code,
)
from openapi_client.tests.parse_arazzo_tests import extract_arazzo_from_test_code
from openapi_client.workflows.emit import (
    _get_json_schema_dict,
    _json_type_to_python_type,
    emit_workflows_code,
)
from openapi_client.workflows.parse import (
    _python_type_to_json_type,
    _safe_literal_eval,
    extract_arazzo_from_code,
)


def test_arazzo_keywords_constants() -> None:
    """Verify every field and alias of all Arazzo 1.1.0 models is in ARAZZO_1_1_0_FIELDS."""
    arazzo_models = (
        ArazzoInfo,
        SourceDescription,
        ExpressionTypeObject,
        SelectorObject,
        CriterionObject,
        ArazzoParameter,
        ReusableObject,
        SuccessAction,
        FailureAction,
        PayloadReplacement,
        ArazzoRequestBody,
        StepObject,
        WorkflowObject,
        ArazzoComponents,
        Arazzo,
    )
    field_set = set(ARAZZO_1_1_0_FIELDS)
    for model_cls in arazzo_models:
        for field_name, field_info in model_cls.model_fields.items():
            assert field_name in field_set
            if field_info.alias:
                assert field_info.alias in field_set
    assert "$statusCode" in ARAZZO_RUNTIME_EXPRESSIONS

    from openapi_client.arazzo.parse import parse_arazzo_json

    with pytest.raises(ValueError, match="Invalid Arazzo JSON"):
        parse_arazzo_json("{invalid json")


def test_arazzo_models_validation() -> None:
    """Test Arazzo 1.1.0 Pydantic model validators and error branches."""
    sd = SourceDescription(name="valid_name-1", url="openapi.json", type="openapi")
    assert sd.name == "valid_name-1"

    with pytest.raises(ValueError, match="Invalid SourceDescription name"):
        SourceDescription(name="invalid name!", url="openapi.json")

    sa = SuccessAction(name="ok", type="end")
    assert sa.type == "end"
    with pytest.raises(ValueError, match="cannot specify both"):
        SuccessAction(name="bad", type="goto", workflowId="w1", stepId="s1")

    fa = FailureAction(name="retry1", type="retry", retryAfter=1.5, retryLimit=3)
    assert fa.retryLimit == 3
    with pytest.raises(ValueError, match="cannot specify both"):
        FailureAction(name="bad", type="goto", workflowId="w1", stepId="s1")
    with pytest.raises(ValueError, match="retryAfter"):
        FailureAction(name="bad", type="retry", retryAfter=-1)
    with pytest.raises(ValueError, match="retryLimit"):
        FailureAction(name="bad", type="retry", retryLimit=-2)

    with pytest.raises(ValueError, match="mutually exclusive"):
        StepObject(stepId="s1", operationId="op1", workflowId="wf1")

    with pytest.raises(ValueError, match="Duplicate stepId"):
        WorkflowObject(
            workflowId="wf1",
            steps=[
                StepObject(stepId="dup", operationId="op1"),
                StepObject(stepId="dup", operationId="op2"),
            ],
        )

    with pytest.raises(ValueError, match="Unsupported Arazzo"):
        Arazzo(
            arazzo="2.0.0",
            info=ArazzoInfo(title="T", version="1.0"),
            sourceDescriptions=[],
            workflows=[],
        )

    with pytest.raises(ValueError, match="Duplicate workflowId"):
        Arazzo(
            arazzo="1.0.1",
            info=ArazzoInfo(title="T", version="1.0"),
            sourceDescriptions=[],
            workflows=[
                WorkflowObject(workflowId="w", steps=[StepObject(stepId="s1")]),
                WorkflowObject(workflowId="w", steps=[StepObject(stepId="s2")]),
            ],
        )


def test_arazzo_parse_and_reusables(tmp_path: Path) -> None:
    """Test Arazzo parsing, reusable component resolution, sourceDescriptions, and operationPath.

    Args:
        tmp_path: Temporary directory path fixture.
    """
    assert decode_json_pointer_token("~1pet~1~0id") == "/pet/~id"

    spec = Arazzo(
        arazzo="1.1.0",
        self_="arazzo.json",
        info=ArazzoInfo(title="Pet Flows", version="1.0.0"),
        sourceDescriptions=[
            SourceDescription(name="petstore", url="oas.json", type="openapi"),
            SourceDescription(name="nested_arazzo", url="nested.json"),
            SourceDescription(name="events", url="async.json"),
            SourceDescription(name="remote", url="https://example.com/oas.json"),
            SourceDescription(name="missing", url="does_not_exist.json"),
            SourceDescription(name="broken", url="broken.json"),
        ],
        workflows=[
            WorkflowObject(
                workflowId="wf1",
                steps=[StepObject(stepId="s1", operationId="get_pet")],
            )
        ],
        components=ArazzoComponents(
            parameters={"p1": ArazzoParameter(name="limit", in_="query", value=10)},
            successActions={"sa1": SuccessAction(name="sa1", type="end")},
            failureActions={
                "fa1": FailureAction(name="fa1", type="retry", retryLimit=2)
            },
        ),
    )

    inline_p = ArazzoParameter(name="id", in_="path", value=1)
    assert resolve_reusable_parameter(inline_p, spec) is inline_p
    resolved_p = resolve_reusable_parameter(
        ReusableObject(reference="$components.parameters.p1", value=25), spec
    )
    assert resolved_p.name == "limit"
    assert resolved_p.value == 25
    resolved_p_no_override = resolve_reusable_parameter(
        ReusableObject(reference="$components.parameters.p1"), spec
    )
    assert resolved_p_no_override.value == 10
    fallback_p = resolve_reusable_parameter(
        ReusableObject(reference="unknown_ref"), spec
    )
    assert fallback_p.name == "unknown_ref"

    inline_sa = SuccessAction(name="s", type="end")
    assert resolve_reusable_success_action(inline_sa, spec) is inline_sa
    assert (
        resolve_reusable_success_action(
            ReusableObject(reference="$components.successActions.sa1"), spec
        ).name
        == "sa1"
    )
    assert (
        resolve_reusable_success_action(ReusableObject(reference="other"), spec).name
        == "other"
    )

    inline_fa = FailureAction(name="f", type="end")
    assert resolve_reusable_failure_action(inline_fa, spec) is inline_fa
    assert (
        resolve_reusable_failure_action(
            ReusableObject(reference="$components.failureActions.fa1"), spec
        ).retryLimit
        == 2
    )
    assert (
        resolve_reusable_failure_action(ReusableObject(reference="other"), spec).name
        == "other"
    )

    norm = resolve_arazzo_components({"info": {"title": "T", "version": "1"}})
    assert norm["arazzo"] == "1.1.0"
    assert norm["sourceDescriptions"] == []
    assert norm["workflows"] == []

    (tmp_path / "arazzo.json").write_text("{}", encoding="utf-8")
    (tmp_path / "oas.json").write_text(
        json.dumps(
            {
                "openapi": "3.2.0",
                "info": {"title": "Pets", "version": "1.0"},
                "paths": {
                    "/pet/{petId}": {
                        "get": {
                            "operationId": "getPetById",
                            "responses": {"200": {"description": "ok"}},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "nested.json").write_text(
        emit_arazzo_json(
            Arazzo(
                info=ArazzoInfo(title="Nested", version="1.0"),
                sourceDescriptions=[],
                workflows=[],
            )
        ),
        encoding="utf-8",
    )
    (tmp_path / "async.json").write_text(
        json.dumps(
            {"asyncapi": "3.0.0", "info": {"title": "Events", "version": "1.0"}}
        ),
        encoding="utf-8",
    )
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")

    # Also test automatic openapi detection when type is None
    spec.sourceDescriptions.append(SourceDescription(name="auto_oas", url="oas.json"))
    sources = resolve_source_descriptions(spec, tmp_path)
    assert isinstance(sources["petstore"], OpenAPI)
    assert isinstance(sources["auto_oas"], OpenAPI)
    assert isinstance(sources["nested_arazzo"], Arazzo)
    assert isinstance(sources["events"], dict)

    # Test visited set and directory self_ path
    spec_dir_self = spec.model_copy(deep=True)
    spec_dir_self.self_ = "."
    sources_visited = resolve_source_descriptions(
        spec_dir_self,
        tmp_path,
        visited=frozenset([(tmp_path / "oas.json").resolve()]),
    )
    assert "petstore" not in sources_visited

    # Test resolve_operation_path variants
    src_name, verb, route, op = resolve_operation_path(
        "{$sourceDescriptions.petstore.url}#/paths/~1pet~1{petId}/get", sources
    )
    assert src_name == "petstore"
    assert verb == "get"
    assert route == "/pet/{petId}"
    assert op is not None and op.operationId == "getPetById"

    src2, _verb2, _route2, op2 = resolve_operation_path(
        "petstore#/paths/~1pet~1{petId}/get", sources
    )
    assert src2 == "petstore"
    assert op2 is not None

    src3, verb3, route3, op3 = resolve_operation_path(
        "#/paths/~1unknown/post",
        {"non_oas": {"asyncapi": "3.0"}, "petstore": sources["petstore"]},
    )
    assert src3 == "petstore"
    assert verb3 == "post"
    assert route3 == "/unknown"
    assert op3 is None

    src4, verb4, route4, op4 = resolve_operation_path("invalid_pointer", {})
    assert src4 is None and verb4 is None and route4 is None and op4 is None


def test_arazzo_expressions_and_selectors() -> None:
    """Test JSON Pointer, JSONPath, XPath, Runtime Expressions, Criteria, Replacements, and CST translation."""
    data = {"items": [{"id": 42, "tags": ["a", "b"]}], "meta": {"count": 1}}
    assert evaluate_json_pointer(data, "") == data
    assert evaluate_json_pointer(data, "#/") == data
    assert evaluate_json_pointer(data, "#/items/0/id") == 42
    assert evaluate_json_pointer(data, "/items/99/id") is None
    assert evaluate_json_pointer(data, "/items/notanint/id") is None
    assert evaluate_json_pointer(data, "/missing/key") is None
    assert evaluate_json_pointer(data, "/items/0/id/deeper") is None

    assert evaluate_jsonpath(data, "$") == data
    assert evaluate_jsonpath(data, "$.items[0].id") == 42
    assert evaluate_jsonpath(data, "$items[0]['id']") == 42
    assert evaluate_jsonpath(data, "items[0].id") == 42
    assert evaluate_jsonpath(data, "$.items[*].id") == [42]
    assert evaluate_jsonpath(data, "$.items[*]['id']") == [42]
    assert evaluate_jsonpath(data, "$.meta.*") == [1]
    assert evaluate_jsonpath(42, "$.*") is None
    assert evaluate_jsonpath(data, "$.meta[*]") is None
    assert evaluate_jsonpath(data, "$.items[5]") is None
    assert evaluate_jsonpath(data, "$.meta[0]") is None
    assert evaluate_jsonpath(data, "$.missing") is None
    assert evaluate_jsonpath(data, "$.meta['missing']") is None

    xml_str = "<root><item><id>101</id></item><item><id>102</id></item><status>active</status></root>"
    assert evaluate_xpath(xml_str, "//item/id/text()") == ["101", "102"]
    assert evaluate_xpath(xml_str, "/root/status/text()") == "active"
    assert evaluate_xpath(xml_str, "/status") == "active"
    assert evaluate_xpath(xml_str, "/root") == "root"
    assert evaluate_xpath("<root>hello</root>", "/root/text()") == "hello"
    assert evaluate_xpath(xml_str, "/root/missing") is None
    assert evaluate_xpath("<<<bad xml", "/root") is None
    assert evaluate_xpath(12345, "/root") is None
    import xml.etree.ElementTree as ET

    elem = ET.fromstring("<root><child>val</child></root>")
    assert evaluate_xpath(elem, "./child") == "val"

    assert (
        _lookup_case_insensitive({"Content-Type": "application/json"}, "content-type")
        == "application/json"
    )
    assert _lookup_case_insensitive({"X-Test": "1"}, "X-Test") == "1"
    assert _lookup_case_insensitive({"X-Test": "1"}, "Missing") is None

    assert _traverse_subpath(data, "") == data
    assert _traverse_subpath(data, "#/meta/count") == 1
    assert _traverse_subpath(data, "/meta/count") == 1
    assert _traverse_subpath(data, ".meta.count") == 1
    assert _traverse_subpath(data, "meta.count") == 1

    ctx: dict[str, Any] = {
        "url": "https://api.example.com/v1/pets",
        "method": "POST",
        "statusCode": 201,
        "self": "file:///arazzo.json",
        "request": {
            "header": {"X-Req-Id": "req-1"},
            "query": {"filter": "all"},
            "path": {"petId": "99"},
            "body": {"name": "Rex"},
        },
        "response": {
            "headers": {"X-Rate-Limit": "100"},
            "body": {"id": 99, "status": "available"},
        },
        "message": {
            "header": {"X-Msg": "m1"},
            "payload": {"event": "created"},
        },
        "inputs": {"petName": "Rex", "nested": {"k": "v"}},
        "outputs": {"resultId": 99},
        "steps": {
            "login": {"outputs": {"token": "abc"}, "custom": "val"},
        },
        "workflows": {"auth": {"outputs": {"jwt": "xyz"}}},
        "sourceDescriptions": {"petstore": {"url": "https://petstore.swagger.io"}},
        "components": {"parameters": {"page": 1}},
    }

    assert evaluate_runtime_expression(123, ctx) == 123
    assert evaluate_runtime_expression("literal_text", ctx) == "literal_text"
    assert evaluate_runtime_expression("{$inputs.petName}", ctx) == "Rex"
    assert (
        evaluate_runtime_expression("Bearer {$steps.login.outputs.token}", ctx)
        == "Bearer abc"
    )
    assert evaluate_runtime_expression("$url", ctx) == "https://api.example.com/v1/pets"
    assert evaluate_runtime_expression("$method", ctx) == "POST"
    assert evaluate_runtime_expression("$statusCode", ctx) == 201
    assert evaluate_runtime_expression("$self", ctx) == "file:///arazzo.json"
    assert evaluate_runtime_expression("$request.header.x-req-id", ctx) == "req-1"
    assert evaluate_runtime_expression("$request.query.filter", ctx) == "all"
    assert evaluate_runtime_expression("$request.path.petId", ctx) == "99"
    assert evaluate_runtime_expression("$request.body#/name", ctx) == "Rex"
    assert evaluate_runtime_expression("$response.header.x-rate-limit", ctx) == "100"
    assert evaluate_runtime_expression("$response.body.status", ctx) == "available"
    assert evaluate_runtime_expression("$message.header.x-msg", ctx) == "m1"
    assert evaluate_runtime_expression("$message.payload.event", ctx) == "created"
    assert evaluate_runtime_expression("$request.unknown", ctx) is None
    assert (
        evaluate_runtime_expression("$request.header.missing", {"request": "not_dict"})
        is None
    )
    assert evaluate_runtime_expression("$inputs", ctx) == ctx["inputs"]
    assert evaluate_runtime_expression("$inputs.nested.k", ctx) == "v"
    assert evaluate_runtime_expression("$outputs.resultId", ctx) == 99
    assert evaluate_runtime_expression("$steps.login", ctx) == ctx["steps"]["login"]
    assert evaluate_runtime_expression("$steps.login.outputs.token", ctx) == "abc"
    assert evaluate_runtime_expression("$steps.login.custom", ctx) == "val"
    assert evaluate_runtime_expression("$workflows.auth.outputs.jwt", ctx) == "xyz"
    assert (
        evaluate_runtime_expression("$sourceDescriptions.petstore.url", ctx)
        == "https://petstore.swagger.io"
    )
    assert evaluate_runtime_expression("$components.parameters.page", ctx) == 1
    assert evaluate_runtime_expression("$unknownRoot", ctx) is None

    sel_jp = SelectorObject(context="$response.body", selector="$.status")
    assert evaluate_runtime_expression(sel_jp, ctx) == "available"
    assert evaluate_selector("$statusCode", ctx) == 201
    assert (
        evaluate_selector(
            SelectorObject(
                context="$response.body",
                selector="/id",
                type=ExpressionTypeObject(type="jsonpointer", version="rfc6901"),
            ),
            ctx,
        )
        == 99
    )
    assert (
        evaluate_selector(SelectorObject(context="$response.body", selector="/id"), ctx)
        == 99
    )
    assert (
        evaluate_selector(
            SelectorObject(
                context="$response.body",
                selector="/root/status/text()",
                type="xpath",
            ),
            {"response": {"body": xml_str}},
        )
        == "active"
    )

    # Criteria
    assert _parse_literal_or_expr("'hello'", ctx) == "hello"
    assert _parse_literal_or_expr("true", ctx) is True
    assert _parse_literal_or_expr("false", ctx) is False
    assert _parse_literal_or_expr("null", ctx) is None
    assert _parse_literal_or_expr("42", ctx) == 42
    assert _parse_literal_or_expr("3.14", ctx) == 3.14
    assert _parse_literal_or_expr("bare_token", ctx) == "bare_token"

    assert (
        _evaluate_simple_condition("$statusCode == 200 || $statusCode == 201", ctx, ctx)
        is True
    )
    assert (
        _evaluate_simple_condition("$statusCode >= 200 && $statusCode < 300", ctx, ctx)
        is True
    )
    assert _evaluate_simple_condition("$statusCode != 500", ctx, ctx) is True
    assert _evaluate_simple_condition("$statusCode <= 201", ctx, ctx) is True
    assert _evaluate_simple_condition("$statusCode > 100", ctx, ctx) is True
    assert (
        _evaluate_simple_condition(
            "$.status == 'available'", ctx["response"]["body"], ctx
        )
        is True
    )
    assert _evaluate_simple_condition("/id == 99", ctx["response"]["body"], ctx) is True
    assert _evaluate_simple_condition("$statusCode < 'not_a_number'", ctx, ctx) is False
    assert _evaluate_simple_condition("$.status", ctx["response"]["body"], ctx) is True
    assert _evaluate_simple_condition("$statusCode", ctx, ctx) is True

    assert (
        evaluate_criterion(
            CriterionObject(
                context="$response.body.status", condition="^avail", type="regex"
            ),
            ctx,
        )
        is True
    )
    assert (
        evaluate_criterion(
            CriterionObject(
                context="$response.body",
                condition="$.status == 'available'",
                type="jsonpath",
            ),
            ctx,
        )
        is True
    )
    assert (
        evaluate_criterion(
            CriterionObject(
                context="$response.body",
                condition="$.status",
                type=ExpressionTypeObject(type="jsonpath", version="rfc9535"),
            ),
            ctx,
        )
        is True
    )
    assert (
        evaluate_criterion(
            CriterionObject(
                context="$response.body", condition="//status/text()", type="xpath"
            ),
            {"response": {"body": xml_str}},
        )
        is True
    )
    assert (
        evaluate_criterion(
            CriterionObject(
                context="$response.body",
                condition="/id",
                type=ExpressionTypeObject(type="jsonpointer", version="rfc6901"),
            ),
            ctx,
        )
        is True
    )

    # Payload replacements
    base_payload = {"user": {"name": "old"}, "items": ["x", "y"]}
    assert apply_payload_replacements("primitive", [], ctx) == "primitive"
    replaced = apply_payload_replacements(
        base_payload,
        [
            PayloadReplacement(target="/user/name", value="$inputs.petName"),
            PayloadReplacement(target="$.items[1]", value="$steps.login.outputs.token"),
            PayloadReplacement(target="/", value="ignored"),
            PayloadReplacement(target="/nonexistent/deep/path", value="ignored"),
            PayloadReplacement(target="/items/0/ deeper", value="ignored"),
        ],
        ctx,
    )
    assert replaced["user"]["name"] == "Rex"
    assert replaced["items"][1] == "abc"

    # LibCST compile & extract
    for expr_in in (
        "$inputs.petName",
        "{$inputs.petName}",
        "$steps.login.outputs.token",
        "$steps.login.outputs.user.id",
        "$statusCode",
        "$response.body.status",
        "$url",
        "plain_literal",
        42,
        3.14,
        True,
        False,
        None,
        SelectorObject(context="$response.body", selector="$.id"),
    ):
        cst_node = compile_expression_to_cst(expr_in)
        round_tripped = extract_expression_from_cst(cst_node)
        if expr_in == "{$inputs.petName}":
            assert round_tripped == "$inputs.petName"
        else:
            assert round_tripped == expr_in

    assert extract_expression_from_cst(cst.Name("custom_var")) == "$inputs.custom_var"
    assert extract_expression_from_cst(cst.parse_expression("1 + 2")) == "1 + 2"


def test_workflows_emit_and_parse_comprehensive() -> None:
    """Test emitting and parsing SDK Workflows across all step, input, criteria, and action variants."""
    comp_spec = Arazzo(
        arazzo="1.1.0",
        info=ArazzoInfo(title="Comp", version="1.0"),
        sourceDescriptions=[],
        workflows=[],
        components=ArazzoComponents(
            inputs={
                "SharedInput": {
                    "type": "object",
                    "properties": {"x": {"type": "integer"}},
                }
            }
        ),
    )
    assert _get_json_schema_dict(None, comp_spec) == {}
    assert (
        _get_json_schema_dict({"$ref": "$components.inputs.SharedInput"}, comp_spec)[
            "type"
        ]
        == "object"
    )
    assert (
        _get_json_schema_dict(
            Reference(**{"$ref": "$components.inputs.SharedInput"}), comp_spec
        )["type"]
        == "object"
    )
    assert _get_json_schema_dict(Reference(**{"$ref": "#/other"}), comp_spec) == {
        "$ref": "#/other"
    }
    assert _get_json_schema_dict(Schema(type="object"), comp_spec) == {"type": "object"}

    for j_type, py_type in (
        ("string", "str"),
        ("integer", "int"),
        ("number", "float"),
        ("boolean", "bool"),
        ("array", "list[Any]"),
        ("object", "dict[str, Any]"),
        ("unknown", "Any"),
    ):
        assert _json_type_to_python_type({"type": j_type}) == py_type
        if j_type != "unknown":
            assert _python_type_to_json_type(py_type) == j_type

    assert _safe_literal_eval("invalid syntax ???") is None

    oas = OpenAPI(
        openapi="3.2.0",
        info=Info(title="Pets", version="1.0.0"),
        paths={
            "/pets": PathItem(
                get=Operation(operationId="list_pets", responses={}),
                post=Operation(operationId="create_pet", responses={}),
            )
        },
    )

    spec = Arazzo(
        arazzo="1.1.0",
        self_="arazzo.json",
        info=ArazzoInfo(
            title="Pet Orchestrator",
            summary="Summary text",
            description="Detailed workflow description",
            version="1.1.0",
        ),
        sourceDescriptions=[
            SourceDescription(name="petstore", url="openapi.json", type="openapi"),
            SourceDescription(name="billing", url="billing.json", type="openapi"),
        ],
        workflows=[
            WorkflowObject(
                workflowId="prereq_flow",
                steps=[
                    StepObject(
                        stepId="init_step",
                        operationId="$sourceDescriptions.petstore.list_pets",
                    )
                ],
            ),
            WorkflowObject(
                workflowId="main_flow",
                summary="Main flow",
                description="Runs full lifecycle",
                dependsOn=["prereq_flow"],
                inputs={
                    "type": "object",
                    "properties": {
                        "pet_name": {"type": "string", "description": "Pet name"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["pet_name"],
                },
                parameters=[ArazzoParameter(name="api_key", in_="header", value="k1")],
                successActions=[SuccessAction(name="wf_end", type="end")],
                failureActions=[FailureAction(name="wf_end_fail", type="end")],
                steps=[
                    StepObject(
                        stepId="step_create",
                        operationPath="{$sourceDescriptions.petstore.url}#/paths/~1pets/post",
                        parameters=[
                            ArazzoParameter(
                                name="tag", in_="query", value="$inputs.pet_name"
                            )
                        ],
                        requestBody=ArazzoRequestBody(
                            contentType="application/json",
                            payload={"name": "placeholder"},
                            replacements=[
                                PayloadReplacement(
                                    target="/name", value="$inputs.pet_name"
                                )
                            ],
                        ),
                        timeout=5000,
                        successCriteria=[
                            CriterionObject(
                                context="$statusCode", condition="$statusCode == 200"
                            )
                        ],
                        onSuccess=[
                            SuccessAction(
                                name="early_exit",
                                type="end",
                                criteria=[
                                    CriterionObject(condition="$statusCode == 204")
                                ],
                            ),
                            SuccessAction(
                                name="goto_prereq",
                                type="goto",
                                workflowId="prereq_flow",
                            ),
                        ],
                        onFailure=[
                            FailureAction(
                                name="retry_create",
                                type="retry",
                                retryLimit=2,
                                retryAfter=0.5,
                            )
                        ],
                        outputs={
                            "created_id": "$response.body.id",
                            "selected_name": SelectorObject(
                                context="$response.body", selector="$.name"
                            ),
                        },
                    ),
                    StepObject(
                        stepId="step_raw_path",
                        dependsOn=["step_create"],
                        operationPath="#/paths/~1custom/get",
                        requestBody=ArazzoRequestBody(payload={"simple": True}),
                    ),
                    StepObject(
                        stepId="step_sub_wf",
                        workflowId="prereq_flow",
                    ),
                    StepObject(
                        stepId="step_channel",
                        channelPath="/events/pet",
                        action="send",
                        correlationId="$steps.step_create.outputs.created_id",
                    ),
                    StepObject(
                        stepId="step_bare",
                    ),
                ],
                outputs={
                    "final_id": "$steps.step_create.outputs.created_id",
                    "final_sel": SelectorObject(
                        context="$response.body", selector="$.name"
                    ),
                },
            ),
        ],
    )

    code = emit_workflows_code(spec, {"petstore": oas, "billing": oas})
    assert "class Workflows:" in code
    extracted_with_snap = extract_arazzo_from_code(code, oas)
    assert emit_arazzo_dict(extracted_with_snap) == emit_arazzo_dict(spec)

    # Also test pure AST extraction when __arazzo_spec__ snapshot is removed
    code_no_snap = chr(10).join(
        line for line in code.splitlines() if not line.startswith("    __arazzo_spec__")
    )
    extracted_ast_only = extract_arazzo_from_code(code_no_snap, oas)
    assert len(extracted_ast_only.workflows) == 2
    wf_main = next(
        w for w in extracted_ast_only.workflows if w.workflowId == "main_flow"
    )
    assert wf_main.dependsOn == ["prereq_flow"]
    assert len(wf_main.steps) == 5
    assert wf_main.steps[0].onFailure is not None
    assert isinstance(wf_main.steps[0].onFailure[0], FailureAction)
    assert wf_main.steps[0].onFailure[0].retryLimit == 2
    assert wf_main.steps[1].dependsOn == ["step_create"]
    assert wf_main.steps[2].workflowId == "prereq_flow"
    assert wf_main.steps[3].channelPath == "/events/pet"

    # Execute generated Workflows class dynamically against a mock client
    ns: dict[str, Any] = {}
    exec(code, ns)  # noqa: S102
    workflows_cls = ns["Workflows"]
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status = 400
    mock_resp.data = {"id": "p-1", "name": "Rex"}
    mock_resp.headers = {}
    mock_client.create_pet.return_value = mock_resp
    mock_client.list_pets.return_value = mock_resp
    mock_client.request.return_value = mock_resp
    mock_client.channel.return_value = mock_resp
    mock_client.call_step.return_value = mock_resp
    runner = workflows_cls(
        client=mock_client, clients={"petstore": mock_client, "billing": mock_client}
    )
    assert runner.prereq_flow() == {}

    # Also test parsing a minimal handwritten workflow class with no steps or plain assert
    handwritten = '''
"""Handwritten workflows."""
class CustomWorkflows:
    """Custom class."""
    __arazzo_version__ = "1.1.0"
    __self_uri__ = "custom.json"
    __info__ = {"title": "Custom", "version": "1.0.0"}
    __source_descriptions__ = [{"name": "default", "url": "oas.json", "type": "openapi"}]
    __components__ = {"parameters": {}}

    def empty_flow(self, count: int, ratio: float = 1.5, flag: bool = True, items: list[str] = [], meta: dict[str, str] = {}) -> dict[str, Any]:
        """Run empty flow.

        Returns:
            Outputs.
        """
        assert True
        return {}

    def single_step_flow(self) -> dict[str, Any]:
        """Single step."""
        response = self.client.do_something(q="val")
        assert response.status == 200
        return {}
'''
    hw_spec = extract_arazzo_from_code(handwritten)
    assert len(hw_spec.workflows) == 2
    assert hw_spec.workflows[1].steps[0].successCriteria is not None


def test_cli_sdk_arazzo_emit_and_parse() -> None:
    """Test emitting and parsing CLI workflow runners from Arazzo specifications."""
    assert _schema_prop_to_argparse_type({"type": "integer"}) == "int"
    assert _schema_prop_to_argparse_type({"type": "number"}) == "float"
    assert _schema_prop_to_argparse_type({"type": "string"}) == "str"
    assert _eval_arg_literal(cst.parse_expression("1 + 2")) is None

    spec = Arazzo(
        arazzo="1.1.0",
        info=ArazzoInfo(title="CLI Suite", description="CLI Desc", version="2.0.0"),
        sourceDescriptions=[
            SourceDescription(name="default", url="openapi.json", type="openapi")
        ],
        workflows=[
            WorkflowObject(
                workflowId="wf_one",
                summary="First workflow",
                inputs={
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "default": 1,
                            "description": "Count arg",
                        },
                        "score": {"type": "number"},
                        "label": {"type": "string"},
                    },
                    "required": ["label"],
                },
                steps=[StepObject(stepId="s1", operationId="op1")],
            ),
            WorkflowObject(
                workflowId="wf_two",
                summary="Second workflow",
                steps=[StepObject(stepId="s2", operationId="op2")],
            ),
        ],
    )

    cli_code = emit_arazzo_cli_code(spec)
    assert "add_parser('wf_one'" in cli_code
    assert emit_arazzo_dict(extract_arazzo_from_cli_code(cli_code)) == emit_arazzo_dict(
        spec
    )

    # Test AST extraction without __arazzo_info__ / __source_descriptions__ metadata
    cli_no_meta = chr(10).join(
        line
        for line in cli_code.splitlines()
        if not line.startswith("__arazzo_info__")
        and not line.startswith("__source_descriptions__")
    )
    also_assign = (
        "plain_var = 1"
        + chr(10)
        + "other_var: int = 1"
        + chr(10)
        + "other.set_defaults(_steps=[])"
        + chr(10)
        + cli_no_meta
    )
    extracted_cli = extract_arazzo_from_cli_code(also_assign)
    assert extracted_cli.info.version == "2.0.0"
    assert len(extracted_cli.workflows) == 2
    wf1_inputs = _get_json_schema_dict(extracted_cli.workflows[0].inputs, extracted_cli)
    assert wf1_inputs["properties"]["count"]["type"] == "integer"
    assert wf1_inputs["properties"]["score"]["type"] == "number"
    assert wf1_inputs["required"] == ["label"]


def test_fastapi_and_tests_arazzo_emit_and_parse() -> None:
    """Test FastAPI workflow routes and pytest workflow test suite emission and extraction."""
    for schema_in, expected in (
        ({"example": "ex"}, "ex"),
        ({"default": "def"}, "def"),
        ({"enum": ["e1", "e2"]}, "e1"),
        ({"type": "integer"}, 1),
        ({"type": "number"}, 1.0),
        ({"type": "boolean"}, True),
        ({"type": "array"}, []),
        ({"type": "object"}, {}),
        ({"type": "string"}, "test_value"),
    ):
        assert _default_input_for_prop(schema_in) == expected

    spec = Arazzo(
        arazzo="1.1.0",
        info=ArazzoInfo(title="Server & Test Workflows", version="1.0.0"),
        sourceDescriptions=[
            SourceDescription(name="default", url="openapi.json", type="openapi")
        ],
        workflows=[
            WorkflowObject(
                workflowId="checkout",
                summary="Checkout workflow",
                inputs={
                    "type": "object",
                    "properties": {"item_id": {"type": "integer", "example": 10}},
                },
                steps=[
                    StepObject(stepId="add_cart", operationId="add_to_cart"),
                    StepObject(stepId="pay", operationId="pay_order"),
                ],
                outputs={
                    "order_id": "$steps.pay.outputs.id",
                    "sel_out": SelectorObject(
                        context="$response.body", selector="$.id"
                    ),
                },
            ),
            WorkflowObject(
                workflowId="simple_wf",
                steps=[StepObject(stepId="s1", operationId="op1")],
            ),
        ],
    )

    fastapi_code = emit_fastapi_arazzo_routes(spec)
    assert "@router.post('/checkout')" in fastapi_code
    assert emit_arazzo_dict(
        extract_arazzo_from_fastapi_code(fastapi_code)
    ) == emit_arazzo_dict(spec)

    fastapi_no_meta = "def helper() -> None:\n    pass\n" + chr(10).join(
        line
        for line in fastapi_code.splitlines()
        if not line.startswith("__arazzo_info__")
        and not line.startswith("__source_descriptions__")
    )
    extracted_fa = extract_arazzo_from_fastapi_code(fastapi_no_meta)
    assert len(extracted_fa.workflows) == 2
    assert extracted_fa.workflows[0].workflowId == "checkout"
    assert len(extracted_fa.workflows[0].steps) == 2

    test_code = emit_arazzo_tests_code(spec)
    assert "def test_workflow_checkout()" in test_code
    assert emit_arazzo_dict(
        extract_arazzo_from_test_code(test_code)
    ) == emit_arazzo_dict(spec)

    test_no_meta = chr(10).join(
        line
        for line in test_code.splitlines()
        if not line.startswith("__arazzo_info__")
        and not line.startswith("__source_descriptions__")
    )
    extracted_test = extract_arazzo_from_test_code(test_no_meta)
    assert len(extracted_test.workflows) == 2
    assert extracted_test.workflows[0].workflowId == "checkout"

    # Also test extracting multi-step client.<op> calls from handwritten pytest code
    handwritten_test = '''
"""Handwritten E2E test."""
def helper_not_a_test() -> None:
    """Helper."""
    pass

def test_multi_step_order() -> None:
    """Order flow."""
    r1 = client.create_order()
    assert r1.status_code == 201
    r2 = client.get_order(r1)
    assert r2.status == 200
'''
    hw_extracted = extract_arazzo_from_test_code(handwritten_test)
    assert len(hw_extracted.workflows) == 1
    assert hw_extracted.workflows[0].workflowId == "multi_step_order"
    assert len(hw_extracted.workflows[0].steps) == 2
    assert hw_extracted.workflows[0].steps[1].parameters is not None


def test_cli_sdk_mcp_integration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test CLI commands (`from_arazzo`, `to_arazzo`, `sync`, `to_docs_json`, `mcp`, `serve_json_rpc`).

    Args:
        tmp_path: Temporary directory path fixture.
        monkeypatch: Pytest monkeypatch fixture.
    """
    arazzo_spec = Arazzo(
        arazzo="1.1.0",
        info=ArazzoInfo(title="Integration Flow", version="1.0.0"),
        sourceDescriptions=[
            SourceDescription(name="default", url="openapi.json", type="openapi")
        ],
        workflows=[
            WorkflowObject(
                workflowId="onboard_user",
                summary="Onboard user",
                steps=[StepObject(stepId="create_user", operationId="create_user")],
            )
        ],
    )
    arazzo_file = tmp_path / "arazzo.json"
    arazzo_file.write_text(emit_arazzo_json(arazzo_spec), encoding="utf-8")

    # Test ClientGenerator.generate_workflows_code and generate_from_openapi with --arazzo
    oas_model = OpenAPI(openapi="3.2.0", info=Info(title="Bundled", version="1.0.0"))
    assert ClientGenerator(oas_model).generate_workflows_code() is None
    wf_code = ClientGenerator(oas_model, arazzo_spec).generate_workflows_code()
    assert wf_code is not None and "class Workflows:" in wf_code

    oas_file = tmp_path / "bundled_openapi.json"
    oas_file.write_text(emit_openapi_json(oas_model), encoding="utf-8")
    out_bundled = tmp_path / "out_bundled"
    cli.generate_from_openapi(
        "to_sdk",
        str(oas_file),
        None,
        str(out_bundled),
        no_github_actions=True,
        no_installable_package=True,
        tests=False,
        mcp=False,
        arazzo_path=str(arazzo_file),
    )
    assert (out_bundled / "src" / "client.py").exists()
    assert (out_bundled / "src" / "workflows.py").exists()
    out_sdk = tmp_path / "out_sdk"
    sdk.generate_from_arazzo(
        str(arazzo_file),
        str(out_sdk),
        no_github_actions=True,
        no_installable_package=True,
        tests=True,
        subcommand="to_sdk",
    )
    assert (out_sdk / "src" / "workflows.py").exists()
    assert (out_sdk / "test" / "test_workflows.py").exists()

    # Also test to_sdk and to_sdk_cli with tests=False and non-arazzo JSON in input_dir
    (tmp_path / "non_arazzo.json").write_text('{"openapi": "3.2.0"}', encoding="utf-8")
    out_cli = tmp_path / "out_cli"
    cli.generate_from_arazzo(
        "to_sdk_cli",
        None,
        str(tmp_path),
        str(out_cli),
        no_github_actions=True,
        no_installable_package=True,
        tests=True,
    )
    assert (out_cli / "src" / "cli_workflows.py").exists()
    cli.generate_from_arazzo(
        "to_sdk_cli",
        str(arazzo_file),
        None,
        str(tmp_path / "out_cli_no_tests"),
        no_github_actions=True,
        no_installable_package=True,
        tests=False,
    )

    out_srv = tmp_path / "out_srv"
    cli.generate_from_arazzo(
        "to_server",
        str(arazzo_file),
        None,
        str(out_srv),
        no_github_actions=True,
        no_installable_package=True,
    )
    assert (out_srv / "routes" / "workflows.py").exists()

    monkeypatch.chdir(tmp_path)
    cli.generate_from_arazzo(
        "to_tests",
        str(arazzo_file),
        None,
        "",
        no_github_actions=False,
        no_installable_package=False,
    )

    with pytest.raises(SystemExit):
        cli.generate_from_arazzo("to_sdk", None, None, str(tmp_path))

    # to_arazzo on directory, snapshot directory, CLI file, server file, test file
    extracted_out = tmp_path / "extracted_arazzo.json"
    sdk.generate_to_arazzo(str(out_sdk), str(extracted_out))
    assert extracted_out.exists()

    snap_only_dir = tmp_path / "snap_only"
    snap_only_dir.mkdir()
    (snap_only_dir / "arazzo.snapshot.json").write_text(
        emit_arazzo_json(arazzo_spec), encoding="utf-8"
    )
    cli.generate_to_arazzo(str(snap_only_dir), "")

    cli.generate_to_arazzo(
        str(out_cli / "src" / "cli_workflows.py"), str(extracted_out)
    )
    cli.generate_to_arazzo(str(out_srv / "routes" / "workflows.py"), str(extracted_out))
    cli.generate_to_arazzo(
        str(out_sdk / "test" / "test_workflows.py"), str(extracted_out)
    )

    # generate_docs_json with Arazzo
    docs_out = tmp_path / "arazzo_docs.json"
    cli.generate_docs_json(str(arazzo_file), False, False, str(docs_out))
    arazzo_payload = json.loads(docs_out.read_text(encoding="utf-8"))
    assert set(arazzo_payload.keys()) == {"endpoints", "webhooks", "workflows"}
    assert arazzo_payload["endpoints"] == {}
    assert arazzo_payload["webhooks"] == {}
    arazzo_docs = arazzo_payload["workflows"]
    assert "onboard_user" in arazzo_docs
    wf_entry = arazzo_docs["onboard_user"]
    assert wf_entry["imports"] == "from workflows import Workflows"
    assert wf_entry["wrapper_start"] == "def main():\n    runner = Workflows()"
    assert wf_entry["snippet"] == "result = runner.onboard_user()\nprint(result)"
    assert wf_entry["wrapper_end"] == 'if __name__ == "__main__":\n    main()'
    assert "from workflows import Workflows" in wf_entry["code"]

    docs_dir = tmp_path / "arazzo_docs_dir"
    docs_dir.mkdir()
    cli.generate_docs_json(str(arazzo_file), True, False, str(docs_dir))
    wf_no_imp = json.loads((docs_dir / "docs.json").read_text(encoding="utf-8"))[
        "workflows"
    ]["onboard_user"]
    assert "imports" not in wf_no_imp
    assert "wrapper_start" in wf_no_imp
    assert "wrapper_end" in wf_no_imp

    cli.generate_docs_json(str(arazzo_file), False, True, str(docs_dir))
    wf_no_wrap = json.loads((docs_dir / "docs.json").read_text(encoding="utf-8"))[
        "workflows"
    ]["onboard_user"]
    assert "imports" in wf_no_wrap
    assert "wrapper_start" not in wf_no_wrap
    assert "wrapper_end" not in wf_no_wrap

    cli.generate_docs_json(str(arazzo_file), True, True, None)

    # sync_dir with arazzo
    sync_proj = tmp_path / "sync_proj"
    sync_proj.mkdir()
    (sync_proj / "arazzo.json").write_text(
        emit_arazzo_json(arazzo_spec), encoding="utf-8"
    )
    cli.sync_dir(str(sync_proj), truth="arazzo")
    assert (sync_proj / "workflows.py").exists()
    cli.sync_dir(str(sync_proj), truth="workflow")
    (sync_proj / "workflows.py").unlink()
    cli.sync_dir(str(sync_proj), truth=None)

    # MCP execute_tool for to_arazzo and from_arazzo
    tool_names = [t["name"] for t in mcp.get_tools()]
    assert "to_arazzo" in tool_names and "from_arazzo" in tool_names
    mcp.execute_tool(
        "from_arazzo",
        {"input_path": str(arazzo_file), "output_dir": str(tmp_path / "mcp_out")},
    )
    mcp.execute_tool(
        "to_arazzo",
        {"input_dir": str(out_sdk), "output_path": str(tmp_path / "mcp_arazzo.json")},
    )

    # run_mcp_server with to_arazzo and from_arazzo
    mcp_reqs = [
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "from_arazzo",
                    "arguments": {
                        "input_path": str(arazzo_file),
                        "output_dir": str(tmp_path / "mcp_stdio"),
                    },
                },
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "to_arazzo",
                    "arguments": {
                        "input_path": str(out_sdk),
                        "output_path": str(tmp_path / "mcp_stdio_out.json"),
                    },
                },
            }
        ),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "close"}),
    ]
    monkeypatch.setattr("sys.stdin", io.StringIO(chr(10).join(mcp_reqs) + chr(10)))
    cli.run_mcp_server()

    # CLI main() with from_arazzo and to_arazzo
    monkeypatch.setattr(
        "sys.argv",
        [
            "cdd-python",
            "from_arazzo",
            "to_sdk",
            "-i",
            str(arazzo_file),
            "-o",
            str(tmp_path / "cli_main_out"),
            "--no-github-actions",
            "--no-installable-package",
        ],
    )
    cli.main()

    monkeypatch.setattr("sys.argv", ["cdd-python", "from_arazzo", "to_sdk"])
    with pytest.raises(SystemExit):
        cli.main()

    monkeypatch.setattr(
        "sys.argv",
        [
            "cdd-python",
            "to_arazzo",
            "-i",
            str(out_sdk),
            "-o",
            str(tmp_path / "cli_main_arazzo.json"),
        ],
    )
    cli.main()

    # Test serve_json_rpc with to_arazzo and from_arazzo_to_sdk
    import http.server
    from io import BytesIO

    class MockArazzoHTTPServer:
        """Mock HTTPServer for Arazzo JSON-RPC testing."""

        def __init__(self, addr: Any, handler_class: Any) -> None:
            """Initialize MockArazzoHTTPServer.

            Args:
                addr: Server address tuple.
                handler_class: Request handler class.
            """
            self.addr = addr
            self.handler_class = handler_class

        def serve_forever(self) -> None:
            """Simulate handling to_arazzo and from_arazzo_to_sdk JSON-RPC requests."""
            for payload in (
                {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "from_arazzo_to_sdk",
                    "params": {
                        "input": str(arazzo_file),
                        "output": str(tmp_path / "rpc_sdk"),
                        "no_github_actions": True,
                        "no_installable_package": True,
                    },
                },
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "to_arazzo",
                    "params": {
                        "input": str(out_sdk),
                        "output": str(tmp_path / "rpc_arazzo.json"),
                    },
                },
            ):
                handler = self.handler_class.__new__(self.handler_class)
                raw_bytes = json.dumps(payload).encode("utf-8")
                handler.rfile = BytesIO(raw_bytes)
                handler.wfile = BytesIO()
                handler.headers = {"Content-Length": str(len(raw_bytes))}
                handler.send_response = lambda code: None
                handler.send_header = lambda k, v: None
                handler.end_headers = lambda: None
                handler.do_POST()

    monkeypatch.setattr(http.server, "HTTPServer", MockArazzoHTTPServer)
    cli.serve_json_rpc(8099, "127.0.0.1")


def test_quoted_conditions_and_selector_type_roundtrip() -> None:
    """Test _evaluate_simple_condition with quoted operators and SelectorObject.type AST round-trip."""
    bs = chr(92)
    ctx = {"response": {"body": {"msg": "a || b && c > d"}}, "statusCode": 200}
    crit = CriterionObject(
        condition="$response.body.msg == 'a || b && c > d' && $statusCode == 200"
    )
    assert evaluate_criterion(crit, ctx) is True

    # Escaped quote inside string literal
    ctx_esc = {"response": {"body": {"msg": f"a{bs}'b || c"}}}
    crit_esc = CriterionObject(condition=f"$response.body.msg == 'a{bs}'b || c'")
    assert evaluate_criterion(crit_esc, ctx_esc) is True

    # SelectorObject with string type
    sel_str = SelectorObject(context="$response.body", selector="//id", type="xpath")
    node_str = compile_expression_to_cst(sel_str)
    extracted_str = extract_expression_from_cst(node_str)
    assert isinstance(extracted_str, SelectorObject)
    assert extracted_str.type == "xpath"

    # SelectorObject with ExpressionTypeObject (with and without version)
    sel_eto = SelectorObject(
        context="$response.body",
        selector="$.id",
        type=ExpressionTypeObject(
            type="jsonpath", version="draft-goessner-dispatch-jsonpath-00"
        ),
    )
    node_eto = compile_expression_to_cst(sel_eto)
    extracted_eto = extract_expression_from_cst(node_eto)
    assert isinstance(extracted_eto, SelectorObject)
    assert isinstance(extracted_eto.type, ExpressionTypeObject)
    assert extracted_eto.type.type == "jsonpath"
    assert extracted_eto.type.version == "draft-goessner-dispatch-jsonpath-00"
