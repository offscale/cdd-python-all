"""Tests for build_wasm, doc_coverage, update_badges, and Petstore/server test scripts."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from unittest import mock

import libcst as cst
import pytest

from openapi_client.models import OpenAPI
from openapi_client.tests.parse import ASTTestExtractor


def test_ast_test_extractor_manual_cases() -> None:
    """Test ASTTestExtractor on stream and non-stream test functions."""
    spec = OpenAPI(openapi="3.2.0", info={"title": "Test", "version": "1.0.0"})

    code = """
def test_stream_something() -> None:
    response = "text/event-stream"

def test_stream_but_no_event_stream() -> None:
    response = "application/json"

def test_normal_function() -> None:
    pass
"""
    module = cst.parse_module(code)
    visitor = ASTTestExtractor(spec)
    module.visit(visitor)
    assert visitor.spec.paths is not None
    assert "/stream_something" in visitor.spec.paths
    stream_op = visitor.spec.paths["/stream_something"].get
    assert stream_op is not None
    assert stream_op.responses is not None
    resp_200 = stream_op.responses["200"]
    assert getattr(resp_200, "content", None) is not None
    assert "text/event-stream" in resp_200.content
    assert "/stream_but_no_event_stream" not in visitor.spec.paths


def test_build_wasm() -> None:
    """Test build_wasm main with successful and fallback execution."""
    import scripts.build_wasm as bw

    with mock.patch("subprocess.run") as m_run, mock.patch("os.makedirs"):
        bw.main()
        m_run.assert_called_once()

    with (
        mock.patch(
            "subprocess.run", side_effect=bw.subprocess.CalledProcessError(1, [])
        ),
        mock.patch("os.makedirs"),
        mock.patch("os.path.exists", return_value=True),
        mock.patch("os.remove") as m_rm,
        mock.patch("zipfile.ZipFile"),
        mock.patch("os.walk", return_value=[("src", [], ["file1.py"])]),
    ):
        bw.main()
        m_rm.assert_called_once()


def test_doc_coverage(tmp_path: Path) -> None:
    """Test calculate_doc_coverage on sample Python files, *args/**kwargs, and SyntaxError failure.

    Args:
        tmp_path: Parameter .
    """
    import scripts.doc_coverage as dc

    nl = chr(10)
    p1 = tmp_path / "f1.py"
    p1.write_text(
        f'"""Mod doc."""{nl}{nl}{nl}def f(x: int, /, y: str, *args: int, kw: bool = True, **kwargs: str) -> None:{nl}    """Doc.{nl}{nl}    Args:{nl}        x: Posonly.{nl}        y: Regular.{nl}        *args: Varargs.{nl}        kw: Kwonly.{nl}        **kwargs: Kwargs.{nl}    """{nl}    pass{nl}',
        encoding="utf-8",
    )
    p2 = tmp_path / "f2.py"
    p2.write_text(f"def g(y):{nl}    pass{nl}", encoding="utf-8")
    p3 = tmp_path / "f3.txt"
    p3.write_text("not python", encoding="utf-8")
    p4 = tmp_path / "f4.py"
    p4.write_text("invalid syntax here", encoding="utf-8")
    p5 = tmp_path / "f5.py"
    p5.write_text(
        f'"""Mod doc."""{nl}{nl}{nl}class C:{nl}    """Doc."""{nl}{nl}    def __init__(self) -> None:{nl}        """Doc."""{nl}        pass{nl}{nl}    def __private(self) -> None:{nl}        pass{nl}',
        encoding="utf-8",
    )

    with pytest.raises(SyntaxError):
        dc.calculate_doc_coverage(str(tmp_path))

    p4.unlink()
    pct, w, t = dc.calculate_doc_coverage(str(tmp_path))
    assert t > 0
    assert 0.0 < pct < 100.0
    assert w < t

    empty_dir = tmp_path / "empty_sub"
    empty_dir.mkdir()
    assert dc.calculate_doc_coverage(str(empty_dir)) == (0.0, 0, 0)

    with mock.patch(
        "scripts.doc_coverage.calculate_doc_coverage", return_value=(50.0, 1, 2)
    ):
        runpy.run_path("scripts/doc_coverage.py", run_name="__main__")


def test_run_petstore_test(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test run_petstore_test script argument validation and execution.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    monkeypatch.setenv("RUN_SLOW_TESTS", "1")
    import scripts.run_petstore_test as rp

    monkeypatch.setattr(sys, "argv", ["run_petstore_test.py"])
    with pytest.raises(SystemExit):
        rp.main()

    monkeypatch.setattr(
        "sys.argv", ["run_petstore_test.py", "missing.json", str(tmp_path)]
    )
    with pytest.raises(SystemExit):
        rp.main()

    f = tmp_path / "dummy.json"
    f.touch()
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr(
        "sys.argv", ["run_petstore_test.py", "dummy.json", str(tmp_path)]
    )

    with (
        mock.patch("subprocess.run") as m_run,
        mock.patch("shutil.rmtree"),
        mock.patch("time.sleep"),
    ):
        rp.main()
        assert m_run.called


def test_update_badges() -> None:
    """Test update_badges color mapping and README badge updates."""
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

        class MockResult:
            """Mock subprocess result for failed test run."""

            returncode = 1
            stdout = "error"

        with (
            mock.patch("subprocess.run", return_value=MockResult()),
            pytest.raises(SystemExit),
        ):
            ub.main()

        class MockResult2:
            """Mock subprocess result for passing test run."""

            returncode = 0
            stdout = "TOTAL 10 0 100%"

        class MockResult3:
            """Mock subprocess result for failed interrogate run."""

            returncode = 1
            stdout = "error"

        with (
            mock.patch("subprocess.run", side_effect=[MockResult2(), MockResult3()]),
            pytest.raises(SystemExit),
        ):
            ub.main()

        class MockResult4:
            """Mock subprocess result for passing test run."""

            returncode = 0
            stdout = "TOTAL 10 0 100%"

        class MockResult5:
            """Mock subprocess result for integer doc coverage."""

            returncode = 0
            stdout = "actual: 80%"

        with (
            mock.patch("subprocess.run", side_effect=[MockResult4(), MockResult5()]),
            mock.patch(
                "builtins.open",
                mock.mock_open(
                    read_data="[![Test Coverage](https://img.shields.io/badge/test_coverage-100%25-brightgreen.svg)](#)"
                ),
            ) as m_open,
        ):
            ub.main()
            assert m_open.called

        class MockResult6:
            """Mock subprocess result for float doc coverage."""

            returncode = 0
            stdout = "actual: 80.5%"

        with (
            mock.patch("subprocess.run", side_effect=[MockResult4(), MockResult6()]),
            mock.patch("builtins.open", mock.mock_open()) as m_open,
        ):
            ub.main()
            assert m_open.called


def test_build_wasm_more() -> None:
    """Test build_wasm fallback when wasm_out and pyproject.toml do not exist."""
    import scripts.build_wasm as bw

    with (
        mock.patch(
            "subprocess.run", side_effect=bw.subprocess.CalledProcessError(1, [])
        ),
        mock.patch("os.makedirs"),
        mock.patch("os.path.exists", side_effect=[False, False]),
        mock.patch("os.remove") as m_rm,
        mock.patch("zipfile.ZipFile"),
        mock.patch(
            "os.walk",
            return_value=[
                ("src/__pycache__", [], ["file.py"]),
                ("src", [], ["file.txt"]),
            ],
        ),
    ):
        bw.main()
        m_rm.assert_not_called()


def test_run_petstore_test_no_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test run_petstore_test when temporary directory does not exist at cleanup.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    monkeypatch.setenv("RUN_SLOW_TESTS", "1")
    import scripts.run_petstore_test as rp

    f = tmp_path / "dummy.json"
    f.touch()
    monkeypatch.setattr("os.path.exists", lambda p: p.endswith("dummy.json"))
    monkeypatch.setattr(
        "sys.argv", ["run_petstore_test.py", str(f), str(tmp_path / "notexist")]
    )
    with mock.patch("subprocess.run") as m_run, mock.patch("time.sleep"):
        rp.main()
        assert m_run.called


def test_update_badges_no_match() -> None:
    """Test update_badges when regex patterns do not match stdout."""
    import scripts.update_badges as ub

    with mock.patch("os.path.exists", return_value=True):

        class MockResult:
            """Mock subprocess result with non-matching output."""

            returncode = 0
            stdout = "NO MATCH HERE"

        with (
            mock.patch("subprocess.run", return_value=MockResult()),
            mock.patch(
                "builtins.open",
                mock.mock_open(
                    read_data="[![Test Coverage](https://img.shields.io/badge/test_coverage-100%25-brightgreen.svg)](#)"
                ),
            ) as m_open,
        ):
            ub.main()
            assert m_open.called


def test_run_petstore_test_all_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test all branches of scripts/run_petstore_test.py.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    import subprocess

    import scripts.run_petstore_test as rp

    port = rp.find_free_port()
    assert isinstance(port, int) and port > 0

    # 1. RUN_SLOW_TESTS != "1"
    monkeypatch.delenv("RUN_SLOW_TESTS", raising=False)
    with pytest.raises(SystemExit) as exc:
        rp.main()
    assert exc.value.code == 0

    monkeypatch.setenv("RUN_SLOW_TESTS", "1")
    monkeypatch.setenv("TEST_HARNESS_DIR", str(tmp_path))
    spec_file = tmp_path / "oas3_petstore.json"
    spec_file.write_text("{}", encoding="utf-8")
    out_dir = tmp_path / "out_petstore"
    out_dir.mkdir(exist_ok=True)
    (tmp_path / "out_petstore_server").mkdir(exist_ok=True)

    monkeypatch.setattr(
        sys, "argv", ["run_petstore_test.py", "oas3_petstore.json", str(out_dir)]
    )

    # 2. Active mock server pingable + SDK test passes
    with (
        mock.patch("subprocess.run") as m_run,
        mock.patch("urllib.request.urlopen", return_value=mock.MagicMock()),
        mock.patch("shutil.rmtree"),
    ):
        rp.main()
        assert m_run.call_count == 2

    # 3. Docker fallback: primary fails, fallback succeeds, ready on 2nd poll, SDK test fails, docker rm runs
    def side_effect_run(cmd, *args, **kwargs):
        """Mock subprocess.run for docker fallback and CLI failure.

        Args:
            cmd: Parameter .
            *args: Parameter .
            **kwargs: Parameter .
        """
        if (
            cmd[:2] == ["docker", "run"]
            and "openapitools/openapi-petstore" in cmd
            and not hasattr(side_effect_run, "failed_once")
        ):
            side_effect_run.failed_once = True
            raise subprocess.CalledProcessError(1, cmd)
        if "cli_main.py" in " ".join(cmd):
            raise subprocess.CalledProcessError(1, cmd, stderr="CLI error")
        return mock.MagicMock(stdout="ok", returncode=0)

    urlopen_calls = [
        OSError("down"),
        OSError("down"),
        OSError("down"),
        OSError("down"),
        mock.MagicMock(),
    ]
    with (
        mock.patch("subprocess.run", side_effect=side_effect_run),
        mock.patch("urllib.request.urlopen", side_effect=urlopen_calls),
        mock.patch("time.sleep"),
        mock.patch("shutil.rmtree"),
    ):
        rp.main()

    # 4. Docker fallback: both primary and fallback fail (swagger 2.0)
    spec_sw = tmp_path / "swagger_petstore.json"
    spec_sw.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["run_petstore_test.py", "swagger_petstore.json", str(out_dir)]
    )

    def side_effect_both_fail(cmd, *args, **kwargs):
        """Mock subprocess.run where docker run raises OSError.

        Args:
            cmd: Parameter .
            *args: Parameter .
            **kwargs: Parameter .
        """
        if cmd[:2] == ["docker", "run"]:
            raise OSError("Docker not installed")
        return mock.MagicMock(returncode=0)

    with (
        mock.patch("subprocess.run", side_effect=side_effect_both_fail),
        mock.patch("urllib.request.urlopen", side_effect=OSError("down")),
        mock.patch("shutil.rmtree"),
    ):
        rp.main()


def test_run_generated_server_test_all_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test all branches of scripts/run_generated_server_test.py.

    Args:
        monkeypatch: Parameter .
        tmp_path: Parameter .
    """
    import subprocess

    import scripts.run_generated_server_test as rg

    port = rg.find_free_port()
    assert isinstance(port, int) and port > 0

    # 1. RUN_SLOW_TESTS != "1"
    monkeypatch.delenv("RUN_SLOW_TESTS", raising=False)
    with pytest.raises(SystemExit) as exc:
        rg.main()
    assert exc.value.code == 0

    monkeypatch.setenv("RUN_SLOW_TESTS", "1")
    monkeypatch.setenv("TEST_HARNESS_DIR", str(tmp_path))

    # 2. Missing args
    monkeypatch.setattr(sys, "argv", ["run_generated_server_test.py"])
    with pytest.raises(SystemExit) as exc2:
        rg.main()
    assert exc2.value.code == 1

    # 3. Missing input_path
    out_dir = tmp_path / "gen_srv_tmp"
    monkeypatch.setattr(
        sys, "argv", ["run_generated_server_test.py", "missing.json", str(out_dir)]
    )
    with pytest.raises(SystemExit) as exc3:
        rg.main()
    assert exc3.value.code == 0

    # 4. Full success flow (first urlopen fails, second succeeds)
    spec_file = tmp_path / "petstore.json"
    spec_file.write_text("{}", encoding="utf-8")
    out_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(
        sys, "argv", ["run_generated_server_test.py", "petstore.json", str(out_dir)]
    )

    mock_proc = mock.MagicMock()
    mock_proc.communicate.return_value = (b"server logs", b"")

    with (
        mock.patch("subprocess.run", return_value=mock.MagicMock(stdout="200 OK")),
        mock.patch("subprocess.Popen", return_value=mock_proc),
        mock.patch(
            "urllib.request.urlopen",
            side_effect=[OSError("starting"), mock.MagicMock()],
        ),
        mock.patch("time.sleep"),
    ):
        rg.main()

    # 5. Server fails to become ready in time + TimeoutExpired on wait
    mock_proc_timeout = mock.MagicMock()
    mock_proc_timeout.communicate.return_value = (b"timeout logs", b"")
    mock_proc_timeout.wait.side_effect = subprocess.TimeoutExpired(
        cmd="main.py", timeout=5
    )

    with (
        mock.patch("subprocess.run", return_value=mock.MagicMock(stdout="ok")),
        mock.patch("subprocess.Popen", return_value=mock_proc_timeout),
        mock.patch("urllib.request.urlopen", side_effect=OSError("down")),
        mock.patch("time.sleep"),
        pytest.raises(SystemExit) as exc4,
    ):
        rg.main()
    assert exc4.value.code == 1
    mock_proc_timeout.kill.assert_called_once()

    # 6. Server ready, but SDK test command fails with CalledProcessError
    out_dir.mkdir(exist_ok=True)

    def run_fail_sdk(cmd, *args, **kwargs):
        """Mock subprocess.run where cli_main.py fails.

        Args:
            cmd: Parameter .
            *args: Parameter .
            **kwargs: Parameter .
        """
        if "cli_main.py" in " ".join(cmd):
            raise subprocess.CalledProcessError(1, cmd, stderr="SDK failed")
        return mock.MagicMock(stdout="ok")

    with (
        mock.patch("subprocess.run", side_effect=run_fail_sdk),
        mock.patch("subprocess.Popen", return_value=mock_proc),
        mock.patch("urllib.request.urlopen", return_value=mock.MagicMock()),
        mock.patch("time.sleep"),
        mock.patch("shutil.rmtree"),
        pytest.raises(SystemExit) as exc5,
    ):
        rg.main()
    assert exc5.value.code == 1
