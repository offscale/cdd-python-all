import os
import json
import pytest
from pathlib import Path
from openapi_client.cli import main, sync_from_openapi, sync_to_openapi, sync_dir


def test_cli_sync_from_openapi(tmp_path):
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out"
    sync_from_openapi(str(spec_path), str(out_dir))

    assert (out_dir / "client.py").exists()
    assert (out_dir / "test_client.py").exists()
    assert (out_dir / "mock_server.py").exists()


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
        ["cdd-python", "from_openapi", "-i", str(spec_path), "-o", str(out_dir)],
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
        ["cdd-python", "to_openapi", "-f", str(py_path), "-o", str(out_spec)],
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
    assert len(output) == 1
    assert output[0]["language"] == "python"

    ops = output[0]["operations"]
    assert len(ops) == 1
    op = ops[0]
    assert op["method"] == "GET"
    assert op["path"] == "/pets"
    assert op["operationId"] == "getPets"

    code = op["code"]
    assert "imports" in code
    assert "wrapper_start" in code
    assert "wrapper_end" in code
    assert "snippet" in code
    assert "limit=limit" in code["snippet"]
    assert code["snippet"].startswith("    response =")

    # Test --no-imports
    monkeypatch.setattr(
        "sys.argv", ["cdd-python", "to_docs_json", "-i", str(spec_path), "--no-imports"]
    )
    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    code = output[0]["operations"][0]["code"]
    assert "imports" not in code
    assert "wrapper_start" in code

    # Test --no-wrapping
    monkeypatch.setattr(
        "sys.argv",
        ["cdd-python", "to_docs_json", "-i", str(spec_path), "--no-wrapping"],
    )
    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    code = output[0]["operations"][0]["code"]
    assert "imports" in code
    assert "wrapper_start" not in code
    assert "wrapper_end" not in code
    assert not code["snippet"].startswith("    response =")
    assert code["snippet"].startswith("response =")

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
    code = output[0]["operations"][0]["code"]
    assert "imports" not in code
    assert "wrapper_start" not in code
    assert "wrapper_end" not in code
    assert "snippet" in code


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
    assert len(output) == 1

    ops = output[0]["operations"]
    assert len(ops) == 1
    op = ops[0]
    assert op["method"] == "POST"
    assert "operationId" not in op  # Only included if present
    assert "post_dogs" in op["code"]["snippet"]
