"""Tests for CLI commands, environment variables, sync_dir, JSON-RPC, and MCP stdio server."""

from __future__ import annotations

import argparse
import json
import sys
import unittest.mock
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import libcst as cst
import pytest
from pydantic import ValidationError

import openapi_client.cli
from openapi_client import cli
from openapi_client.cli import (
    apply_env_vars_to_parser,
    generate_docs_json,
    generate_from_openapi,
    generate_to_openapi,
    main,
    run_mcp_server,
    sync_dir,
)
from openapi_client.functions.emit import emit_functions
from openapi_client.functions.parse import FunctionExtractor
from openapi_client.mocks.emit import emit_mock_server
from openapi_client.mocks.parse import MockServerExtractor
from openapi_client.models import Components, Info, OpenAPI, Operation, PathItem, Schema
from openapi_client.openapi.parse import parse_openapi_dict
from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy


def test_cli_sync_from_openapi(tmp_path) -> None:
    """Test test_cli_sync_from_openapi.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out"
    generate_from_openapi("to_sdk", str(spec_path), None, str(out_dir))
    generate_from_openapi("to_server", str(spec_path), None, str(out_dir))

    assert (out_dir / "src" / "client.py").exists()
    assert (out_dir / "main.py").exists()


def test_cli_generate_to_openapi(tmp_path) -> None:
    """Test test_cli_generate_to_openapi.

    Args:
        tmp_path: Parameter .
    """
    py_code = "class Client:\n    pass\n"
    py_path = tmp_path / "client.py"
    py_path.write_text(py_code)

    out_spec = tmp_path / "openapi.json"
    generate_to_openapi(str(py_path), str(out_spec))

    assert out_spec.exists()
    data = json.loads(out_spec.read_text())
    assert data["openapi"] == "3.2.0"


def test_cli_main_from_openapi(tmp_path, monkeypatch) -> None:
    """Test test_cli_main_from_openapi.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {"type": "object", "properties": {"name": {"type": "string"}}}
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))
    out_dir = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv",
        [
            "cdd-python",
            "from_openapi",
            "to_sdk",
            "-i",
            str(spec_path),
            "-o",
            str(out_dir),
        ],
    )
    main()
    assert (out_dir / "src" / "client.py").exists()
    assert (out_dir / "src" / "models.py").exists()

    out_dir_cli = tmp_path / "out_cli"
    monkeypatch.setattr(
        "sys.argv",
        [
            "cdd-python",
            "from_openapi",
            "to_sdk_cli",
            "-i",
            str(spec_path),
            "-o",
            str(out_dir_cli),
        ],
    )
    main()
    assert (out_dir_cli / "src" / "client.py").exists()
    assert (out_dir_cli / "src" / "cli_main.py").exists()
    assert (out_dir_cli / "src" / "models.py").exists()


def test_cli_main_to_openapi(tmp_path, monkeypatch) -> None:
    """Test test_cli_main_to_openapi.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """
    py_code = "class Client:\n    pass\n"
    py_path = tmp_path / "client.py"
    py_path.write_text(py_code)
    out_spec = tmp_path / "openapi.json"

    monkeypatch.setattr(
        "sys.argv",
        ["cdd-python", "to_openapi", "-i", str(py_path), "-o", str(out_spec)],
    )
    main()
    assert out_spec.exists()


def test_cli_generate_to_openapi_with_models(tmp_path) -> None:
    """Test test_cli_generate_to_openapi_with_models.

    Args:
        tmp_path: Parameter .
    """
    py_code = "class Client:\n    pass\n"
    py_path = tmp_path / "client.py"
    py_path.write_text(py_code)

    models_code = (
        "from pydantic import BaseModel\nclass Pet(BaseModel):\n    name: str\n"
    )
    models_path = tmp_path / "models.py"
    models_path.write_text(models_code)

    out_spec = tmp_path / "openapi.json"
    generate_to_openapi(str(tmp_path), str(out_spec))

    assert out_spec.exists()
    data = json.loads(out_spec.read_text())
    assert data["openapi"] == "3.2.0"
    assert "Pet" in data["components"]["schemas"]


def test_cli_sync_dir(tmp_path) -> None:
    """Test test_cli_sync_dir.

    Args:
        tmp_path: Parameter .
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # client.py
    client_py = project_dir / "client.py"
    client_py.write_text("""
class Client:
    def get_pets(self):
        pass
""")

    # models.py
    models_py = project_dir / "models.py"
    models_py.write_text("""
from pydantic import BaseModel
class Pet(BaseModel):
    name: str
""")

    # mock_server.py
    mock_py = project_dir / "mock_server.py"
    mock_py.write_text("""
from fastapi import FastAPI
app = FastAPI()

@app.get("/pets")
def get_pets():
    pass
""")

    # test_client.py
    test_py = project_dir / "test_client.py"
    test_py.write_text("""
def test_get_pets() -> None:
    pass
""")

    sync_dir(str(project_dir))

    # verify openapi.json was generated
    openapi_json = project_dir / "openapi.json"
    assert openapi_json.exists()

    data = json.loads(openapi_json.read_text())
    assert "/pets" in data["paths"]
    assert "Pet" in data["components"]["schemas"]

    # run sync_dir again but with only openapi.json
    project_dir2 = tmp_path / "project2"
    project_dir2.mkdir()
    openapi_json2 = project_dir2 / "openapi.json"
    openapi_json2.write_text(json.dumps(data))

    sync_dir(str(project_dir2))
    assert (project_dir2 / "client.py").exists()


def test_cli_main_sync(tmp_path, monkeypatch) -> None:
    """Test test_cli_main_sync.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    client_py = project_dir / "client.py"
    client_py.write_text("class Client:\n    pass\n")

    monkeypatch.setattr("sys.argv", ["cdd-python", "sync", "-i", str(project_dir)])
    main()
    assert (project_dir / "openapi.json").exists()


def test_cli_main_invalid(monkeypatch) -> None:
    """Test test_cli_main_invalid.

    Args:
        monkeypatch: Parameter .
    """
    monkeypatch.setattr("sys.argv", ["cdd-python"])
    with pytest.raises(SystemExit):
        main()


