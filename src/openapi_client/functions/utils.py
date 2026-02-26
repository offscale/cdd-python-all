"""
Utility functions for generating API client methods.
"""


def get_annotation_for_schema(s) -> str:
    """
    Get the Python type annotation string for a given OpenAPI Schema object.

    Args:
        s: The OpenAPI schema object.

    Returns:
        str: The Python type annotation as a string.
    """
    if not s:
        return "Any"
    t = getattr(s, "type", None)
    if t == "string":
        return "str"
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        items = getattr(s, "items", None)
        item_t = get_annotation_for_schema(items)
        return f"List[{item_t}]"
    if t == "object":
        return "Dict[str, Any]"
    return "Any"
