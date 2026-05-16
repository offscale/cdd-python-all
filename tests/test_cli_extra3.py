import json
from openapi_client.cli import process_from_openapi, sync_to_openapi


def test_snapshot_roundtrip(tmp_path):
    """Test that a snapshot is created during to_sdk and correctly parsed during from_sdk."""
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
    process_from_openapi("to_sdk", str(in_file), None, str(out_sdk_dir))

    assert (out_sdk_dir / "src" / "openapi.snapshot.json").exists()

    # Run sync_to_openapi (to_openapi)
    out_spec = tmp_path / "out.json"
    sync_to_openapi(out_sdk_dir, out_spec)

    out_spec_parsed = json.loads(out_spec.read_text())
    assert "webhooks" in out_spec_parsed
    assert "myWebhook" in out_spec_parsed["webhooks"]
