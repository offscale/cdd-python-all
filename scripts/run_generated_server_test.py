import os
import sys
import shutil
import subprocess
import time
import socket
import urllib.request


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
        # Generate Server
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

        # Generate Client
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

        # Start Server
        port = find_free_port()
        print(f"Starting generated server on port {port}...")

        env = os.environ.copy()
        env["PORT"] = str(port)
        env.pop("VIRTUAL_ENV", None)

        # We need to install dependencies for the server.
        # uv run in the generated directory might inherit the parent environment.
        # It's safer to create a venv and install.
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
                except Exception:
                    pass

            if not server_ready:
                print("Server failed to start or become ready in time.")
                server_process.terminate()
                stdout, _ = server_process.communicate()
                print(stdout.decode("utf-8", errors="ignore"))
                sys.exit(1)

            print("Server is ready. Testing SDK...")

            # Use SDK to get inventory
            client_env = os.environ.copy()
            client_env["API_BASE_URL"] = f"http://localhost:{port}"
            client_env.pop("VIRTUAL_ENV", None)

            # Setup client venv to isolate
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
            stdout, _ = server_process.communicate()
            # print("Server final output:")
            # print(stdout.decode("utf-8", errors="ignore"))

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    main()
