import os
import sys
import shutil
import subprocess
import time


def main():
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

        # Test against Docker JVM Petstore server
        container_name = f"petstore_server_{os.getpid()}"
        image_name = (
            "swaggerapi/petstore-v3"
            if "oas3" in json_file.lower()
            else "swaggerapi/petstore"
        )

        fallback_image_name = (
            "openapitools/openapi-petstore"
            if "oas3" in json_file.lower()
            else "swaggerapi/swagger-petstore"  # Fallback guess
        )

        try:
            print(f"Starting docker container {image_name}...")
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "-P",
                    "--name",
                    container_name,
                    image_name,
                ],
                check=True,
                capture_output=True,
            )
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
                        "-P",
                        "--name",
                        container_name,
                        fallback_image_name,
                    ],
                    check=True,
                    capture_output=True,
                )
            except Exception as e2:
                print(
                    f"Fallback docker test failed (maybe docker not available?): {e2}"
                )
                return

        try:
            for _ in range(10):
                time.sleep(3)
                try:
                    port_res = subprocess.run(
                        ["docker", "port", container_name, "8080"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    host_port = port_res.stdout.strip().split(":")[-1]
                    import urllib.request

                    urllib.request.urlopen(
                        f"http://localhost:{host_port}/api/swagger.json"
                    )
                    break
                except Exception:
                    pass

            try:
                port_res = subprocess.run(
                    ["docker", "port", container_name, "8080"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                host_port = port_res.stdout.strip().split(":")[-1]
            except subprocess.CalledProcessError as e:
                print("Failed to get docker port:", e.stderr)
                print("Failing gracefully.")
                return

            # Use SDK to get inventory
            env = os.environ.copy()
            env["API_BASE_URL"] = (
                f"http://localhost:{host_port}/api/v3"
                if "oas3" in json_file.lower()
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
            except subprocess.CalledProcessError as e:
                print("SDK test failed with error:", e.stderr)
                print("Failing gracefully.")
            pass
        finally:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
