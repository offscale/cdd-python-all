"""Arazzo 1.1.0 Runtime Expression, Selector, Criterion, and LibCST AST compiler engine."""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from typing import Any

import libcst as cst

from openapi_client.arazzo.parse import decode_json_pointer_token
from openapi_client.arazzo_models import (
    CriterionObject,
    ExpressionTypeObject,
    PayloadReplacement,
    SelectorObject,
)

_EMBEDDED_EXPR_RE = re.compile(r"\{(\$[A-Za-z0-9_.\-#/~]+)\}")
_JSONPATH_PART_RE = re.compile(
    r"""\.([A-Za-z0-9_\-*]+)|\[(\d+|\*)\]|\[['"]([^'"]+)['"]\]"""
)


def evaluate_json_pointer(data: Any, pointer: str) -> Any:
    """Evaluate an RFC 6901 JSON Pointer against a nested Python dict/list structure.

    Args:
        data: The root JSON-compatible Python structure.
        pointer: RFC 6901 pointer string (e.g. `"/items/0/id"` or `"#/items/0/id"`).

    Returns:
        The resolved value, or `None` if any segment cannot be resolved.
    """
    clean = pointer.removeprefix("#")
    if not clean or clean == "/":
        return data
    current = data
    for raw_token in clean.lstrip("/").split("/"):
        token = decode_json_pointer_token(raw_token)
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit():
                return None
            idx = int(token)
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        else:
            return None
    return current


def evaluate_jsonpath(data: Any, path_expr: str) -> Any:
    """Evaluate an RFC 9535 JSONPath expression against a Python dict/list structure.

    Args:
        data: The root JSON-compatible Python structure.
        path_expr: JSONPath expression (e.g. `"$.items[0].id"`, `"$.data[*].name"`, `"$['key']"`).

    Returns:
        The resolved value (scalar if single path traversal, list if wildcard `*` used, or `None`).
    """
    expr = path_expr.strip()
    if expr == "$":
        return data
    if expr.startswith("$"):
        expr = expr[1:]
        if not expr.startswith((".", "[")):
            expr = "." + expr
    else:
        expr = "." + expr.lstrip(".")

    current: Any = data
    has_wildcard = False
    for match in _JSONPATH_PART_RE.finditer(expr):
        dot_key, index_token, bracket_key = match.groups()
        if dot_key is not None:
            if dot_key == "*":
                has_wildcard = True
                if isinstance(current, dict):
                    current = list(current.values())
                else:
                    return None
            elif has_wildcard and isinstance(current, list):
                current = [
                    item[dot_key]
                    for item in current
                    if isinstance(item, dict) and dot_key in item
                ]
            elif isinstance(current, dict) and dot_key in current:
                current = current[dot_key]
            else:
                return None
        elif index_token is not None:
            if index_token == "*":
                has_wildcard = True
                if not isinstance(current, list):
                    return None
            elif isinstance(current, list):
                idx = int(index_token)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        else:
            if has_wildcard and isinstance(current, list):
                current = [
                    item[bracket_key]
                    for item in current
                    if isinstance(item, dict) and bracket_key in item
                ]
            elif isinstance(current, dict) and bracket_key in current:
                current = current[bracket_key]
            else:
                return None

    return current


def evaluate_xpath(xml_data: Any, xpath_expr: str) -> Any:
    """Evaluate an XPath expression against an XML string or ElementTree node.

    Args:
        xml_data: XML string or `xml.etree.ElementTree.Element`.
        xpath_expr: XPath expression string (e.g. `".//item/id"`, `"/root/status/text()"`).

    Returns:
        Extracted string text, list of texts, or `None` if unmatched or invalid XML.
    """
    if isinstance(xml_data, str):
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            return None
    elif isinstance(xml_data, ET.Element):
        root = xml_data
    else:
        return None

    clean_expr = xpath_expr.strip()
    wants_text = clean_expr.endswith("/text()")
    if wants_text:
        clean_expr = clean_expr[: -len("/text()")]

    if clean_expr.startswith("//"):
        clean_expr = "." + clean_expr
    elif clean_expr.startswith("/"):
        parts = [p for p in clean_expr.strip("/").split("/") if p]
        if parts and parts[0] == root.tag:
            clean_expr = "./" + "/".join(parts[1:]) if len(parts) > 1 else "."
        else:
            clean_expr = "./" + "/".join(parts)

    if clean_expr in ("", "."):
        return root.text if wants_text else (root.text or root.tag)

    matches = root.findall(clean_expr)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0].text
    return [m.text for m in matches]


