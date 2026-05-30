import os
import subprocess


def main():
    os.makedirs("bin", exist_ok=True)
    wasm_out = os.path.join("bin", "cdd-python-all.wasm")

    try:
        print("Building WASI...")
        subprocess.run(
            ["uv", "run", "py2wasm", "src/openapi_client/cli.py", "-o", wasm_out],
            check=True,
        )
    except subprocess.CalledProcessError:
        print("WASI build failed. Falling back to Pyodide zip bundle.")
        if os.path.exists(wasm_out):
            os.remove(wasm_out)

        # Cross-platform zip
        import zipfile

        with zipfile.ZipFile(wasm_out, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk("src"):
                for file in files:
                    if "__pycache__" not in root and file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, file_path)
            if os.path.exists("pyproject.toml"):
                zipf.write("pyproject.toml", "pyproject.toml")


if __name__ == "__main__":  # pragma: no cover
    main()
