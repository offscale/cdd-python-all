#!/usr/bin/env python3
import os
import re
import subprocess
import sys


def get_color(pct):
    if pct >= 90:
        return "brightgreen"
    if pct >= 80:
        return "green"
    if pct >= 70:
        return "yellowgreen"
    if pct >= 60:
        return "yellow"
    if pct >= 50:
        return "orange"
    return "red"


def main():
    readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
    if not os.path.exists(readme_path):
        return

    print("Running tests and calculating coverage...")
    test_result = subprocess.run(
        ["pytest", "--cov=src/openapi_client", "--cov-report=term"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if test_result.returncode != 0:
        print("Tests failed!")
        print(test_result.stdout)
        sys.exit(test_result.returncode)

    test_cov = 100
    m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", test_result.stdout)
    if m:
        test_cov = int(m.group(1))

    print("Running interrogate for doc coverage...")
    doc_result = subprocess.run(
        ["interrogate", "--fail-under=0", "src/openapi_client"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if doc_result.returncode != 0 and "Coverage:" not in doc_result.stdout:
        print("Interrogate failed!")
        print(doc_result.stdout)
        sys.exit(doc_result.returncode)

    doc_cov = 100
    m = re.search(r"actual:\s*([0-9]+)\.[0-9]*%", doc_result.stdout)
    if m:
        doc_cov = int(m.group(1))
    else:
        m2 = re.search(r"actual:\s*([0-9]+)%", doc_result.stdout)
        if m2:
            doc_cov = int(m2.group(1))

    test_color = get_color(test_cov)
    doc_color = get_color(doc_cov)

    with open(readme_path) as f:
        content = f.read()

    content = re.sub(
        r"\[\!\[Test Coverage\]\(https://img\.shields\.io/badge/test_coverage-[0-9.]+%25-[a-z]+\.svg\)\]\(#\)",
        f"[![Test Coverage](https://img.shields.io/badge/test_coverage-{test_cov}%25-{test_color}.svg)](#)",
        content,
    )

    content = re.sub(
        r"\[\!\[Doc Coverage\]\(https://img\.shields\.io/badge/doc_coverage-[0-9.]+%25-[a-z]+\.svg\)\]\(#\)",
        f"[![Doc Coverage](https://img.shields.io/badge/doc_coverage-{doc_cov}%25-{doc_color}.svg)](#)",
        content,
    )

    with open(readme_path, "w") as f:
        f.write(content)


if __name__ == "__main__":
    main()
