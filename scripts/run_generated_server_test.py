"""Run generated server tests."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request


def find_free_port() -> int:
    """Find a free TCP port on localhost.

    Returns:
        An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port: int = s.getsockname()[1]
        return port


def main() -> None:
    """Execute end-to-end generated server and client verification."""
    if os.environ.get("RUN_SLOW_TESTS") != "1":
        print("Skipping slow test. Set RUN_SLOW_TESTS=1 to run.")
        sys.exit(0)

    test_harness_dir = os.environ.get(
        "TEST_HARNESS_DIR", os.path.expanduser("~/repos/cdd-openapi-test-harness")
    )

    if len(sys.argv) < 3:
        print("Usage: run_generated_server_test.py <json_file> <tmp_dir>")
        sys.exit(1)

    json_file = sys.argv[1]
    tmp_dir = os.path.abspath(sys.argv[2])

    server_dir = os.path.join(tmp_dir, "server")
    client_dir = os.path.join(tmp_dir, "client")

    input_path = os.path.join(test_harness_dir, json_file)
    if not os.path.exists(input_path):
        print(f"Skipping test, missing {input_path}")
        sys.exit(0)

    try:
        print(f"Generating server from {input_path} -> {server_dir}")
        subprocess.run(
            [
                "uv",
                "run",
                "cdd-python",
                "from_openapi",
                "to_server",
                "-i",
                input_path,
                "-o",
                server_dir,
            ],
            check=True,
        )

        print(f"Generating client from {input_path} -> {client_dir}")
        subprocess.run(
            [
                "uv",
                "run",
                "cdd-python",
                "from_openapi",
                "to_sdk_cli",
                "-i",
                input_path,
                "-o",
                client_dir,
            ],
            check=True,
        )

        port = find_free_port()
        print(f"Starting generated server on port {port}...")

        env = os.environ.copy()
        env["PORT"] = str(port)
        env.pop("VIRTUAL_ENV", None)

        subprocess.run(["uv", "venv"], cwd=server_dir, env=env, check=True)
        subprocess.run(
            ["uv", "pip", "install", "-e", ".", "pytest", "httpx"],
            cwd=server_dir,
            env=env,
            check=True,
        )

        print("Running generated server tests...")
        subprocess.run(
            [
                os.path.join(server_dir, ".venv", "bin", "python"),
                "-m",
                "pytest",
                "tests/",
            ],
            cwd=server_dir,
            env=env,
            check=True,
        )

        server_process = subprocess.Popen(
            [
                os.path.join(server_dir, ".venv", "bin", "python"),
                "main.py",
                "--ephemeral",
                "--seed",
            ],
            cwd=server_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        server_ready = False
        try:
            for _ in range(30):
                time.sleep(1)
                try:
                    urllib.request.urlopen(
                        f"http://localhost:{port}/openapi.json", timeout=1
                    )
                    server_ready = True
                    break
                except OSError:
                    pass

            if not server_ready:
                print("Server failed to start or become ready in time.")
                server_process.terminate()
                stdout, _ = server_process.communicate()
                print(stdout.decode("utf-8", errors="ignore"))
                sys.exit(1)

            print("Server is ready. Testing SDK...")

            client_env = os.environ.copy()
            client_env["API_BASE_URL"] = f"http://localhost:{port}"
            client_env.pop("VIRTUAL_ENV", None)

            subprocess.run(["uv", "venv"], cwd=client_dir, env=client_env, check=True)
            subprocess.run(
                ["uv", "pip", "install", "-e", "."],
                cwd=client_dir,
                env=client_env,
                check=True,
            )

            test_cmd = [
                os.path.join(client_dir, ".venv", "bin", "python"),
                os.path.join("src", "cli_main.py"),
                "get_inventory",
            ]
            print(f"Testing SDK with command: {' '.join(test_cmd)}")
            try:
                result = subprocess.run(
                    test_cmd,
                    cwd=client_dir,
                    env=client_env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print("SDK output:")
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print("SDK test failed with error:")
                print(e.stderr)
                print("Server output:")
                server_process.terminate()
                stdout, _ = server_process.communicate()
                print(stdout.decode("utf-8", errors="ignore"))
                sys.exit(1)

        finally:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            server_process.communicate()

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
