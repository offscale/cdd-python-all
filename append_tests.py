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