def _lookup_case_insensitive(mapping: dict[str, Any], key: str) -> Any:
    """Look up a key in a dictionary case-insensitively (for HTTP headers).

    Args:
        mapping: Dictionary of header names to values.
        key: Target header name.

    Returns:
        The matched header value, or `None` if not present.
    """
    if key in mapping:
        return mapping[key]
    lower_key = key.lower()
    for k, v in mapping.items():
        if k.lower() == lower_key:
            return v
    return None


def _traverse_subpath(data: Any, subpath: str) -> Any:
    """Traverse a `#<json-pointer>` or `.<dot-path>` suffix on a body/payload object.

    Args:
        data: The target body or dictionary object.
        subpath: Suffix beginning with `#`, `.`, or bare path tokens.

    Returns:
        The resolved nested value.
    """
    if not subpath:
        return data
    if subpath.startswith("#"):
        return evaluate_json_pointer(data, subpath[1:])
    if subpath.startswith("/"):
        return evaluate_json_pointer(data, subpath)
    return evaluate_jsonpath(
        data, "$" + (subpath if subpath.startswith(".") else "." + subpath)
    )


def evaluate_runtime_expression(expr: Any, context: dict[str, Any]) -> Any:
    """Evaluate an Arazzo 1.1.0 runtime expression or embedded template against `context`.

    Supports all 17 Arazzo 1.1.0 expression roots (`$url`, `$method`, `$statusCode`,
    `$request.*`, `$response.*`, `$message.*`, `$inputs.*`, `$outputs.*`, `$steps.*`,
    `$workflows.*`, `$sourceDescriptions.*`, `$components.*`, `$self`).

    Args:
        expr: Arazzo runtime expression string, `SelectorObject`, or literal value.
        context: Runtime execution state dictionary.

    Returns:
        The evaluated runtime value.
    """
    if isinstance(expr, SelectorObject):
        return evaluate_selector(expr, context)
    if not isinstance(expr, str):
        return expr

    stripped = expr.strip()
    if (
        stripped.startswith("{$")
        and stripped.endswith("}")
        and stripped.count("{$") == 1
    ):
        stripped = stripped[1:-1]

    if not stripped.startswith("$"):
        if "{$" in expr:
            return _EMBEDDED_EXPR_RE.sub(
                lambda m: str(evaluate_runtime_expression(m.group(1), context) or ""),
                expr,
            )
        return expr

    if stripped == "$url":
        return context.get("url")
    if stripped == "$method":
        return context.get("method")
    if stripped == "$statusCode":
        return context.get("statusCode")
    if stripped == "$self":
        return context.get("self")

    for section in ("request", "response", "message"):
        prefix = f"${section}."
        if stripped.startswith(prefix):
            rest = stripped[len(prefix) :]
            sec_data = context.get(section, {})
            if not isinstance(sec_data, dict):
                return None
            if rest.startswith("header."):
                hdr_name = rest[len("header.") :]
                headers = sec_data.get("header", sec_data.get("headers", {}))
                return (
                    _lookup_case_insensitive(headers, hdr_name)
                    if isinstance(headers, dict)
                    else None
                )
            for sub in ("query.", "path."):
                if rest.startswith(sub):
                    sub_key = sub[:-1]
                    param_name = rest[len(sub) :]
                    params = sec_data.get(sub_key, {})
                    return params.get(param_name) if isinstance(params, dict) else None
            for body_key in ("body", "payload"):
                if rest == body_key or rest.startswith(
                    (f"{body_key}#", f"{body_key}.")
                ):
                    body_val = sec_data.get(body_key)
                    suffix = rest[len(body_key) :]
                    return _traverse_subpath(body_val, suffix)
            return None

    for map_root in ("inputs", "outputs", "sourceDescriptions", "components"):
        prefix = f"${map_root}."
        if stripped == f"${map_root}":
            return context.get(map_root)
        if stripped.startswith(prefix):
            rest = stripped[len(prefix) :]
            return _traverse_subpath(context.get(map_root, {}), rest)

    if stripped.startswith("$steps."):
        rest = stripped[len("$steps.") :]
        parts = rest.split(".", 2)
        step_id = parts[0]
        steps_ctx = context.get("steps", {})
        step_data = steps_ctx.get(step_id, {}) if isinstance(steps_ctx, dict) else {}
        if len(parts) == 1:
            return step_data
        if parts[1] == "outputs" and len(parts) == 3:
            outputs_data = step_data.get("outputs", {})
            return _traverse_subpath(outputs_data, parts[2])
        return _traverse_subpath(step_data, ".".join(parts[1:]))

    if stripped.startswith("$workflows."):
        rest = stripped[len("$workflows.") :]
        return _traverse_subpath(context.get("workflows", {}), rest)

    return None