def test_cli_to_docs_json(tmp_path, monkeypatch, capsys) -> None:
    """Test test_cli_to_docs_json.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import json

    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "getPets",
                    "parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}}
                    ],
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    # Test full output
    monkeypatch.setattr(
        "sys.argv", ["cdd-python", "to_docs_json", "-i", str(spec_path)]
    )
    main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "endpoints" in output
    endpoints = output["endpoints"]
    assert "/pets" in endpoints
    assert "get" in endpoints["/pets"]

    code = endpoints["/pets"]["get"]
    assert "import json" in code
    assert "def main():" in code
    assert "client = Client(" in code
    assert "limit = 'example'" in code
    assert "response = client.get_pets(limit=limit)" in code
    assert 'if __name__ == "__main__":' in code

    # Test --no-imports
    monkeypatch.setattr(
        "sys.argv", ["cdd-python", "to_docs_json", "-i", str(spec_path), "--no-imports"]
    )
    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    code = output["endpoints"]["/pets"]["get"]
    assert "import json" not in code
    assert "def main():" in code

    # Test --no-wrapping
    monkeypatch.setattr(
        "sys.argv",
        ["cdd-python", "to_docs_json", "-i", str(spec_path), "--no-wrapping"],
    )
    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    code = output["endpoints"]["/pets"]["get"]
    assert "import json" in code
    assert "def main():" not in code
    assert 'if __name__ == "__main__":' not in code
    assert code.startswith("import json")
    assert "response = client.get_pets(limit=limit)" in code

    # Test both
    monkeypatch.setattr(
        "sys.argv",
        [
            "cdd-python",
            "to_docs_json",
            "-i",
            str(spec_path),
            "--no-imports",
            "--no-wrapping",
        ],
    )
    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    code = output["endpoints"]["/pets"]["get"]
    assert "import json" not in code
    assert "def main():" not in code
    assert "response = client.get_pets(limit=limit)" in code


def test_cli_to_docs_json_no_operation_id(tmp_path, monkeypatch, capsys) -> None:
    """Test test_cli_to_docs_json_no_operation_id.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import json

    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {"/dogs": {"post": {}}},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    # Test full output
    monkeypatch.setattr(
        "sys.argv", ["cdd-python", "to_docs_json", "-i", str(spec_path)]
    )
    main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "endpoints" in output
    endpoints = output["endpoints"]
    assert "/dogs" in endpoints
    assert "post" in endpoints["/dogs"]

    code = endpoints["/dogs"]["post"]
    assert "post_dogs(" in code


def test_generate_from_openapi_input_dir(tmp_path) -> None:
    """Test test_generate_from_openapi_input_dir.

    Args:
        tmp_path: Parameter .
    """
    import json

    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {},
    }
    d = tmp_path / "specs"
    d.mkdir()
    (d / "1.json").write_text(json.dumps(spec))
    out_dir = tmp_path / "out"
    generate_from_openapi("to_sdk_cli", None, str(d), str(out_dir))
    assert (out_dir / "src" / "client.py").exists()
    assert (out_dir / "src" / "cli_main.py").exists()


def test_generate_from_openapi_no_input(capsys) -> None:
    """Test test_generate_from_openapi_no_input.

    Args:
        capsys: Parameter .
    """
    import pytest

    with pytest.raises(SystemExit):
        generate_from_openapi("to_sdk", None, None, "out")


def test_generate_to_openapi_cli(tmp_path) -> None:
    """Test test_generate_to_openapi_cli.

    Args:
        tmp_path: Parameter .
    """
    py_code = 'import argparse\nparser = argparse.ArgumentParser()\nsubparsers = parser.add_subparsers()\nsubparsers.add_parser("test")'
    py_path = tmp_path / "cli_main.py"
    py_path.write_text(py_code)

    out_spec = tmp_path / "openapi.json"
    generate_to_openapi(str(py_path), str(out_spec))

    assert out_spec.exists()
    import json

    data = json.loads(out_spec.read_text())
    assert data["info"]["title"] == "Extracted API"


def test_sync_dir_with_cli(tmp_path) -> None:
    """Test test_sync_dir_with_cli.

    Args:
        tmp_path: Parameter .
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "cli_main.py").write_text(
        'import argparse\nparser = argparse.ArgumentParser()\nsubparsers = parser.add_subparsers()\nsubparsers.add_parser("test")'
    )
    sync_dir(str(project_dir))
    assert (project_dir / "cli_main.py").exists()
    assert (project_dir / "openapi.json").exists()


def test_cli_main_from_openapi_missing_input(monkeypatch, capsys) -> None:
    """Test test_cli_main_from_openapi_missing_input.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import pytest

    monkeypatch.setattr("sys.argv", ["cdd-python", "from_openapi", "to_sdk"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1


def test_cli_main_from_openapi_missing_subcmd(monkeypatch, capsys) -> None:
    """Test test_cli_main_from_openapi_missing_subcmd.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import pytest

    monkeypatch.setattr("sys.argv", ["cdd-python", "from_openapi"])
    with pytest.raises(SystemExit):
        main()


def test_cli_to_docs_json_url(monkeypatch, capsys) -> None:
    """Test test_cli_to_docs_json_url.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import json

    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/pets": {
                "post": {
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    }
                }
            }
        },
    }

    class MockResponse:
        """Test MockResponse."""

        def read(self):
            """Test read."""
            return json.dumps(spec).encode("utf-8")

        def __enter__(self):
            """Test __enter__."""
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            """Test __exit__."""

    def mock_urlopen(req, timeout=30):
        """Test mock_urlopen.

        Args:
            req: The URL Request object.
            timeout: Connection timeout in seconds.
        """
        assert timeout == 30
        return MockResponse()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    monkeypatch.setattr(
        "sys.argv",
        ["cdd-python", "to_docs_json", "-i", "https://example.com/openapi.json"],
    )
    main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    code = output["endpoints"]["/pets"]["post"]
    assert "body = {}" in code
    assert "body=body" in code


