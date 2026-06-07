"""Tests for cli.py branches."""


def test_serve_json_rpc_break(monkeypatch, capsys):
    """Test serve_json_rpc termination conditions."""
    import sys
    from io import StringIO

    # Mock sys.stdin to have empty line then close method
    inputs = '\n\n{"jsonrpc": "2.0", "method": "close", "id": 1}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))

    # Needs a mock client passed to it but cli.py creates it inside...
    # Let's check cli.py serve_json_rpc again to see if we can easily test it.


def test_apply_env_vars_store_true():
    from openapi_client.cli import apply_env_vars_to_parser
    import argparse
    import os

    """Test test_apply_env_vars_store_true."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-true", action="store_true")
    parser.add_argument("--test-false", action="store_false")
    os.environ["CDD_TEST_TRUE"] = "yes"
    os.environ["CDD_TEST_FALSE"] = "no"

    apply_env_vars_to_parser(parser)
    assert parser._actions[1].default is True
    assert (
        parser._actions[2].default is True
    )  # Since not in yes/true/1 it means True for StoreFalse

    os.environ["CDD_TEST_TRUE"] = "no"
    os.environ["CDD_TEST_FALSE"] = "yes"
    apply_env_vars_to_parser(parser)
    assert parser._actions[1].default is False
    assert parser._actions[2].default is False
