import os
import json
import pytest
from pathlib import Path
from openapi_client.cli import main, process_from_openapi, sync_to_openapi, sync_dir


def test_cli_sync_from_openapi(tmp_path):
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out"
    process_from_openapi("to_sdk", str(spec_path), None, str(out_dir))
    process_from_openapi("to_server", str(spec_path), None, str(out_dir))

    assert (out_dir / "client.py").exists()
    assert (out_dir / "test_client.py").exists()
    assert (out_dir / "main.py").exists()


def test_cli_sync_to_openapi(tmp_path):
    py_code = "class Client:\n    pass\n"
    py_path = tmp_path / "client.py"
    py_path.write_text(py_code)

    out_spec = tmp_path / "openapi.json"
    sync_to_openapi(str(py_path), str(out_spec))

    assert out_spec.exists()
    data = json.loads(out_spec.read_text())
    assert data["openapi"] == "3.2.0"


def test_cli_main_from_openapi(tmp_path, monkeypatch):
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
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
    assert (out_dir / "client.py").exists()


def test_cli_main_to_openapi(tmp_path, monkeypatch):
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


def test_cli_sync_dir(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # client.py
    client_py = project_dir / "client.py"
    client_py.write_text("""
from pydantic import BaseModel
class Pet(BaseModel):
    name: str

class Client:
    def get_pets(self):
        pass
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
def test_get_pets():
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


def test_cli_main_sync(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    client_py = project_dir / "client.py"
    client_py.write_text("class Client:\n    pass\n")

    monkeypatch.setattr("sys.argv", ["cdd-python", "sync", "--dir", str(project_dir)])
    main()
    assert (project_dir / "openapi.json").exists()


def test_cli_main_invalid(monkeypatch):
    monkeypatch.setattr("sys.argv", ["cdd-python"])
    with pytest.raises(SystemExit):
        main()


def test_cli_to_docs_json(tmp_path, monkeypatch, capsys):
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
    assert "response = client.getPets(limit=limit)" in code
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
    assert "response = client.getPets(limit=limit)" in code

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
    assert "response = client.getPets(limit=limit)" in code


def test_cli_to_docs_json_no_operation_id(tmp_path, monkeypatch, capsys):
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


def test_process_from_openapi_input_dir(tmp_path):
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
    process_from_openapi("to_sdk_cli", None, str(d), str(out_dir))
    assert (out_dir / "client.py").exists()
    assert (out_dir / "cli_main.py").exists()


def test_process_from_openapi_no_input(capsys):
    import pytest

    with pytest.raises(SystemExit):
        process_from_openapi("to_sdk", None, None, "out")


def test_sync_to_openapi_cli(tmp_path):
    py_code = 'import argparse\nparser = argparse.ArgumentParser()\nsubparsers = parser.add_subparsers()\nsubparsers.add_parser("test")'
    py_path = tmp_path / "cli_main.py"
    py_path.write_text(py_code)

    out_spec = tmp_path / "openapi.json"
    sync_to_openapi(str(py_path), str(out_spec))

    assert out_spec.exists()
    import json

    data = json.loads(out_spec.read_text())
    assert data["info"]["title"] == "Extracted API"


def test_sync_dir_with_cli(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "cli_main.py").write_text(
        'import argparse\nparser = argparse.ArgumentParser()\nsubparsers = parser.add_subparsers()\nsubparsers.add_parser("test")'
    )
    sync_dir(str(project_dir))
    assert (project_dir / "cli_main.py").exists()
    assert (project_dir / "openapi.json").exists()


def test_cli_main_from_openapi_missing_subcmd(monkeypatch, capsys):
    import pytest

    monkeypatch.setattr("sys.argv", ["cdd-python", "from_openapi"])
    with pytest.raises(SystemExit):
        main()


def test_cli_to_docs_json_url(monkeypatch, capsys):
    import json
    import io
    from urllib.request import Request

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
        def read(self):
            return json.dumps(spec).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(req):
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
