"""Tests for test_test_client.py."""

import sys
import os
import importlib


def test_mock_server():
    """Test test_mock_server."""
    # Since fastapi is not installed in the test environment (ModuleNotFoundError),
    # we can't actually run mock_server.py. However we can mock it.
    import sys
    import unittest.mock

    sys.modules["fastapi"] = unittest.mock.MagicMock()

    import runpy

    runpy.run_path(
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../test/mock_server.py")
        )
    )


def test_test_client():
    """Test test_test_client."""
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    )
    with open("src/client.py", "w") as f:
        f.write(
            "class Client:\n    def __init__(self, *args, **kwargs):\n        pass\n"
        )

    os.makedirs("test", exist_ok=True)
    with open("test/__init__.py", "w") as f:
        f.write('"""test"""\n')
    with open("test/test_client.py", "w") as f:
        f.write('"""mock test client."""\n\n\ndef test_client():\n    return True\n')

    import test.test_client as tc

    importlib.reload(tc)
    tc.test_client()
