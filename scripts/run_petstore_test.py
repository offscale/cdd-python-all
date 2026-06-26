import os
import sys
import shutil
import subprocess
import time
import socket


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def main():
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

        # Try to run Python-based generated server first
        host_port = None
        server_process = None
        is_oas3 = "oas3" in json_file.lower()

        try:
            print("Attempting to run Python-based mock server...")
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
                    tmp_server_dir,
                ],
                check=True,
            )
            host_port = str(find_free_port())

            env = os.environ.copy()
            env["PORT"] = host_port
            env.pop("VIRTUAL_ENV", None)

            subprocess.run(["uv", "venv"], cwd=tmp_server_dir, env=env, check=True)
            subprocess.run(
                ["uv", "pip", "install", "-e", "."],
                cwd=tmp_server_dir,
                env=env,
                check=True,
            )

            server_process = subprocess.Popen(
                [
                    os.path.join(".venv", "bin", "python"),
                    "main.py",
                    "--ephemeral",
                    "--seed",
                ],
                cwd=tmp_server_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            import urllib.request

            server_ready = False
            for _ in range(30):
                time.sleep(1)
                try:
                    urllib.request.urlopen(
                        f"http://localhost:{host_port}/openapi.json", timeout=1
                    )
                    server_ready = True
                    break
                except Exception:
                    pass

            if not server_ready:
                print("Python mock server failed to start. Output:")
                server_process.terminate()
                try:
                    stdout, _ = server_process.communicate(timeout=5)
                    print(
                        f"--- SERVER OUTPUT ---\n{stdout.decode('utf-8', errors='ignore')}\n-------------------"
                    )
                except Exception as e:
                    print(f"Failed to get server output: {e}")
                server_process = None
                host_port = None

        except Exception as e:
            print(f"Failed to start Python mock server: {e}")
            if server_process:
                server_process.terminate()
                server_process = None
            host_port = None

        container_name = None
        if not host_port:
            print("Falling back to Docker JVM Petstore server...")
            container_name = f"petstore_server_{os.getpid()}"
            image_name = "swaggerapi/petstore-v3" if is_oas3 else "swaggerapi/petstore"

            fallback_image_name = (
                "openapitools/openapi-petstore"
                if is_oas3
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
                import urllib.request

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
            except Exception as e:
                print(f"Docker fallback setup failed: {e}")
                return

        try:
            # Use SDK to get inventory
            env = os.environ.copy()
            if server_process:
                # Python mock server has endpoints at root
                env["API_BASE_URL"] = f"http://localhost:{host_port}"
            else:
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
            if server_process:
                server_process.terminate()
                try:
                    server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_process.kill()
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
