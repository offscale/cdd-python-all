import json
import re
import subprocess
import sys
import os


def run_tests():
    print("Running tests and coverage...")
    subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "--cov=src/openapi_client",
            "--cov-report=json",
            "tests/",
        ],
        check=True,
    )
    with open("coverage.json", "r") as f:
        data = json.load(f)
    test_cov = data["totals"]["percent_covered"]
    if os.path.exists("coverage.json"):
        os.remove("coverage.json")
    return test_cov


def run_interrogate():
    print("Running interrogate...")
    res = subprocess.run(
        [
            "uv",
            "run",
            "interrogate",
            "--ignore-init-method",
            "--ignore-init-module",
            "src/openapi_client/",
        ],
        capture_output=True,
        text=True,
    )
    match = re.search(r"actual: ([\d.]+)%", res.stdout)
    if match:
        return float(match.group(1))
    match = re.search(r"actual: ([\d.]+)%", res.stdout + res.stderr)
    if match:
        return float(match.group(1))

    # Let's run and display the error if any
    print(res.stderr)
    print("Could not find interrogate coverage")
    return 0.0


def update_readme(test_cov, doc_cov):
    print(f"Test Coverage: {test_cov:.1f}%")
    print(f"Doc Coverage: {doc_cov:.1f}%")

    with open("README.md", "r") as f:
        content = f.read()

    def get_color(cov):
        if cov >= 95:
            return "brightgreen"
        if cov >= 80:
            return "green"
        if cov >= 70:
            return "yellow"
        if cov >= 60:
            return "orange"
        return "red"

    test_color = get_color(test_cov)
    doc_color = get_color(doc_cov)

    test_badge = f"[![Test Coverage](https://img.shields.io/badge/Test_Coverage-{test_cov:.1f}%25-{test_color})](https://github.com/offscale/cdd-python-client/actions)"
    doc_badge = f"[![Doc Coverage](https://img.shields.io/badge/Doc_Coverage-{doc_cov:.1f}%25-{doc_color})](https://github.com/offscale/cdd-python-client/actions)"

    # Regex search for existing badges
    if "![Test Coverage]" in content and "![Doc Coverage]" in content:
        content = re.sub(
            r"\[?!\[Test Coverage\]\(https://img\.shields\.io/badge/Test_Coverage-[^\)]+\)\]?(?:\(https://[^\)]+\))?",
            test_badge,
            content,
        )
        content = re.sub(
            r"\[?!\[Doc Coverage\]\(https://img\.shields\.io/badge/Doc_Coverage-[^\)]+\)\]?(?:\(https://[^\)]+\))?",
            doc_badge,
            content,
        )
    else:
        # replace the placeholder from template
        if "<!-- REPLACE WITH separate test and doc coverage badges" in content:
            content = content.replace(
                "<!-- REPLACE WITH separate test and doc coverage badges that you generate in pre-commit hook -->",
                f"{test_badge}\n{doc_badge}",
            )
        else:
            # prepend to README
            content = f"{test_badge}\n{doc_badge}\n\n" + content

    with open("README.md", "w") as f:
        f.write(content)


if __name__ == "__main__":
    try:
        t_cov = run_tests()
        d_cov = run_interrogate()
        update_readme(t_cov, d_cov)
    except Exception as e:
        print(f"Failed to update badges: {e}")
        sys.exit(1)