def test_generate_from_openapi_tests_flag(tmp_path) -> None:
    """Test test_generate_from_openapi_tests_flag.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out"
    generate_from_openapi("to_sdk", str(spec_path), None, str(out_dir), tests=True)

    assert (out_dir / "src" / "client.py").exists()
    assert (out_dir / "test" / "test_client.py").exists()
    assert (out_dir / "test" / "mock_server.py").exists()


def test_generate_from_openapi_to_sdk_cli_tests(tmp_path) -> None:
    """Test to_sdk_cli with tests.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_cli_tests"
    generate_from_openapi("to_sdk_cli", str(spec_path), None, str(out_dir), tests=True)

    assert (out_dir / "src" / "cli_main.py").exists()
    assert (out_dir / "test" / "test_client.py").exists()
    assert (out_dir / "test" / "mock_server.py").exists()


def test_generate_from_openapi_to_sdk_cli_mcp(tmp_path) -> None:
    """Test to_sdk_cli with mcp.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_cli_mcp"
    generate_from_openapi("to_sdk_cli", str(spec_path), None, str(out_dir), mcp=True)

    assert (out_dir / "src" / "cli_main.py").exists()
    assert (out_dir / "src" / "mcp_server.py").exists()
    assert (out_dir / "src" / "mcp_sse_server.py").exists()
    assert (out_dir / "src" / "mcp_adapter.py").exists()


def test_apply_env_vars_to_parser(monkeypatch, tmp_path) -> None:
    # Setup files
    """Test test_apply_env_vars_to_parser.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    input_file = tmp_path / "dummy.json"
    spec = {"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}
    input_file.write_text(json.dumps(spec))

    monkeypatch.setenv("CDD_INPUT", str(input_file))
    monkeypatch.setenv("CDD_OUTPUT", str(tmp_path))
    monkeypatch.setenv("CDD_NO_GITHUB_ACTIONS", "true")

    monkeypatch.setattr("sys.argv", ["cdd-python", "from_openapi", "to_sdk"])
    main()
    assert (tmp_path / "src" / "client.py").exists()
    assert not (tmp_path / ".github" / "workflows" / "ci.yml").exists()


def test_scaffold_package(monkeypatch, tmp_path) -> None:
    """Test test_scaffold_package.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    spec = {"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}
    input_file = tmp_path / "dummy.json"
    input_file.write_text(json.dumps(spec))

    monkeypatch.setattr(
        "sys.argv",
        [
            "cdd-python",
            "from_openapi",
            "to_sdk",
            "-i",
            str(input_file),
            "-o",
            str(tmp_path),
        ],
    )
    main()
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()


def test_json_rpc_handler_direct(monkeypatch, capsys) -> None:
    # Mock HTTPServer
    """Test test_json_rpc_handler_direct.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """

    class MockHTTPServer:
        """Test MockHTTPServer."""

        def __init__(self, addr, handler_class):
            """Test __init__.

            Args:
                addr: Parameter .
                handler_class: Parameter .
            """
            self.addr = addr
            self.handler_class = handler_class
            self.handled = []

        def serve_forever(self):
            # We trigger one fake request manually
            """Test serve_forever."""
            from io import BytesIO

            class MockRequest:  # pragma: no cover
                """Test MockRequest."""

                def makefile(self, mode, *args, **kwargs):
                    """Test makefile.

                    Args:
                        mode: Parameter .
                        *args: Parameter .
                        **kwargs: Parameter .
                    """
                    if "b" in mode:
                        return BytesIO(b"{}")  # pragma: no cover
                    return BytesIO()

                def sendall(self, data):
                    """Test sendall.

                    Args:
                        data: Parameter .
                    """

            handler = self.handler_class(MockRequest(), self.addr, self)
            handler.rfile = BytesIO(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "to_openapi",
                        "params": {"file": "mock", "output": "mock"},
                        "id": 1,
                    }
                ).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}

            # mock generate_to_openapi
            def mock_generate_to_openapi(p, o):
                """Test mock_generate_to_openapi.

                Args:
                    p: Parameter .
                    o: Parameter .
                """
                print("MOCK SYNC")

            monkeypatch.setattr(
                openapi_client.cli, "generate_to_openapi", mock_generate_to_openapi
            )
            handler.do_POST()

            # test another
            handler.rfile = BytesIO(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "from_openapi_to_sdk",
                        "params": {
                            "input": "mock",
                            "output": "mock",
                            "no_github_actions": True,
                        },
                    }
                ).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}

            def mock_generate_from_openapi(*args, **kwargs):
                """Test mock_generate_from_openapi.

                Args:
                    *args: Parameter .
                    **kwargs: Parameter .
                """
                print("MOCK PROCESS")

            monkeypatch.setattr(
                openapi_client.cli, "generate_from_openapi", mock_generate_from_openapi
            )
            handler.do_POST()

            # test to_docs_json
            handler.rfile = BytesIO(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "to_docs_json",
                        "params": {"input": "mock"},
                    }
                ).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}

            def mock_generate_docs_json(*args, **kwargs):
                """Test mock_generate_docs_json.

                Args:
                    *args: Parameter .
                    **kwargs: Parameter .
                """
                print("MOCK DOCS")

            monkeypatch.setattr(
                openapi_client.cli, "generate_docs_json", mock_generate_docs_json
            )
            handler.do_POST()

            # test sync
            handler.rfile = BytesIO(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "sync", "params": {"dir": "mock"}}
                ).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}

            def mock_sync_dir(*args, **kwargs):
                """Test mock_sync_dir.

                Args:
                    *args: Parameter .
                    **kwargs: Parameter .
                """
                print("MOCK SYNC DIR")

            monkeypatch.setattr(openapi_client.cli, "sync_dir", mock_sync_dir)
            handler.do_POST()

            # test bad json
            handler.rfile = BytesIO(b"bad json")
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}
            handler.do_POST()

            # test missing method
            handler.rfile = BytesIO(
                json.dumps({"jsonrpc": "2.0", "method": "invalid"}).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}
            handler.do_POST()

            # test exception
            handler.rfile = BytesIO(
                json.dumps(
                    {"jsonrpc": "2.0", "method": "sync", "params": {"dir": "mock"}}
                ).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}

            def raise_exc(*args, **kwargs):
                """Test raise_exc.

                Args:
                    *args: Parameter .
                    **kwargs: Parameter .
                """
                raise ValueError("ERROR")

            monkeypatch.setattr(openapi_client.cli, "sync_dir", raise_exc)
            handler.do_POST()

    import http.server

    monkeypatch.setattr(http.server, "HTTPServer", MockHTTPServer)

    monkeypatch.setattr("sys.argv", ["cdd-python", "serve_json_rpc", "--port", "1234"])
    main()

    # Check outputs
    out = capsys.readouterr().out
    assert "MOCK SYNC" in out
    assert "MOCK PROCESS" in out
    assert "MOCK DOCS" in out
    assert "MOCK SYNC DIR" in out


def test_to_docs_json_output_file(tmp_path, monkeypatch) -> None:
    """Test test_to_docs_json_output_file.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """
    spec = {"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}
    input_file = tmp_path / "dummy.json"
    input_file.write_text(json.dumps(spec))

    out_file = tmp_path / "docs.json"
    monkeypatch.setattr(
        "sys.argv",
        ["cdd-python", "to_docs_json", "-i", str(input_file), "-o", str(out_file)],
    )
    main()
    assert out_file.exists()


def test_cli_missing_coverage(monkeypatch, tmp_path) -> None:
    """Test test_cli_missing_coverage.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    import json

    import openapi_client.cli

    # store false via apply_env_vars
    parser = openapi_client.cli.argparse.ArgumentParser()
    parser.add_argument("--test-flag", action="store_false", dest="test_flag")
    monkeypatch.setenv("CDD_TEST_FLAG", "false")
    openapi_client.cli.apply_env_vars_to_parser(parser)

    # generate_from_openapi output_dir="." fallback
    def mock_mkdir(*args, **kwargs):  # pragma: no cover
        """Test mock_mkdir.

        Args:
            *args: Parameter .
            **kwargs: Parameter .
        """

    monkeypatch.chdir(tmp_path)
    spec = {"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}
    input_file = tmp_path / "dummy.json"
    input_file.write_text(json.dumps(spec))
    openapi_client.cli.generate_from_openapi(
        "to_sdk", str(input_file), None, None, True, True
    )

    # generate_to_openapi output_path="openapi.json" fallback
    py_code = "class Client:\n    pass\n"
    py_file = tmp_path / "client.py"
    py_file.write_text(py_code)
    openapi_client.cli.generate_to_openapi(str(py_file), None)


def test_jsonrpc_invalid_rpc(monkeypatch, capsys) -> None:
    """Test test_jsonrpc_invalid_rpc.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import http.server
    import json
    from io import BytesIO

    import openapi_client.cli

    class MockHTTPServer:
        """Test MockHTTPServer."""

        def __init__(self, addr, handler_class):
            """Test __init__.

            Args:
                addr: Parameter .
                handler_class: Parameter .
            """
            self.addr = addr
            self.handler_class = handler_class

        def serve_forever(self):
            """Test serve_forever."""

            class MockRequest:  # pragma: no cover
                """Test MockRequest."""

                def makefile(self, mode, *args, **kwargs):
                    """Test makefile.

                    Args:
                        mode: Parameter .
                        *args: Parameter .
                        **kwargs: Parameter .
                    """
                    if "b" in mode:
                        return BytesIO(b"{}")  # pragma: no cover
                    return BytesIO()

                def sendall(self, data):
                    """Test sendall.

                    Args:
                        data: Parameter .
                    """

            handler = self.handler_class(MockRequest(), self.addr, self)
            handler.rfile = BytesIO(
                json.dumps({"jsonrpc": "1.0", "method": "test"}).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}
            handler.do_POST()

    monkeypatch.setattr(http.server, "HTTPServer", MockHTTPServer)
    monkeypatch.setattr("sys.argv", ["cdd-python", "serve_json_rpc"])
    openapi_client.cli.main()


def test_openapi_client_mcp(monkeypatch) -> None:
    """Test test_openapi_client_mcp.

    Args:
        monkeypatch: Parameter .
    """
    from openapi_client import mcp, sdk

    tools = mcp.get_tools()
    assert len(tools) == 5

    def mock_generate_to_openapi(*args, **kwargs):
        """Test mock_generate_to_openapi.

        Args:
            *args: Parameter .
            **kwargs: Parameter .
        """
        return "to_openapi"

    def mock_generate_from_openapi(*args, **kwargs):
        """Test mock_generate_from_openapi.

        Args:
            *args: Parameter .
            **kwargs: Parameter .
        """
        return "from_openapi"

    def mock_generate_docs_json(*args, **kwargs):
        """Test mock_generate_docs_json.

        Args:
            *args: Parameter .
            **kwargs: Parameter .
        """
        return "docs_json"

    monkeypatch.setattr(sdk, "generate_to_openapi", mock_generate_to_openapi)
    monkeypatch.setattr(sdk, "generate_from_openapi", mock_generate_from_openapi)
    monkeypatch.setattr(sdk, "generate_docs_json", mock_generate_docs_json)

    assert mcp.execute_tool("to_openapi", {}) == "to_openapi"
    assert mcp.execute_tool("from_openapi", {}) == "from_openapi"
    assert mcp.execute_tool("to_docs_json", {}) == "docs_json"

    import pytest

    with pytest.raises(ValueError, match="Unknown tool"):
        mcp.execute_tool("invalid_tool", {})

    res = mcp.get_resources()
    assert len(res) == 1
    assert res[0]["uri"] == "schema://current"

    schema = mcp.read_resource("schema://current")
    assert schema["openapi"] == "3.0.0"

    with pytest.raises(ValueError, match="Resource not found"):
        mcp.read_resource("schema://invalid")


def test_cli_mcp_server(monkeypatch, capsys) -> None:
    """Test test_cli_mcp_server.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    import sys
    from io import StringIO

    # Simulate a stream of stdio inputs
    test_inputs = [
        json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1}),
        json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        ),
        json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {}}
        ),
        json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/progress", "params": {}}
        ),
        "",
        json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 2}),
        json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 3}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "to_openapi",
                    "arguments": {"input_path": ".", "output_path": "openapi.json"},
                },
                "id": 4,
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "from_openapi",
                    "arguments": {
                        "subcommand": "to_sdk",
                        "input_path": "dummy.json",
                        "output_dir": ".",
                    },
                },
                "id": 5,
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "sync_dir", "arguments": {"project_dir": "."}},
                "id": 6,
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "to_docs_json",
                    "arguments": {
                        "input_path": "dummy.json",
                        "output_file": "docs.json",
                    },
                },
                "id": 7,
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "not_a_real_tool"},
                "id": 8,
            }
        ),
        "{ bad_json ",
        json.dumps({"jsonrpc": "2.0", "method": "invalid_method", "id": 9}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "to_openapi",
                    "arguments": {"input_path": ".", "output_path": "openapi.json"},
                },
                "id": 10,
            }
        ),
        json.dumps({"jsonrpc": "2.0", "method": "resources/list", "id": 11}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "schema://current"},
                "id": 12,
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "schema://invalid"},
                "id": 13,
            }
        ),
        json.dumps({"jsonrpc": "2.0", "method": "prompts/list", "id": 15}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "prompts/get",
                "params": {
                    "name": "generate_tests",
                    "arguments": {"component": "client"},
                },
                "id": 16,
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "prompts/get",
                "params": {"name": "unknown_prompt"},
                "id": 17,
            }
        ),
        json.dumps({"jsonrpc": "2.0", "method": "close", "id": 14}),
        "",
    ]

    mock_stdin = StringIO("\n".join(test_inputs) + "\n")
    monkeypatch.setattr(sys, "stdin", mock_stdin)

    def mock_generate_to_openapi(input_path, output_path):
        """Test mock_generate_to_openapi.

        Args:
            input_path: Parameter .
            output_path: Parameter .
        """
        if hasattr(mock_generate_to_openapi, "called"):
            raise RuntimeError("Mock generic error")
        mock_generate_to_openapi.called = True
        print("MOCK GENERATE TO OPENAPI")
        raise ValueError("Mock error")

    def mock_generate_from_openapi(*args, **kwargs):
        """Test mock_generate_from_openapi.

        Args:
            *args: Parameter .
            **kwargs: Parameter .
        """
        print("MOCK GENERATE FROM OPENAPI")

    def mock_sync_dir(project_dir):
        """Test mock_sync_dir.

        Args:
            project_dir: Parameter .
        """
        print("MOCK SYNC DIR")

    def mock_generate_docs_json(*args, **kwargs):
        """Test mock_generate_docs_json.

        Args:
            *args: Parameter .
            **kwargs: Parameter .
        """
        print("MOCK GENERATE DOCS")

    monkeypatch.setattr(
        openapi_client.cli, "generate_to_openapi", mock_generate_to_openapi
    )
    monkeypatch.setattr(
        openapi_client.cli, "generate_from_openapi", mock_generate_from_openapi
    )
    monkeypatch.setattr(openapi_client.cli, "sync_dir", mock_sync_dir)
    monkeypatch.setattr(
        openapi_client.cli, "generate_docs_json", mock_generate_docs_json
    )

    monkeypatch.setattr("sys.argv", ["cdd-python", "mcp"])
    openapi_client.cli.main()

    out = capsys.readouterr().out

    assert "protocolVersion" in out
    assert "tools" in out
    assert "MOCK GENERATE FROM OPENAPI" in out
    assert "MOCK SYNC DIR" in out
    assert "MOCK GENERATE DOCS" in out
    assert "-32601" in out


