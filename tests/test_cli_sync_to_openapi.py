import json
from pathlib import Path
from openapi_client.cli import sync_to_openapi

def test_sync_to_openapi_dir(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    client_py = project_dir / "client.py"
    client_py.write_text("class Client:\n    pass\n")

    mock_py = project_dir / "mock_server.py"
    mock_py.write_text("def test_mock():\n    pass\n")

    test_py = project_dir / "test_client.py"
    test_py.write_text("def test_client():\n    pass\n")

    cli_py = project_dir / "cli_main.py"
    cli_py.write_text("import argparse\n")

    out_file = tmp_path / "openapi.json"
    sync_to_openapi(str(project_dir), str(out_file))

    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert "openapi" in data

def test_sync_to_openapi_empty_output(tmp_path: Path) -> None:
    # Test when output_path is not given (it defaults to "openapi.json")
    import os
    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        project_dir = tmp_path / "project2"
        project_dir.mkdir()
        client_py = project_dir / "client.py"
        client_py.write_text("class Client:\n    pass\n")
        sync_to_openapi(str(project_dir), "")
        assert (tmp_path / "openapi.json").exists()
    finally:
        os.chdir(old_cwd)
