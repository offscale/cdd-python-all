"""Test cli exit"""

from openapi_client.cli import run_mcp_server


def test_run_mcp_server_close(monkeypatch):
    """Test test_run_mcp_server_close."""
    import sys
    from io import StringIO

    inputs = '{"jsonrpc": "2.0", "method": "close", "id": 1}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", StringIO())

    run_mcp_server()


def test_run_mcp_server_empty_line(monkeypatch):
    """Test test_run_mcp_server_empty_line."""
    import sys
    from io import StringIO

    inputs = "\n\n"
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", StringIO())

    run_mcp_server()


def test_run_mcp_server_exception_req_id(monkeypatch):
    """Test exception with req_id."""
    import sys
    from io import StringIO

    inputs = '{"jsonrpc": "2.0", "method": "to_openapi", "id": 1, "params": {}}\n{"jsonrpc": "2.0", "method": "close", "id": 2}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", StringIO())

    import openapi_client.cli as cli

    # Directly use a lambda to avoid missing def coverage lines
    monkeypatch.setattr(
        cli,
        "generate_to_openapi",
        lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Mock error")),
    )

    run_mcp_server()


def test_run_mcp_server_exception_no_req_id(monkeypatch):
    """Test exception without req_id."""
    import sys
    from io import StringIO

    inputs = '{"jsonrpc": "2.0", "method": "to_openapi", "params": {}}\n{"jsonrpc": "2.0", "method": "close", "id": 2}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", StringIO())

    import openapi_client.cli as cli

    monkeypatch.setattr(
        cli,
        "generate_to_openapi",
        lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Mock error")),
    )

    run_mcp_server()


def test_run_mcp_server_exception_early(monkeypatch):
    """Test exception early in loop without req_id."""
    import sys
    from io import StringIO

    inputs = '{\n{"jsonrpc": "2.0", "method": "close", "id": 2}\n'
    monkeypatch.setattr(sys, "stdin", StringIO(inputs))
    monkeypatch.setattr(sys, "stdout", StringIO())

    run_mcp_server()
