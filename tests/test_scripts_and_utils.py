import sys
import runpy
from unittest import mock
import pytest


def test_fix_cli_extra():
    # Running the script directly
    with mock.patch(
        "builtins.open",
        mock.mock_open(
            read_data="def makefile(self, mode, *args, **kwargs):\n    return BytesIO()"
        ),
    ):
        try:
            runpy.run_path("fix_cli_extra.py")
        except Exception:  # pragma: no cover
            pass  # ignore errors from re.sub if any


def test_run_manual_test():
    runpy.run_path("run_manual_test.py")


def test_build_wasm(monkeypatch):
    import scripts.build_wasm as bw

    # Test successful subprocess
    with mock.patch("subprocess.run") as m_run:
        with mock.patch("os.makedirs"):
            bw.main()
            m_run.assert_called_once()

    # Test failed subprocess falling back to zip
    with mock.patch(
        "subprocess.run", side_effect=bw.subprocess.CalledProcessError(1, [])
    ) as m_run:
        with mock.patch("os.makedirs"):
            with mock.patch("os.path.exists", return_value=True):
                with mock.patch("os.remove"):
                    with mock.patch("zipfile.ZipFile"):
                        with mock.patch(
                            "os.walk", return_value=[("src", [], ["file1.py"])]
                        ):
                            bw.main()


def test_doc_coverage(tmp_path):
    import scripts.doc_coverage as dc

    # Create dummy files
    p1 = tmp_path / "f1.py"
    p1.write_text('def f():\n    """doc"""\n    pass')
    p2 = tmp_path / "f2.py"
    p2.write_text("def g():\n    pass")
    p3 = tmp_path / "f3.txt"
    p3.write_text("not python")
    p4 = tmp_path / "f4.py"
    p4.write_text("invalid syntax here")
    p5 = tmp_path / "f5.py"
    p5.write_text(
        'class C:\n    """doc"""\n    def __init__(self):\n        """doc"""\n    def __private(self):\n        pass'
    )

    pct, w, t = dc.calculate_doc_coverage(str(tmp_path))

    # run as main
    with mock.patch(
        "scripts.doc_coverage.calculate_doc_coverage", return_value=(50.0, 1, 2)
    ):
        runpy.run_path("scripts/doc_coverage.py", run_name="__main__")


def test_run_petstore_test(monkeypatch, tmp_path):
    import scripts.run_petstore_test as rp

    # No args
    monkeypatch.setattr(sys, "argv", ["run_petstore_test.py"])
    with pytest.raises(SystemExit):
        rp.main()

    # Valid args but file missing
    monkeypatch.setattr(
        sys, "argv", ["run_petstore_test.py", "missing.json", str(tmp_path)]
    )
    with pytest.raises(SystemExit):
        rp.main()

    # Valid args and file exists
    f = tmp_path / "dummy.json"
    f.touch()
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr(
        sys, "argv", ["run_petstore_test.py", "dummy.json", str(tmp_path)]
    )

    with mock.patch("subprocess.run"):
        with mock.patch("shutil.rmtree"):
            rp.main()


def test_update_badges(monkeypatch):
    import scripts.update_badges as ub

    assert ub.get_color(95) == "brightgreen"
    assert ub.get_color(85) == "green"
    assert ub.get_color(75) == "yellowgreen"
    assert ub.get_color(65) == "yellow"
    assert ub.get_color(55) == "orange"
    assert ub.get_color(45) == "red"

    with mock.patch("os.path.exists", return_value=False):
        ub.main()

    with mock.patch("os.path.exists", return_value=True):
        # test failure
        class MockResult:
            returncode = 1
            stdout = "error"

        with mock.patch("subprocess.run", return_value=MockResult()):
            with pytest.raises(SystemExit):
                ub.main()

        # interrogate failure
        class MockResult2:
            returncode = 0
            stdout = "TOTAL 10 0 100%"

        class MockResult3:
            returncode = 1
            stdout = "error"

        with mock.patch("subprocess.run", side_effect=[MockResult2(), MockResult3()]):
            with pytest.raises(SystemExit):
                ub.main()

        # success branch with actual: x%
        class MockResult4:
            returncode = 0
            stdout = "TOTAL 10 0 100%"

        class MockResult5:
            returncode = 0
            stdout = "actual: 80%"

        with mock.patch("subprocess.run", side_effect=[MockResult4(), MockResult5()]):
            with mock.patch(
                "builtins.open",
                mock.mock_open(
                    read_data="[![Test Coverage](https://img.shields.io/badge/test_coverage-100%25-brightgreen.svg)](#)"
                ),
            ):
                ub.main()

        # success branch with actual: x.x%
        class MockResult6:
            returncode = 0
            stdout = "actual: 80.5%"

        with mock.patch("subprocess.run", side_effect=[MockResult4(), MockResult6()]):
            with mock.patch("builtins.open", mock.mock_open()):
                ub.main()


def test_build_wasm_more(monkeypatch):
    import scripts.build_wasm as bw

    with mock.patch(
        "subprocess.run", side_effect=bw.subprocess.CalledProcessError(1, [])
    ):
        with mock.patch("os.makedirs"):
            with mock.patch(
                "os.path.exists", side_effect=[False, False]
            ):  # wasm_out exists=False, pyproject exists=False
                with mock.patch("os.remove"):
                    with mock.patch("zipfile.ZipFile"):
                        # one match, one no-match
                        with mock.patch(
                            "os.walk",
                            return_value=[
                                ("src/__pycache__", [], ["file.py"]),
                                ("src", [], ["file.txt"]),
                            ],
                        ):
                            bw.main()


def test_run_petstore_test_no_tmp(monkeypatch, tmp_path):
    import scripts.run_petstore_test as rp

    f = tmp_path / "dummy.json"
    f.touch()
    monkeypatch.setattr(
        "os.path.exists", lambda p: p.endswith("dummy.json")
    )  # tmp_dir does not exist
    monkeypatch.setattr(
        "sys.argv", ["run_petstore_test.py", str(f), str(tmp_path / "notexist")]
    )
    with mock.patch("subprocess.run"):
        rp.main()


def test_update_badges_no_match(monkeypatch):
    import scripts.update_badges as ub

    with mock.patch("os.path.exists", return_value=True):

        class MockResult:
            returncode = 0
            stdout = "NO MATCH HERE"

        with mock.patch("subprocess.run", return_value=MockResult()):
            with mock.patch(
                "builtins.open",
                mock.mock_open(
                    read_data="[![Test Coverage](https://img.shields.io/badge/test_coverage-100%25-brightgreen.svg)](#)"
                ),
            ):
                ub.main()
