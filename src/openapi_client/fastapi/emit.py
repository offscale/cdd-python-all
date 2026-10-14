"""Emit FastAPI server code."""

from __future__ import annotations

from openapi_client.functions.utils import sanitize_name
from openapi_client.models import OpenAPI


def emit_fastapi(spec: OpenAPI) -> dict[str, str]:
    """Generate a FastAPI server from OpenAPI in a modular way.

    Args:
        spec: The OpenAPI specification model.

    Returns:
        A dictionary mapping relative file paths to generated Python code strings.
    """
    files: dict[str, str] = {}
    main_lines = [
        "from __future__ import annotations",
        "import argparse",
        "import os",
        "import uvicorn",
        "from fastapi import FastAPI, HTTPException, Request",
        "from fastapi.middleware.cors import CORSMiddleware",
        "from pydantic import BaseModel",
        "from typing import Any",
        "import models",
        "from db import setup_database, get_db_session",
        "from seeder import seed_database",
        "",
        "app = FastAPI(",
        f"    title={spec.info.title!r},",
        f"    version={spec.info.version!r},",
    ]
    if spec.info.description:
        main_lines.append(f"    description={spec.info.description!r},")
    main_lines.append(")")
    main_lines.append("")

    main_lines.extend(
        [
            "# CORS Configuration",
            "app.add_middleware(",
            "    CORSMiddleware,",
            "    allow_origins=['*'],",
            "    allow_credentials=True,",
            "    allow_methods=['*'],",
            "    allow_headers=['*'],",
            ")",
            "",
            "# Global Configuration Flags",
            "config_flags = {",
            "    'strict_validation': False,",
            "    'enforce_auth': False,",
            "}",
            "",
            "@app.middleware('http')",
            "async def mock_server_middleware(request: Request, call_next):",
            '    """Advanced mock capabilities middleware."""',
            "    if config_flags['strict_validation']:",
            "        if request.method in ('POST', 'PUT', 'PATCH') and not request.headers.get('content-type'):",
            "            from fastapi.responses import JSONResponse",
            "            return JSONResponse(status_code=422, content={'message': 'Missing Content-Type header'})",
            "",
            "    if config_flags['enforce_auth'] and request.url.path != '/_mock/trigger-webhook':",
            "        auth_header = request.headers.get('Authorization')",
            "        if not auth_header or not auth_header.startswith('Bearer mock-token'):",
            "            from fastapi.responses import JSONResponse",
            "            return JSONResponse(status_code=401, content={'message': 'Unauthorized'})",
            "",
            "    return await call_next(request)",
            "",
            "@app.post('/_mock/trigger-webhook/{webhook_name}')",
            "async def trigger_webhook(webhook_name: str):",
            '    """Administrative trigger for outgoing webhooks."""',
            "    return {'status': 'webhook triggered', 'webhook_name': webhook_name}",
            "",
            "# Identity Provider / Auth Server",
            "@app.post('/auth/register')",
            "async def auth_register():",
            '    """Integrated Identity Provider: Register."""',
            "    return {'token': 'mock-token-registered'}",
            "",
            "@app.post('/auth/login')",
            "async def auth_login():",
            '    """Integrated Identity Provider: Login."""',
            "    return {'token': 'mock-token-123'}",
            "",
            "@app.post('/auth/refresh')",
            "async def auth_refresh():",
            '    """Integrated Identity Provider: Refresh."""',
            "    return {'token': 'mock-token-refreshed'}",
            "",
            "@app.post('/auth/logout')",
            "async def auth_logout():",
            '    """Integrated Identity Provider: Logout."""',
            "    return {'status': 'logged out'}",
            "",
        ]
    )

    routers: dict[str, list[str]] = {}
    if spec.paths:
        for path, path_item in spec.paths.items():
            raw_tag = "default"
            parts = path.split("/")
            if len(parts) > 1 and parts[1]:
                raw_tag = parts[1]
            tag = sanitize_name(raw_tag) or "default"

            if tag not in routers:
                routers[tag] = [
                    "from fastapi import APIRouter",
                    "",
                    f"router = APIRouter(tags=[{raw_tag!r}])",
                    "",
                ]

            for method in ["get", "post", "put", "delete", "patch"]:
                operation = getattr(path_item, method, None)
                if operation:
                    raw_op_id = (
                        operation.operationId
                        or f"{method}_{path.replace('/', '_').strip('_')}"
                    )
                    op_id = sanitize_name(raw_op_id)
                    doc_text = (
                        f"{operation.summary or ''}\n    {operation.description or ''}"
                    )

                    routers[tag].append(f"@router.{method}({path!r})")
                    routers[tag].append(f"def {op_id}():")
                    routers[tag].append(f'    """{doc_text}"""')
                    routers[tag].append('    return {"message": "Not implemented"}')
                    routers[tag].append("")

    for tag, router_lines in routers.items():
        files[f"routes/{tag}.py"] = "\n".join(router_lines)

        main_lines.append(f"from routes.{tag} import router as {tag}_router")
        main_lines.append(f"app.include_router({tag}_router)")
        main_lines.append("")

    files["routes/__init__.py"] = ""

    main_lines.extend(
        [
            "def main():",
            '    """',
            "    Main server entrypoint.",
            "    Parses CLI arguments, sets up DAOs and Database, and starts the server.",
            '    """',
            "    parser = argparse.ArgumentParser(description='Run the CDD server.')",
            "    parser.add_argument(",
            "        '--ephemeral', action='store_true',",
            "        help='Triggers the Concrete DAOs and overrides DATABASE_URL with a throwaway database.'",
            "    )",
            "    parser.add_argument(",
            "        '--seed', action='store_true',",
            "        help='Runs the fake data seeder on startup (requires a concrete DB connection).'",
            "    )",
            "    parser.add_argument(",
            "        '--strict-validation', action='store_true',",
            "        help='Enable strict OpenAPI request validation.'",
            "    )",
            "    parser.add_argument(",
            "        '--enforce-auth', action='store_true',",
            "        help='Enforce authentication (mock tokens in ephemeral mode).'",
            "    )",
            "    parser.add_argument(",
            "        '--start-auth-server', action='store_true',",
            "        help='Run the identity provider endpoints.'",
            "    )",
            "    args, unknown = parser.parse_known_args()",
            "",
            "    # Apply Phase 10 Configuration Flags",
            "    config_flags['strict_validation'] = args.strict_validation",
            "    config_flags['enforce_auth'] = args.enforce_auth",
            "    config_flags['start_auth_server'] = args.start_auth_server",
            "",
            "    # 1 & 2. Database Initialization & DAO Resolution",
            "    setup_database(ephemeral=args.ephemeral)",
            "",
            "    # 3. Data Seeding",
            "    has_db = bool(os.environ.get('DATABASE_URL')) or args.ephemeral",
            "    if args.seed and has_db:",
            "        db_gen = get_db_session()",
            "        db = next(db_gen)",
            "        try:",
            "            seed_database(db)",
            "        finally:",
            "            db_gen.close()",
            "",
            "    # 4. Start Listeners",
            "    port = int(os.environ.get('PORT', 8000))",
            "    uvicorn.run(app, host='0.0.0.0', port=port)",
            "",
            "if __name__ == '__main__':",
            "    main()",
            "",
        ]
    )

    files["main.py"] = "\n".join(main_lines)

    return files
