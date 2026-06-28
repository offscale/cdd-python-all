"""Tests for test_cli_extra.py."""

import json

import openapi_client.cli
from openapi_client.cli import main


def test_apply_env_vars_to_parser(monkeypatch, tmp_path):
    # Setup files
    """Test test_apply_env_vars_to_parser."""
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


def test_scaffold_package(monkeypatch, tmp_path):
    """Test test_scaffold_package."""
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


def test_json_rpc_handler_direct(monkeypatch, capsys):
    # Mock HTTPServer
    """Test test_json_rpc_handler_direct."""

    class MockHTTPServer:
        """Test MockHTTPServer."""

        def __init__(self, addr, handler_class):
            """Test __init__."""
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
                    """Test makefile."""
                    if "b" in mode:
                        return BytesIO(b"{}")  # pragma: no cover
                    return BytesIO()

                def sendall(self, data):
                    """Test sendall."""
                    pass

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
                """Test mock_generate_to_openapi."""
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
                """Test mock_generate_from_openapi."""
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
                """Test mock_generate_docs_json."""
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
                """Test mock_sync_dir."""
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
                """Test raise_exc."""
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


def test_to_docs_json_output_file(tmp_path, monkeypatch):
    """Test test_to_docs_json_output_file."""
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


def test_cli_missing_coverage(monkeypatch, tmp_path):
    """Test test_cli_missing_coverage."""
    import json
    import openapi_client.cli

    # store false via apply_env_vars
    parser = openapi_client.cli.argparse.ArgumentParser()
    parser.add_argument("--test-flag", action="store_false", dest="test_flag")
    monkeypatch.setenv("CDD_TEST_FLAG", "false")
    openapi_client.cli.apply_env_vars_to_parser(parser)

    # generate_from_openapi output_dir="." fallback
    def mock_mkdir(*args, **kwargs):  # pragma: no cover
        """Test mock_mkdir."""
        pass

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


def test_jsonrpc_invalid_rpc(monkeypatch, capsys):
    """Test test_jsonrpc_invalid_rpc."""
    import json
    from io import BytesIO
    import openapi_client.cli
    import http.server

    class MockHTTPServer:
        """Test MockHTTPServer."""

        def __init__(self, addr, handler_class):
            """Test __init__."""
            self.addr = addr
            self.handler_class = handler_class

        def serve_forever(self):
            """Test serve_forever."""

            class MockRequest:  # pragma: no cover
                """Test MockRequest."""

                def makefile(self, mode, *args, **kwargs):
                    """Test makefile."""
                    if "b" in mode:
                        return BytesIO(b"{}")  # pragma: no cover
                    return BytesIO()

                def sendall(self, data):
                    """Test sendall."""
                    pass

            handler = self.handler_class(MockRequest(), self.addr, self)
            handler.rfile = BytesIO(
                json.dumps({"jsonrpc": "1.0", "method": "test"}).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}
            handler.do_POST()

    monkeypatch.setattr(http.server, "HTTPServer", MockHTTPServer)
    monkeypatch.setattr("sys.argv", ["cdd-python", "serve_json_rpc"])
    openapi_client.cli.main()


def test_openapi_client_mcp(monkeypatch):
    """Test test_openapi_client_mcp."""
    from openapi_client import mcp
    import openapi_client.sdk as sdk

    tools = mcp.get_tools()
    assert len(tools) == 3

    def mock_generate_to_openapi(*args, **kwargs):
        """Test mock_generate_to_openapi."""
        return "to_openapi"

    def mock_generate_from_openapi(*args, **kwargs):
        """Test mock_generate_from_openapi."""
        return "from_openapi"

    def mock_generate_docs_json(*args, **kwargs):
        """Test mock_generate_docs_json."""
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


def test_cli_mcp_server(monkeypatch, capsys):
    """Test test_cli_mcp_server."""
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
        json.dumps({"jsonrpc": "2.0", "method": "close", "id": 14}),
        "",
    ]

    mock_stdin = StringIO("\n".join(test_inputs) + "\n")
    monkeypatch.setattr(sys, "stdin", mock_stdin)

    def mock_generate_to_openapi(input_path, output_path):
        """Test mock_generate_to_openapi."""
        if hasattr(mock_generate_to_openapi, "called"):
            raise Exception("Mock generic error")
        mock_generate_to_openapi.called = True
        print("MOCK GENERATE TO OPENAPI")
        raise ValueError("Mock error")

    def mock_generate_from_openapi(*args, **kwargs):
        """Test mock_generate_from_openapi."""
        print("MOCK GENERATE FROM OPENAPI")

    def mock_sync_dir(project_dir):
        """Test mock_sync_dir."""
        print("MOCK SYNC DIR")

    def mock_generate_docs_json(*args, **kwargs):
        """Test mock_generate_docs_json."""
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