def evaluate_selector(
    selector: str | SelectorObject, context_data: dict[str, Any]
) -> Any:
    """Evaluate a `SelectorObject` or selector string against `context_data`.

    Args:
        selector: Either a `SelectorObject` or a runtime expression string.
        context_data: Runtime state dictionary.

    Returns:
        The extracted value from the target context.
    """
    if isinstance(selector, str):
        return evaluate_runtime_expression(selector, context_data)

    target = evaluate_runtime_expression(selector.context, context_data)
    dialect: str = "jsonpath"
    if isinstance(selector.type, ExpressionTypeObject):
        dialect = selector.type.type
    elif isinstance(selector.type, str):
        dialect = selector.type
    elif selector.selector.startswith(("/", "#/")):
        dialect = "jsonpointer"

    if dialect == "jsonpointer":
        return evaluate_json_pointer(target, selector.selector)
    if dialect == "xpath":
        return evaluate_xpath(target, selector.selector)
    return evaluate_jsonpath(target, selector.selector)


def _parse_literal_or_expr(token: str, context_data: dict[str, Any]) -> Any:
    """Parse an operand token in a `simple` criterion condition.

    Args:
        token: Stripped operand token string.
        context_data: Runtime state dictionary.

    Returns:
        The evaluated Python value for comparison.
    """
    tok = token.strip()
    if tok.startswith("$"):
        return evaluate_runtime_expression(tok, context_data)
    if (tok.startswith("'") and tok.endswith("'")) or (
        tok.startswith('"') and tok.endswith('"')
    ):
        return tok[1:-1]
    if tok == "true":
        return True
    if tok == "false":
        return False
    if tok in ("null", "None"):
        return None
    if re.match(r"^-?\d+$", tok):
        return int(tok)
    if re.match(r"^-?\d+\.\d+$", tok):
        return float(tok)
    return tok


