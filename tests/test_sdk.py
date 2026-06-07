"""Tests for test_sdk.py."""

from openapi_client import sdk
from unittest.mock import patch


def test_generate_from_openapi():
    """Test test_generate_from_openapi."""
    with patch("openapi_client.sdk.cli_generate_from_openapi") as mock:
        sdk.generate_from_openapi("input.json", "out_dir")
        mock.assert_called_once()


def test_generate_to_openapi():
    """Test test_generate_to_openapi."""
    with patch("openapi_client.sdk.cli_generate_to_openapi") as mock:
        sdk.generate_to_openapi("input_dir")
        mock.assert_called_once()


def test_generate_docs_json():
    """Test test_generate_docs_json."""
    with patch("openapi_client.sdk.cli_generate_docs_json") as mock:
        sdk.generate_docs_json("input.json")
        mock.assert_called_once()


def test_serve_json_rpc():
    """Test test_serve_json_rpc."""
    with patch("openapi_client.sdk.cli_serve_json_rpc") as mock:
        sdk.serve_json_rpc()
        mock.assert_called_once()
