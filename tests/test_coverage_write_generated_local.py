"""Tests for test_coverage_write_generated_local.py."""

import unittest.mock
from openapi_client.cli import sync_dir


def test_write_generated_local_str(tmp_path):
    """Test sync_dir where emit_seeder returns a string."""
    with unittest.mock.patch(
        "openapi_client.cli.emit_seeder", return_value="string_code", create=True
    ):
        with unittest.mock.patch(
            "openapi_client.seeder.emit.emit_seeder", return_value="string_code"
        ):
            sync_dir(str(tmp_path))

    assert (tmp_path / "seeder.py").read_text() == "string_code"
