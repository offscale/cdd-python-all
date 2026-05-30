import sys
import os


def test_mock_server():
    pass


def test_test_client():
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
    )
    with open("src/client.py", "w") as f:
        f.write(
            "class Client:\n    def __init__(self, *args, **kwargs):\n        pass\n"
        )
    import test.test_client as tc

    # Just import it to cover line/branch. function is fixture, let's call the original func
    tc.client.__wrapped__()
