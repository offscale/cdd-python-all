"""Emit FastAPI server code."""

from typing import List
from openapi_client.models import OpenAPI


def emit_fastapi(spec: OpenAPI) -> str:
    """Generate a FastAPI server from OpenAPI."""
    lines = [
        "from fastapi import FastAPI, HTTPException",
        "from pydantic import BaseModel",
        "from typing import List, Optional, Any",
        "import models",  # The SQLAlchemy models
        "",
        "app = FastAPI(",
        f'    title="{spec.info.title}",',
        f'    version="{spec.info.version}",',
    ]
    if spec.info.description:
        lines.append(f'    description="{spec.info.description}",')
    lines.append(")")
    lines.append("")

    # We can use the existing Pydantic models from `client.py` or `models.py`
    # Let's assume Pydantic models are in `schemas.py` which we could also generate, but here we just emit routes.

    if spec.paths:
        for path, path_item in spec.paths.items():
            fastapi_path = path.replace("{", "{").replace(
                "}", "}"
            )  # FastAPI uses the same format
            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )

                    lines.append(f"@app.{method}('{fastapi_path}')")
                    lines.append(f"def {op_id}():")
                    lines.append(
                        f'    """{operation.summary or ""}\n    {operation.description or ""}"""'
                    )
                    lines.append(f'    return {{"message": "Not implemented"}}')
                    lines.append("")

    return "\\n".join(lines)
