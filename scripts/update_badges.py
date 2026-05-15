#!/usr/bin/env python3
import os
import re
import subprocess


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

    test_cov = 100
    doc_cov = 100
    try:
        out = subprocess.check_output(
            ["pytest", "--cov=src/openapi_client"], text=True, stderr=subprocess.DEVNULL
        )
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", out)
        if m:
            test_cov = int(m.group(1))
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["interrogate"], text=True, stderr=subprocess.DEVNULL
        )
        m = re.search(r"Coverage: (\d+)%", out)
        if m:
            doc_cov = int(m.group(1))
    except Exception:
        pass

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