def test_cli_output_file(tmp_path) -> None:
    """Test test_cli_output_file.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_file = tmp_path / "out" / "client.py"
    generate_from_openapi("to_sdk", str(spec_path), None, str(out_file))

    assert (tmp_path / "out" / "src" / "client.py").exists()


def test_cli_to_server_with_models(tmp_path) -> None:
    """Test test_cli_to_server_with_models.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_server"
    generate_from_openapi("to_server", str(spec_path), None, str(out_dir))

    assert (out_dir / "main.py").exists()
    assert (out_dir / "models" / "pet.py").exists()


def test_cli_to_sdk_cli_cdd(tmp_path, monkeypatch) -> None:
    """Test test_cli_to_sdk_cli_cdd.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "getPets",
                    "summary": "Get all pets",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema_": {"type": ["integer", "null"]},
                            "required": True,
                        }
                    ],
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_sdk_cli"
    generate_from_openapi("to_sdk_cli", str(spec_path), None, str(out_dir), tests=True)

    assert (out_dir / "src" / "cli_main.py").exists()
    cli_code = (out_dir / "src" / "cli_main.py").read_text(encoding="utf-8")
    assert "def set_cli_args_get_pets" in cli_code


def test_cli_to_server_sqlalchemy_ast_types(tmp_path) -> None:
    """Test test_cli_to_server_sqlalchemy_ast_types.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "id": {"type": ["integer"]},
                        "name": {"type": ["string", "null"]},
                    },
                }
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out_server2"
    generate_from_openapi("to_server", str(spec_path), None, str(out_dir))
    assert (out_dir / "models" / "pet.py").exists()


