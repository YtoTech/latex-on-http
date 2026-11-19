"""
tests.test_compiler
~~~~~~~~~~~~~~~~~~~
Check compiler process output and log decoding.

:copyright: (c) 2017-2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import logging
import sys
import time

import pytest

from latexonhttp import compiler
from latexonhttp.sandbox import SandboxUnavailable


def fake_command_result(command):
    return {
        "command": command,
        "return_code": 12,
        "stdout": "",
        "duration": 0,
        "is_timeout": False,
    }


def test_run_command_replaces_invalid_utf8_output(tmp_path):
    result = compiler.run_command(
        tmp_path,
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.buffer.write(b'latex output: \\x9d\\n'); "
                "raise SystemExit(12)"
            ),
        ],
        isolate=False,
    )

    assert result["return_code"] == 12
    assert "latex output: \ufffd\n" in result["stdout"]


def test_failed_command_logs_full_output(tmp_path, caplog):
    caplog.set_level(logging.DEBUG, logger="latexonhttp.compiler")

    result = compiler.run_command(
        tmp_path,
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stderr.write('LATEX_DIAGNOSTIC\\nSECOND_DIAGNOSTIC_LINE'); "
                "raise SystemExit(12)"
            ),
        ],
        isolate=False,
    )

    assert result["return_code"] == 12
    assert "return code 12" in caplog.text
    assert "Command output:" in caplog.text
    assert "LATEX_DIAGNOSTIC" in caplog.text
    assert "SECOND_DIAGNOSTIC_LINE" in caplog.text


def test_latex_to_pdf_replaces_invalid_utf8_in_log_files(tmp_path, monkeypatch):
    (tmp_path / "main.log").write_bytes(b"latex log: \x9d\n")

    def fake_run_command(directory, command, shell_escape=False, **kwargs):
        return fake_command_result(command)

    monkeypatch.setattr(compiler, "run_command", fake_run_command)
    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["log_files"] == {"main.log": "latex log: \ufffd\n"}


def test_valid_pdf_and_log_return_success(tmp_path, monkeypatch):
    (tmp_path / "main.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "main.log").write_text("LaTeX log")
    monkeypatch.setattr(
        compiler,
        "run_command",
        lambda directory, command, **kwargs: fake_command_result(command),
    )

    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["status"] == "ok"
    assert result["error"] is None
    assert result["pdf"] == b"%PDF-1.7"
    assert result["log_files"] == {"main.log": "LaTeX log"}


def test_missing_pdf_remains_an_ordinary_compilation_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        compiler,
        "run_command",
        lambda directory, command, **kwargs: fake_command_result(command),
    )

    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["status"] == "ko"
    assert result["error"] is None
    assert result["pdf"] is None


def test_oversized_pdf_returns_a_generated_file_error(tmp_path, monkeypatch):
    (tmp_path / "main.pdf").write_bytes(b"0123456789")
    monkeypatch.setattr(compiler, "MAX_PDF_SIZE", 9)
    monkeypatch.setattr(
        compiler,
        "run_command",
        lambda directory, command, **kwargs: fake_command_result(command),
    )

    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["status"] == "error"
    assert result["error"] == {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "too_large",
            "path": "main.pdf",
        },
    }


def test_symlinked_log_returns_a_generated_file_error(tmp_path, monkeypatch):
    (tmp_path / "main.pdf").write_bytes(b"%PDF-1.7")
    (tmp_path / "original.log").write_text("original log")
    (tmp_path / "main.log").symlink_to(tmp_path / "original.log")
    monkeypatch.setattr(
        compiler,
        "run_command",
        lambda directory, command, **kwargs: fake_command_result(command),
    )

    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["status"] == "error"
    assert result["error"] == {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "symlink",
            "path": "main.log",
        },
    }


def test_latex_to_pdf_disables_shell_escape_by_default(tmp_path, monkeypatch):
    calls = []

    def fake_run_command(directory, command, shell_escape=False, **kwargs):
        calls.append(shell_escape)
        return fake_command_result(command)

    monkeypatch.setattr(compiler, "run_command", fake_run_command)
    compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert calls == [False]
    assert "-no-shell-escape" in (tmp_path / ".latexmkrc").read_text()


def test_latex_to_pdf_opts_into_shell_escape(tmp_path, monkeypatch):
    calls = []

    def fake_run_command(directory, command, shell_escape=False, **kwargs):
        calls.append(shell_escape)
        return fake_command_result(command)

    monkeypatch.setattr(compiler, "run_command", fake_run_command)
    compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
        {"compiler": {"shell_escape": True}},
    )

    assert calls == [True]
    assert "-shell-escape" in (tmp_path / ".latexmkrc").read_text()


@pytest.mark.parametrize("compiler_name", ["platex", "uplatex"])
def test_japanese_compilers_use_dvipdfmx(tmp_path, monkeypatch, compiler_name):
    commands = []

    def fake_run_command(directory, command, **kwargs):
        commands.append(command)
        return fake_command_result(command)

    monkeypatch.setattr(compiler, "run_command", fake_run_command)
    compiler.latexToPdf(
        compiler_name,
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert commands[0][1] == "-pdfdvi"
    latexmkrc = (tmp_path / ".latexmkrc").read_text()
    assert "$dvipdf = 'dvipdfmx %O -o %D %S';" in latexmkrc
    assert f"$latex = '{compiler_name} " in latexmkrc


def test_bubblewrap_startup_failure_is_not_a_latex_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        compiler,
        "build_sandbox_command",
        lambda *_args, **_kwargs: [
            sys.executable,
            "-c",
            (
                "import sys; sys.stderr.write('bwrap: No permissions to create namespace'); "
                "raise SystemExit(1)"
            ),
        ],
    )

    with pytest.raises(SandboxUnavailable, match="No permissions"):
        compiler.run_command(tmp_path, ["latexmk", "main.tex"])


def test_missing_bubblewrap_executable_raises_sandbox_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        compiler,
        "build_sandbox_command",
        lambda *_args, **_kwargs: ["/missing/bwrap", "latexmk"],
    )

    with pytest.raises(SandboxUnavailable, match="Cannot start Bubblewrap"):
        compiler.run_command(tmp_path, ["latexmk", "main.tex"])


def test_timeout_kills_descendant_processes(tmp_path):
    result = compiler.run_command(
        tmp_path,
        [
            sys.executable,
            "-c",
            (
                "import subprocess, sys, time; "
                "subprocess.Popen([sys.executable, '-c', "
                "'import pathlib,time; time.sleep(0.8); "
                'pathlib.Path("child-survived").write_text("yes")\']); '
                "time.sleep(30)"
            ),
        ],
        timeout=0.3,
        isolate=False,
    )

    assert result["is_timeout"] is True
    time.sleep(1)
    assert not (tmp_path / "child-survived").exists()
