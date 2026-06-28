from openapi_client.cli import sync_dir


def test_sync_dir_output_flag(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    openapi_json = project_dir / "openapi.json"
    openapi_json.write_text(
        '{"openapi": "3.2.0", "info": {"title": "Test", "version": "1"}, "paths": {}, "components": {"schemas": {}}}'
    )

    out_dir = tmp_path / "out"

    sync_dir(str(project_dir), output_dir=str(out_dir))

    assert (out_dir / "openapi.json").exists()
    assert (out_dir / "client.py").exists()


def test_cli_main_sync_output(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    openapi_json = project_dir / "openapi.json"
    openapi_json.write_text(
        '{"openapi": "3.2.0", "info": {"title": "Test", "version": "1"}, "paths": {}, "components": {"schemas": {}}}'
    )

    out_dir = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv", ["cdd-python", "sync", "-i", str(project_dir), "-o", str(out_dir)]
    )

    from openapi_client.cli import main

    main()

    assert (out_dir / "openapi.json").exists()
    assert (out_dir / "client.py").exists()
