import os
import json
import pytest
from pathlib import Path
from openapi_client.cli import main, sync_to_python, sync_to_openapi


def test_cli_sync_to_python(tmp_path):
    spec = {
        "openapi": "3.2.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {},
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec))

    out_dir = tmp_path / "out"
    sync_to_python(str(spec_path), str(out_dir))

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


def test_cli_main_python(tmp_path, monkeypatch):
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
        ["cdd", "sync", "--from-openapi", str(spec_path), "--to-python", str(out_dir)],
    )
    main()
    assert (out_dir / "client.py").exists()


def test_cli_main_openapi(tmp_path, monkeypatch):
    py_code = "class Client:\n    pass\n"
    py_path = tmp_path / "client.py"
    py_path.write_text(py_code)
    out_spec = tmp_path / "openapi.json"

    monkeypatch.setattr(
        "sys.argv",
        ["cdd", "sync", "--from-python", str(py_path), "--to-openapi", str(out_spec)],
    )
    main()
    assert out_spec.exists()


def test_cli_main_invalid(monkeypatch):
    monkeypatch.setattr("sys.argv", ["cdd", "sync"])
    with pytest.raises(SystemExit):
        main()


from openapi_client.cli import sync_dir


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

    # run sync_dir
    import json

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


def test_cli_main_sync_dir(tmp_path, monkeypatch):
    from openapi_client.cli import main

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    client_py = project_dir / "client.py"
    client_py.write_text("class Client:\n    pass\n")

    import sys

    monkeypatch.setattr("sys.argv", ["cdd", "sync", "--dir", str(project_dir)])
    main()
    assert (project_dir / "openapi.json").exists()
