"""Tests for test_sdk.py."""

from openapi_client import sdk
from unittest.mock import patch


def test_from_openapi():
    """Test test_from_openapi."""
    with patch("openapi_client.sdk.cli_generate_from_openapi") as mock:
        sdk.generate_from_openapi("input.json", "out_dir")
        mock.assert_called_once()


def test_to_openapi():
    """Test test_to_openapi."""
    with patch("openapi_client.sdk.cli_generate_to_openapi") as mock:
        sdk.generate_to_openapi("input_dir")
        mock.assert_called_once()


def test_to_docs_json():
    """Test test_to_docs_json."""
    with patch("openapi_client.sdk.cli_generate_docs_json") as mock:
        sdk.generate_docs_json("input.json")
        mock.assert_called_once()


def test_serve_json_rpc():
    """Test test_serve_json_rpc."""
    with patch("openapi_client.sdk.cli_serve_json_rpc") as mock:
        sdk.serve_json_rpc()
        mock.assert_called_once()


def test_sync():
    """Test test_sync."""
    with patch("openapi_client.sdk.cli_sync_dir") as mock:
        sdk.run_sync("input_dir")
        mock.assert_called_once()


def test_mcp():
    """Test test_mcp."""
    with patch("openapi_client.sdk.cli_run_mcp_server") as mock:
        sdk.mcp()
        mock.assert_called_once()
