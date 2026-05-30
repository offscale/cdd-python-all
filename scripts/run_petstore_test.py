import os
import sys
import shutil
import subprocess


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
        print(f"Running petstore test against {input_path} -> {tmp_dir}")
        subprocess.run(cmd, check=True)
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
