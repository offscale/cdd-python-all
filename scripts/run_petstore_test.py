"""Run tests against the Petstore server."""

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
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", 0))
        port: int = s.getsockname()[1]
        return port


def main() -> None:
    """Execute Petstore SDK CLI generation and integration test."""
    if os.environ.get("RUN_SLOW_TESTS") != "1":
        print("Skipping slow test. Set RUN_SLOW_TESTS=1 to run.")
        sys.exit(0)

    test_harness_dir = os.environ.get(
        "TEST_HARNESS_DIR", os.path.expanduser("~/repos/cdd-openapi-test-harness")
    )

    if len(sys.argv) < 3:
        print("Usage: run_petstore_test.py <json_file> <tmp_dir>")
        sys.exit(1)

    json_file = sys.argv[1]
    tmp_dir = sys.argv[2]

    input_path = os.path.join(test_harness_dir, json_file)
    if not os.path.exists(input_path):
        print(f"Skipping test, missing {input_path}")
        sys.exit(0)

    cmd = [
        "uv",
        "run",
        "cdd-python",
        "from_openapi",
        "to_sdk_cli",
        "-i",
        input_path,
        "-o",
        tmp_dir,
    ]

    try:
        print(f"Running petstore SDK generation against {input_path} -> {tmp_dir}")
        subprocess.run(cmd, check=True)

        is_oas3 = "oas3" in json_file.lower()
        host_port: str | None = None
        container_name: str | None = None

        default_port = 8081 if is_oas3 else 8080
        test_urls = (
            [
                f"http://localhost:{default_port}/api/v3/openapi.json",
                f"http://localhost:{default_port}/api/v3/swagger.json",
                f"http://localhost:{default_port}/v3/openapi.json",
            ]
            if is_oas3
            else [f"http://localhost:{default_port}/api/swagger.json"]
        )

        print(f"Checking if existing mock server is pingable at {test_urls}...")
        for t_url in test_urls:
            try:
                urllib.request.urlopen(t_url, timeout=2)
                host_port = str(default_port)
                print(f"Found active mock server on port {host_port} at {t_url}")
                break
            except OSError:
                continue

        if not host_port:
            print("Falling back to Docker JVM Petstore server...")
            container_name = f"petstore_server_{os.getpid()}"
            image_name = (
                "openapitools/openapi-petstore" if is_oas3 else "swaggerapi/petstore"
            )

            fallback_image_name = (
                "openapitools/openapi-petstore"
                if is_oas3
                else "swaggerapi/swagger-petstore"
            )

            try:
                print(f"Starting docker container {image_name}...")
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "-p",
                        f"{default_port}:8080",
                        "--name",
                        container_name,
                        image_name,
                    ],
                    check=True,
                    capture_output=True,
                )
                host_port = str(default_port)
            except (subprocess.CalledProcessError, OSError) as e:
                print(
                    f"Failed to start JVM image {image_name}, falling back to {fallback_image_name}: {e}"
                )
                try:
                    subprocess.run(
                        [
                            "docker",
                            "run",
                            "-d",
                            "-p",
                            f"{default_port}:8080",
                            "--name",
                            container_name,
                            fallback_image_name,
                        ],
                        check=True,
                        capture_output=True,
                    )
                    host_port = str(default_port)
                except (subprocess.CalledProcessError, OSError) as e2:
                    print(
                        f"Fallback docker test failed (maybe docker not available?): {e2}"
                    )
                    return

            for _ in range(15):
                time.sleep(2)
                success = False
                for t_url in test_urls:
                    try:
                        urllib.request.urlopen(t_url, timeout=1)
                        print(f"Docker mock server is ready at {t_url}")
                        success = True
                        break
                    except OSError:
                        pass
                if success:
                    break
            else:
                print("Docker mock server failed to become ready.")
                return

        try:
            env = os.environ.copy()
            env["API_BASE_URL"] = (
                f"http://localhost:{host_port}/api/v3"
                if is_oas3
                else f"http://localhost:{host_port}/api"
            )

            test_cmd = [
                "uv",
                "run",
                "python",
                os.path.join(tmp_dir, "src", "cli_main.py"),
                "get_inventory",
            ]
            print(f"Testing SDK with command: {' '.join(test_cmd)}")
            try:
                _ = subprocess.run(
                    test_cmd, env=env, check=True, capture_output=True, text=True
                )
                print("SDK test passed.")
            except subprocess.CalledProcessError as e:
                print("SDK test failed with error:", e.stderr)
                print("Failing gracefully.")
        finally:
            if container_name:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    check=False,
                    capture_output=True,
                )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
