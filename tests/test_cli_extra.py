import os
import sys
import json
import pytest
from pathlib import Path
from http.server import HTTPServer

import openapi_client.cli
from openapi_client.cli import main, apply_env_vars_to_parser, run_json_rpc_server


def test_apply_env_vars_to_parser(monkeypatch, tmp_path):
    # Setup files
    input_file = tmp_path / "dummy.json"
    spec = {"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}
    input_file.write_text(json.dumps(spec))

    monkeypatch.setenv("CDD_PYTHON_INPUT", str(input_file))
    monkeypatch.setenv("CDD_PYTHON_OUTPUT", str(tmp_path))
    monkeypatch.setenv("CDD_PYTHON_NO_GITHUB_ACTIONS", "true")

    monkeypatch.setattr("sys.argv", ["cdd-python", "from_openapi", "to_sdk"])
    main()
    assert (tmp_path / "client.py").exists()
    assert not (tmp_path / ".github" / "workflows" / "ci.yml").exists()


def test_scaffold_package(monkeypatch, tmp_path):
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
    class MockHTTPServer:
        def __init__(self, addr, handler_class):
            self.addr = addr
            self.handler_class = handler_class
            self.handled = []

        def serve_forever(self):
            # We trigger one fake request manually
            from io import BytesIO

            class MockRequest:
                def makefile(self, mode, *args, **kwargs):
                    if "b" in mode:
                        return BytesIO(b"{}")
                    return BytesIO()

                def sendall(self, data):
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

            # mock sync_to_openapi
            def mock_sync_to_openapi(p, o):
                print("MOCK SYNC")

            monkeypatch.setattr(
                openapi_client.cli, "sync_to_openapi", mock_sync_to_openapi
            )
            handler.do_POST()

            # test another
            handler.rfile = BytesIO(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "from_openapi",
                        "params": {
                            "subcommand": "to_sdk",
                            "output": "mock",
                            "no_github_actions": True,
                        },
                    }
                ).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}

            def mock_process_from_openapi(*args, **kwargs):
                print("MOCK PROCESS")

            monkeypatch.setattr(
                openapi_client.cli, "process_from_openapi", mock_process_from_openapi
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
                raise ValueError("ERROR")

            monkeypatch.setattr(openapi_client.cli, "sync_dir", raise_exc)
            handler.do_POST()

    import http.server

    monkeypatch.setattr(http.server, "HTTPServer", MockHTTPServer)

    monkeypatch.setattr("sys.argv", ["cdd-python", "server_json_rpc", "--port", "1234"])
    main()

    # Check outputs
    out = capsys.readouterr().out
    assert "MOCK SYNC" in out
    assert "MOCK PROCESS" in out
    assert "MOCK DOCS" in out
    assert "MOCK SYNC DIR" in out


def test_to_docs_json_output_file(tmp_path, monkeypatch):
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
    import json
    import openapi_client.cli

    # store false via apply_env_vars
    parser = openapi_client.cli.argparse.ArgumentParser()
    parser.add_argument("--test-flag", action="store_false", dest="test_flag")
    monkeypatch.setenv("CDD_PYTHON_TEST_FLAG", "false")
    openapi_client.cli.apply_env_vars_to_parser(parser)

    # process_from_openapi output_dir="." fallback
    def mock_mkdir(*args, **kwargs):
        pass

    spec = {"openapi": "3.2.0", "info": {"title": "T", "version": "1"}, "paths": {}}
    input_file = tmp_path / "dummy.json"
    input_file.write_text(json.dumps(spec))
    openapi_client.cli.process_from_openapi(
        "to_sdk", str(input_file), None, None, True, True
    )

    # sync_to_openapi output_path="openapi.json" fallback
    py_code = "class Client:\n    pass\n"
    py_file = tmp_path / "client.py"
    py_file.write_text(py_code)
    openapi_client.cli.sync_to_openapi(str(py_file), None)


def test_jsonrpc_invalid_rpc(monkeypatch, capsys):
    import json
    from io import BytesIO
    import openapi_client.cli
    import http.server

    class MockHTTPServer:
        def __init__(self, addr, handler_class):
            self.addr = addr
            self.handler_class = handler_class

        def serve_forever(self):
            class MockRequest:
                def makefile(self, mode, *args, **kwargs):
                    if "b" in mode:
                        return BytesIO(b"{}")
                    return BytesIO()

                def sendall(self, data):
                    pass

            handler = self.handler_class(MockRequest(), self.addr, self)
            handler.rfile = BytesIO(
                json.dumps({"jsonrpc": "1.0", "method": "test"}).encode()
            )
            handler.headers = {"Content-Length": str(len(handler.rfile.getvalue()))}
            handler.do_POST()

    monkeypatch.setattr(http.server, "HTTPServer", MockHTTPServer)
    monkeypatch.setattr("sys.argv", ["cdd-python", "server_json_rpc"])
    openapi_client.cli.main()