def _evaluate_simple_condition(
    condition: str, context_val: Any, context_data: dict[str, Any]
) -> bool:
    """Evaluate an Arazzo `simple` criterion condition string.

    Args:
        condition: Condition string supporting `||`, `&&`, and comparison operators.
        context_val: Evaluated value of `criterion.context` (if provided).
        context_data: Full runtime state dictionary.

    Returns:
        `True` if the condition holds, `False` otherwise.
    """
    if "||" in condition:
        return any(
            _evaluate_simple_condition(part, context_val, context_data)
            for part in condition.split("||")
        )
    if "&&" in condition:
        return all(
            _evaluate_simple_condition(part, context_val, context_data)
            for part in condition.split("&&")
        )

    cond = condition.strip()
    for op_str in ("==", "!=", "<=", ">=", "<", ">"):
        if op_str in cond:
            lhs_raw, rhs_raw = cond.split(op_str, 1)
            lhs_tok = lhs_raw.strip()
            if lhs_tok.startswith("$.") and context_val is not None:
                lhs = evaluate_jsonpath(context_val, lhs_tok)
            elif lhs_tok.startswith("/") and context_val is not None:
                lhs = evaluate_json_pointer(context_val, lhs_tok)
            else:
                lhs = _parse_literal_or_expr(lhs_tok, context_data)
            rhs = _parse_literal_or_expr(rhs_raw, context_data)
            try:
                if op_str == "==":
                    return bool(lhs == rhs)
                if op_str == "!=":
                    return bool(lhs != rhs)
                if op_str == "<=":
                    return bool(lhs <= rhs)
                if op_str == ">=":
                    return bool(lhs >= rhs)
                if op_str == "<":
                    return bool(lhs < rhs)
                return bool(lhs > rhs)
            except TypeError:
                return False

    val = (
        evaluate_jsonpath(context_val, cond)
        if cond.startswith("$")
        and not cond.startswith(
            (
                "$statusCode",
                "$response",
                "$request",
                "$inputs",
                "$steps",
                "$outputs",
                "$url",
                "$method",
            )
        )
        else _parse_literal_or_expr(cond, context_data)
    )
    return bool(val)


def evaluate_criterion(
    criterion: CriterionObject, context_data: dict[str, Any]
) -> bool:
    """Evaluate a `CriterionObject` assertion against `context_data`.

    Args:
        criterion: The `CriterionObject` specifying `context`, `condition`, and `type`.
        context_data: Runtime state dictionary.

    Returns:
        `True` if the criterion passes, `False` otherwise.
    """
    context_val = (
        evaluate_runtime_expression(criterion.context, context_data)
        if criterion.context
        else context_data
    )

    ctype: str = (
        criterion.type.type
        if isinstance(criterion.type, ExpressionTypeObject)
        else (criterion.type or "simple")
    )

    if ctype == "regex":
        target_str = "" if context_val is None else str(context_val)
        return re.search(criterion.condition, target_str) is not None
    if (
        ctype == "jsonpath"
        and "==" not in criterion.condition
        and "!=" not in criterion.condition
    ):
        res = evaluate_jsonpath(context_val, criterion.condition)
        return bool(res)
    if ctype == "xpath":
        res = evaluate_xpath(context_val, criterion.condition)
        return bool(res)
    if ctype == "jsonpointer":
        res = evaluate_json_pointer(context_val, criterion.condition)
        return bool(res)
    return _evaluate_simple_condition(criterion.condition, context_val, context_data)


def apply_payload_replacements(
    payload: Any,
    replacements: list[PayloadReplacement] | None,
    context_data: dict[str, Any],
) -> Any:
    """Apply `PayloadReplacement` rules to a deep copy of `payload`.

    Args:
        payload: The base request body payload (dict, list, or primitive).
        replacements: Optional list of `PayloadReplacement` rules.
        context_data: Runtime state dictionary used to resolve `replacement.value`.

    Returns:
        The modified payload with all dynamic replacements applied.
    """
    result = copy.deepcopy(payload)
    if not replacements or not isinstance(result, (dict, list)):
        return result

    for rep in replacements:
        new_val = evaluate_runtime_expression(rep.value, context_data)
        target = rep.target.strip()
        if target.startswith("$."):
            tokens = [
                m.group(1) or m.group(2) or m.group(3)
                for m in _JSONPATH_PART_RE.finditer(target[1:])
            ]
        else:
            clean = target.removeprefix("#")
            tokens = [
                decode_json_pointer_token(t) for t in clean.lstrip("/").split("/") if t
            ]

        if not tokens:
            continue
        curr: Any = result
        for tok in tokens[:-1]:
            if isinstance(curr, dict) and tok in curr:
                curr = curr[tok]
            elif isinstance(curr, list) and tok.isdigit() and int(tok) < len(curr):
                curr = curr[int(tok)]
            else:
                curr = None
                break
        last = tokens[-1]
        if isinstance(curr, dict):
            curr[last] = new_val
        elif isinstance(curr, list) and last.isdigit() and int(last) < len(curr):
            curr[int(last)] = new_val

    return result