def test_fastapi_emit(tmp_path) -> None:
    """Test test_fastapi_emit.

    Args:
        tmp_path: Parameter .
    """
    from openapi_client.fastapi.emit import emit_fastapi
    from openapi_client.models import Info, OpenAPI, Operation, PathItem

    spec = OpenAPI(
        openapi="3.0.0",
        info=Info(title="Test", version="1.0", description="Desc"),
        paths={
            "/test": PathItem(
                get=Operation(summary="sum", description="desc"),
                post=Operation(operationId="post_test"),
            )
        },
    )
    code = emit_fastapi(spec)
    assert "main.py" in code
    assert "@router.get('/test')" in code["routes/test.py"]

    assert "def get_test():" in code["routes/test.py"]
    assert "def post_test():" in code["routes/test.py"]


def test_fastapi_parse() -> None:
    """Test test_fastapi_parse."""
    import libcst as cst

    from openapi_client.fastapi.parse import extract_fastapi_from_ast
    from openapi_client.models import OpenAPI

    code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/hello")
def hello():
    pass
"""
    module = cst.parse_module(code)
    spec = OpenAPI(openapi="3.0.0", info={"title": "T", "version": "1"})
    extract_fastapi_from_ast(module, spec)
    assert "/hello" in spec.paths
    assert spec.paths["/hello"].get is not None
    assert spec.paths["/hello"].get.operationId == "hello"


def test_sqlalchemy_cdd_emit_no_components(tmp_path) -> None:
    """Test test_sqlalchemy_cdd_emit_no_components.

    Args:
        tmp_path: Parameter .
    """
    from openapi_client.models import OpenAPI
    from openapi_client.sqlalchemy_cdd.emit import emit_sqlalchemy

    spec = OpenAPI(openapi="3.0.0", info={"title": "Test", "version": "1.0"})
    res = emit_sqlalchemy(spec)
    assert res == {}


def test_snapshot_roundtrip(tmp_path) -> None:
    """Test that a snapshot is created during to_sdk and correctly parsed during from_sdk.

    Args:
        tmp_path: Parameter .
    """
    spec_json = {
        "openapi": "3.2.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {},
        "components": {"schemas": {}},
        "webhooks": {
            "myWebhook": {
                "post": {
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    },
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    in_file = tmp_path / "in.json"
    in_file.write_text(json.dumps(spec_json))

    out_sdk_dir = tmp_path / "sdk"
    out_sdk_dir.mkdir()

    # Run to_sdk
    generate_from_openapi("to_sdk", str(in_file), None, str(out_sdk_dir))

    assert (out_sdk_dir / "src" / "openapi.snapshot.json").exists()

    # Run generate_to_openapi (to_openapi)
    out_spec = tmp_path / "out.json"
    generate_to_openapi(out_sdk_dir, out_spec)

    out_spec_parsed = json.loads(out_spec.read_text())
    assert "webhooks" in out_spec_parsed
    assert "myWebhook" in out_spec_parsed["webhooks"]


def test_sync_dir_output_flag(tmp_path: Path) -> None:
    """Test sync_dir with an explicit output_dir argument.

    Args:
        tmp_path: Parameter .
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    openapi_json = project_dir / "openapi.json"
    openapi_json.write_text(
        '{"openapi": "3.2.0", "info": {"title": "Test", "version": "1"}, "paths": {}, "components": {"schemas": {}}}',
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"

    sync_dir(str(project_dir), output_dir=str(out_dir))

    assert (out_dir / "openapi.json").exists()
    assert (out_dir / "client.py").exists()


def test_cli_main_sync_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test `cdd-python sync -i <dir> -o <out>` via main CLI entrypoint.

    Args:
        tmp_path: Parameter .
        monkeypatch: Parameter .
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    openapi_json = project_dir / "openapi.json"
    openapi_json.write_text(
        '{"openapi": "3.2.0", "info": {"title": "Test", "version": "1"}, "paths": {}, "components": {"schemas": {}}}',
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv", ["cdd-python", "sync", "-i", str(project_dir), "-o", str(out_dir)]
    )

    main()

    assert (out_dir / "openapi.json").exists()
    assert (out_dir / "client.py").exists()


def test_generate_to_openapi_dir(tmp_path: Path) -> None:
    """Test test_generate_to_openapi_dir.

    Args:
        tmp_path: Parameter .
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    client_py = project_dir / "client.py"
    client_py.write_text("class Client:\n    pass\n")

    mock_py = project_dir / "mock_server.py"
    mock_py.write_text("def test_mock() -> None:\n    pass\n")

    test_py = project_dir / "test_client.py"
    test_py.write_text("def test_client() -> None:\n    pass\n")

    cli_py = project_dir / "cli_main.py"
    cli_py.write_text("import argparse\n")

    out_file = tmp_path / "openapi.json"
    generate_to_openapi(str(project_dir), str(out_file))

    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "openapi" in data


def test_generate_to_openapi_empty_output(tmp_path: Path) -> None:
    """Test test_generate_to_openapi_empty_output.

    Args:
        tmp_path: Parameter .
    """
    # Test when output_path is not given (it defaults to "openapi.json")
    """Test test_generate_to_openapi_empty_output."""
    import os

    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        project_dir = tmp_path / "project2"
        project_dir.mkdir()
        client_py = project_dir / "client.py"
        client_py.write_text("class Client:\n    pass\n")
        generate_to_openapi(str(project_dir), "")
        assert (tmp_path / "openapi.json").exists()
    finally:
        os.chdir(old_cwd)


def test_serve_json_rpc_break(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test run_mcp_server termination conditions on empty lines followed by close.

    Args:
        monkeypatch: Parameter .
        capsys: Parameter .
    """
    inputs = '\n\n{"jsonrpc": "2.0", "method": "close", "id": 1}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))

    run_mcp_server()
    out = capsys.readouterr().out
    assert '"id": 1' in out
    assert '"result": {}' in out


def test_apply_env_vars_store_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test apply_env_vars_to_parser with store_true and store_false actions.

    Args:
        monkeypatch: Parameter .
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-true", action="store_true")
    parser.add_argument("--test-false", action="store_false")
    monkeypatch.setenv("CDD_TEST_TRUE", "yes")
    monkeypatch.setenv("CDD_TEST_FALSE", "no")

    apply_env_vars_to_parser(parser)
    assert parser._actions[1].default is True
    assert parser._actions[2].default is True

    monkeypatch.setenv("CDD_TEST_TRUE", "no")
    monkeypatch.setenv("CDD_TEST_FALSE", "yes")
    apply_env_vars_to_parser(parser)
    assert parser._actions[1].default is False
    assert parser._actions[2].default is False


def test_run_mcp_server_close(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_mcp_server responds to close and exits cleanly.

    Args:
        monkeypatch: Parameter .
    """
    inputs = '{"jsonrpc": "2.0", "method": "close", "id": 1}\n'
    out = StringIO()
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", out)

    run_mcp_server()
    resp = json.loads(out.getvalue().strip())
    assert resp["id"] == 1
    assert resp["result"] == {}


def test_run_mcp_server_empty_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_mcp_server ignores empty lines.

    Args:
        monkeypatch: Parameter .
    """
    inputs = "\n\n"
    out = StringIO()
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", out)

    run_mcp_server()
    assert out.getvalue() == ""


def test_run_mcp_server_exception_req_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_mcp_server returns -32603 error when an exception occurs with req_id.

    Args:
        monkeypatch: Parameter .
    """
    inputs = '[{"id": 1}]\n{"jsonrpc": "2.0", "method": "close", "id": 2}\n'
    out = StringIO()
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", out)

    run_mcp_server()
    lines = [json.loads(line) for line in out.getvalue().strip().splitlines()]
    assert lines[-1]["id"] == 2

    # Also test when req_id is set before an unexpected exception in method handling
    inputs2 = '{"jsonrpc": "2.0", "method": "tools/call", "id": 9, "params": null}\n'
    out2 = StringIO()
    monkeypatch.setattr(sys, "stdin", StringIO(inputs2))
    monkeypatch.setattr(sys, "stdout", out2)
    run_mcp_server()
    resp = json.loads(out2.getvalue().strip())
    assert resp["id"] == 9
    assert resp["error"]["code"] == -32603


def test_run_mcp_server_exception_no_req_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_mcp_server suppresses response when exception occurs without req_id.

    Args:
        monkeypatch: Parameter .
    """
    inputs = '{"jsonrpc": "2.0", "method": "tools/call", "params": null}\n{"jsonrpc": "2.0", "method": "close", "id": 2}\n'
    out = StringIO()
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", out)

    monkeypatch.setattr(
        cli,
        "generate_to_openapi",
        lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Mock error")),
    )

    run_mcp_server()
    lines = [json.loads(line) for line in out.getvalue().strip().splitlines()]
    assert len(lines) == 1
    assert lines[0]["id"] == 2


def test_run_mcp_server_exception_early(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test run_mcp_server handles malformed JSON before req_id is assigned.

    Args:
        monkeypatch: Parameter .
    """
    inputs = '{\n{"jsonrpc": "2.0", "method": "close", "id": 2}\n'
    out = StringIO()
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", out)

    run_mcp_server()
    lines = [json.loads(line) for line in out.getvalue().strip().splitlines()]
    assert len(lines) == 1
    assert lines[0]["id"] == 2


def test_cli_docs_json_missing_branches(tmp_path: Path) -> None:
    """Test generate_docs_json with Reference parameters and empty path items.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {
            "/test": {
                "get": {
                    "operationId": "get_test",
                    "parameters": [{"$ref": "#/components/parameters/RefParam"}],
                }
            },
            "/empty_path": {"summary": "This path has no HTTP methods"},
        },
    }
    input_file = tmp_path / "openapi.json"
    input_file.write_text(json.dumps(spec), encoding="utf-8")
    output_file = tmp_path / "docs.json"
    generate_docs_json(str(input_file), False, False, str(output_file))
    docs = json.loads(output_file.read_text(encoding="utf-8"))
    assert "/test" in docs["endpoints"]
    assert "/empty_path" not in docs["endpoints"]


def test_openapi_to_cdd_project_invalid_subcommand(tmp_path: Path) -> None:
    """Test main CLI exits on unknown from_openapi subcommand.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {},
    }
    input_file = tmp_path / "openapi.json"
    input_file.write_text(json.dumps(spec), encoding="utf-8")
    with (
        patch(
            "sys.argv",
            ["cli.py", "from_openapi", "to_unknown", "--input", str(input_file)],
        ),
        pytest.raises(SystemExit),
    ):
        main()


def test_generate_to_openapi_snapshot_exists(tmp_path: Path) -> None:
    """Test generate_to_openapi loads from openapi.snapshot.json when present.

    Args:
        tmp_path: Parameter .
    """
    snapshot = tmp_path / "openapi.snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Snapshot API", "version": "1.0"},
                "paths": {},
            }
        ),
        encoding="utf-8",
    )
    out_file = tmp_path / "out.json"
    generate_to_openapi(str(tmp_path), str(out_file))
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert parsed["info"]["title"] == "Snapshot API"


def test_generate_to_openapi_no_client_py_but_models_py(tmp_path: Path) -> None:
    """Test generate_to_openapi extracts models.py when client.py is absent.

    Args:
        tmp_path: Parameter .
    """
    models_py = tmp_path / "models.py"
    models_py.write_text("class MyModel:\n    id: int = 1\n", encoding="utf-8")
    out_file = tmp_path / "out.json"
    generate_to_openapi(str(tmp_path), str(out_file))
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert "MyModel" in parsed["components"]["schemas"]


def test_sync_project_src_exists_cli_missing(tmp_path: Path) -> None:
    """Test sync_dir when src/ directory exists without cli_main.py.

    Args:
        tmp_path: Parameter .
    """
    (tmp_path / "src").mkdir()
    openapi_json = tmp_path / "openapi.json"
    openapi_json.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Test", "version": "1.0"},
                "paths": {},
            }
        ),
        encoding="utf-8",
    )
    sync_dir(str(tmp_path))
    assert (tmp_path / "client.py").exists()


def test_cli_main_invalid_command() -> None:
    """Test main CLI when parse_args returns an unrecognized command."""
    with patch("argparse.ArgumentParser.parse_args") as mock_parse:
        mock_args = MagicMock()
        mock_args.command = "some_unknown_command"
        mock_parse.return_value = mock_args
        main()
        mock_parse.assert_called_once()


def test_functions_emit_missing_branches() -> None:
    """Test emit_functions when parameter mocks do not have a `name` attribute."""
    m1 = Mock()
    m1.in_ = "body"
    del m1.name

    m2 = Mock()
    m2.in_ = "query"
    del m2.name

    spec = OpenAPI(
        openapi="3.0",
        info=Info(title="test", version="1"),
        paths={"/test": PathItem(get=Operation(operationId="get_test"))},
    )
    spec.paths["/test"].get.parameters = [m1, m2]

    funcs = emit_functions(spec)
    assert len(funcs) == 2


def test_functions_parse_missing_branches() -> None:
    """Test FunctionExtractor on edge-case decorators and method signatures."""
    spec = OpenAPI(
        openapi="3.0", info=Info(title="test", version="1"), paths={"/test": PathItem()}
    )
    extractor = FunctionExtractor(spec)

    code = """
class MyClient:
    @obj.attr
    @tags()
    @tags([])
    def get_pets(self, param1, body: dict, data: dict, a: list[1:2]):
        pass

    def getpets(self):
        pass

    def func_pets(self):
        pass
"""
    mod = cst.parse_module(code)
    mod.visit(extractor)
    assert "/pets" in (extractor.spec.paths or {})

    func_node = mod.body[0].body.body[0]
    extractor.spec.paths = None
    extractor.visit_FunctionDef(func_node)
    assert extractor.spec.paths is None


def test_mocks_emit_missing_branches() -> None:
    """Test emit_mock_server skips path keys that do not start with a slash."""
    spec = OpenAPI(
        openapi="3.0",
        info=Info(title="test", version="1"),
        paths={"not_slash": PathItem(get=Operation(operationId="test"))},
    )
    mod = emit_mock_server(spec)
    assert "def test" not in mod.code


def test_mocks_parse_missing_branches() -> None:
    """Test MockServerExtractor on routes with non-EventSourceResponse returns."""
    spec = OpenAPI(openapi="3.0", info=Info(title="t", version="1"))
    extractor = MockServerExtractor(spec)

    code = """
@app.get("/test")
def route():
    return None

@app.get("/test2")
def route2():
    return obj.method()

@app.get("/test3")
def route3():
    return Response()
"""
    mod = cst.parse_module(code)
    mod.visit(extractor)
    assert "/test" in (extractor.spec.paths or {})
    assert "/test2" in (extractor.spec.paths or {})
    assert "/test3" in (extractor.spec.paths or {})

    extractor.spec.paths = None
    func_node = mod.body[0]
    extractor.visit_FunctionDef(func_node)
    assert extractor.spec.paths is None


def test_openapi_parse_missing_branches(tmp_path: Path) -> None:
    """Test parse_openapi_dict with internal and external JSON pointer refs.

    Args:
        tmp_path: Parameter .
    """
    external_file = tmp_path / "ext.json"
    external_file.write_text(
        json.dumps({"components": {"schemas": {"A": {"type": "string"}}}}),
        encoding="utf-8",
    )

    spec = {
        "openapi": "3.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "components": {
            "schemas": {
                "InternalRef": {"$ref": "#/components/schemas/A"},
                "ExternalRef": {"$ref": "ext.json#//components/schemas/A"},
            }
        },
    }
    parsed = parse_openapi_dict(spec, base_path=tmp_path)
    assert parsed.components is not None
    assert parsed.components.schemas["ExternalRef"].type == "string"


def test_sqlalchemy_cdd_emit_missing_branches() -> None:
    """Test emit_sqlalchemy skips schemas without properties."""
    spec = OpenAPI(
        openapi="3.0",
        info=Info(title="t", version="1"),
        components=Components(schemas={"NoProps": Schema(type="string")}),
    )
    files = emit_sqlalchemy(spec)
    assert "models/__init__.py" in files
    assert "models/no_props.py" not in files


def test_cli_loop_skip(tmp_path: Path) -> None:
    """Test generate_from_openapi with an unrecognized subcommand still scaffolds.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0"},
        "paths": {},
    }
    input_file = tmp_path / "openapi.json"
    input_file.write_text(json.dumps(spec), encoding="utf-8")
    generate_from_openapi(
        "to_unknown_subcommand",
        str(input_file),
        None,
        str(tmp_path),
        False,
        False,
        False,
    )
    assert (tmp_path / "pyproject.toml").exists()


def test_openapi_parse_empty_part(tmp_path: Path) -> None:
    """Test parse_openapi_dict with empty pointer segments and empty $ref.

    Args:
        tmp_path: Parameter .
    """
    external_file = tmp_path / "ext.json"
    external_file.write_text(
        json.dumps({"components": {"schemas": {"A": {"type": "string"}}}}),
        encoding="utf-8",
    )

    spec = {
        "openapi": "3.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "components": {
            "schemas": {
                "EmptyPart": {"$ref": "ext.json#//components//schemas/A"},
                "EmptyRef": {"$ref": ""},
            }
        },
    }
    parsed = parse_openapi_dict(spec, base_path=tmp_path)
    assert parsed.components is not None
    assert parsed.components.schemas["EmptyPart"].type == "string"


def test_openapi_parse_parameters_list(tmp_path: Path) -> None:
    """Test parse_openapi_dict when top-level parameters is a list instead of dict.

    Args:
        tmp_path: Parameter .
    """
    spec = {
        "openapi": "3.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
        "parameters": [{"name": "test", "in": "query", "schema": {"type": "string"}}],
    }
    with pytest.raises(ValidationError):
        parse_openapi_dict(spec, base_path=tmp_path)


def test_write_generated_local_str(tmp_path) -> None:
    """Test sync_dir where emit_seeder returns a string.

    Args:
        tmp_path: Parameter .
    """
    with (
        unittest.mock.patch(
            "openapi_client.cli.emit_seeder", return_value="string_code", create=True
        ),
        unittest.mock.patch(
            "openapi_client.seeder.emit.emit_seeder", return_value="string_code"
        ),
    ):
        sync_dir(str(tmp_path))

    assert (tmp_path / "seeder.py").read_text() == "string_code"
