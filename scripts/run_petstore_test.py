"""Run tests against the Petstore server."""

import os
import sys
import shutil
import subprocess
import time
import socket


def find_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def main():
    """Main execution of the petstore test."""
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
    tmp_server_dir = tmp_dir + "_server"

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
        host_port = None
        container_name = None

        import urllib.request

        default_port = 8081 if is_oas3 else 8080
        test_url = (
            f"http://localhost:{default_port}/api/v3/swagger.json"
            if is_oas3
            else f"http://localhost:{default_port}/api/swagger.json"
        )

        try:
            print(f"Checking if existing mock server is pingable at {test_url}...")
            urllib.request.urlopen(test_url, timeout=2)
            host_port = str(default_port)
            print(f"Found active mock server on port {host_port}")
        except Exception:
            print("No active mock server found.")

        if not host_port:
            print("Falling back to Docker JVM Petstore server...")
            container_name = f"petstore_server_{os.getpid()}"
            image_name = "swaggerapi/petstore-v3" if is_oas3 else "swaggerapi/petstore"

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
            except Exception as e:
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
                except Exception as e2:
                    print(
                        f"Fallback docker test failed (maybe docker not available?): {e2}"
                    )
                    return

            try:
                for _ in range(15):
                    time.sleep(2)
                    try:
                        urllib.request.urlopen(test_url, timeout=1)
                        print("Docker mock server is ready.")
                        break
                    except Exception:
                        pass
                else:
                    print("Docker mock server failed to become ready.")
                    return
            except Exception as e:
                print(f"Docker fallback setup failed: {e}")
                return

        try:
            # Use SDK to get inventory
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
                    ["docker", "rm", "-f", container_name], capture_output=True
                )

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        if os.path.exists(tmp_server_dir):
            shutil.rmtree(tmp_server_dir)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