def compile_expression_to_cst(expr: Any) -> cst.BaseExpression:
    """Compile an Arazzo runtime expression or literal into a LibCST `BaseExpression` node.

    Args:
        expr: Arazzo runtime expression (`str`, `SelectorObject`, or Python literal).

    Returns:
        A `libcst.BaseExpression` node representing the runtime lookup in generated Python code.
    """
    if isinstance(expr, SelectorObject):
        return cst.parse_expression(
            f"evaluate_selector(SelectorObject(context={expr.context!r}, selector={expr.selector!r}), context)"
        )
    if not isinstance(expr, str):
        return cst.parse_expression(repr(expr))

    stripped = expr.strip()
    if (
        stripped.startswith("{$")
        and stripped.endswith("}")
        and stripped.count("{$") == 1
    ):
        stripped = stripped[1:-1]

    if stripped.startswith("$inputs."):
        field = stripped[len("$inputs.") :]
        return cst.Subscript(
            value=cst.Name("inputs"),
            slice=[cst.SubscriptElement(cst.Index(cst.SimpleString(repr(field))))],
        )
    if stripped.startswith("$steps."):
        parts = stripped[len("$steps.") :].split(".")
        step_id, _, out_key = parts
        return cst.parse_expression(
            f"steps_context[{step_id!r}]['outputs'][{out_key!r}]"
        )
    if stripped == "$statusCode":
        return cst.parse_expression("response.status")
    if stripped.startswith("$response.body."):
        field = stripped[len("$response.body.") :]
        return cst.parse_expression(f"response.data[{field!r}]")
    if stripped.startswith("$") or "{$" in expr:
        return cst.parse_expression(f"evaluate_runtime_expression({expr!r}, context)")
    return cst.SimpleString(repr(expr))


def extract_expression_from_cst(node: cst.BaseExpression) -> Any:
    """Reverse-compile a LibCST `BaseExpression` node back into an Arazzo runtime expression or literal.

    Args:
        node: The LibCST expression node from a workflow method or test AST.

    Returns:
        An Arazzo runtime expression string (e.g. `"$inputs.petId"`), `SelectorObject`, or Python literal.
    """
    code = cst.Module([]).code_for_node(node).strip()

    m_eval = re.match(r"""^evaluate_runtime_expression\(\s*(['"].*?['"])\s*,""", code)
    if m_eval:
        return str(cst.SimpleString(m_eval.group(1)).evaluated_value)

    m_sel = re.match(
        r"""^evaluate_selector\(\s*SelectorObject\(\s*context=(['"].*?['"])\s*,\s*selector=(['"].*?['"])\s*\)""",
        code,
    )
    if m_sel:
        return SelectorObject(
            context=str(cst.SimpleString(m_sel.group(1)).evaluated_value),
            selector=str(cst.SimpleString(m_sel.group(2)).evaluated_value),
        )

    m_in = re.match(r"""^inputs\[\s*(['"])([^'"]+)\1\s*\]$""", code)
    if m_in:
        return f"$inputs.{m_in.group(2)}"

    m_step = re.match(
        r"""^steps_context\[\s*(['"])([^'"]+)\1\s*\]\[\s*['"]outputs['"]\s*\]\[\s*(['"])([^'"]+)\3\s*\]$""",
        code,
    )
    if m_step:
        return f"$steps.{m_step.group(2)}.outputs.{m_step.group(4)}"

    if code in ("response.status", "response.status_code"):
        return "$statusCode"

    m_resp = re.match(
        r"""^response\.(?:data|json\(\))\[\s*(['"])([^'"]+)\1\s*\]$""", code
    )
    if m_resp:
        return f"$response.body.{m_resp.group(2)}"

    if isinstance(node, cst.SimpleString):
        return node.evaluated_value
    if isinstance(node, cst.Integer):
        return int(node.value)
    if isinstance(node, cst.Float):
        return float(node.value)
    if isinstance(node, cst.Name):
        if node.value == "True":
            return True
        if node.value == "False":
            return False
        if node.value == "None":
            return None
        return f"$inputs.{node.value}"
    return code
