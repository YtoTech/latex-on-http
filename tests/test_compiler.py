# -*- coding: utf-8 -*-
"""
tests.test_compiler
~~~~~~~~~~~~~~~~~~~
Check compiler process output and log decoding.

:copyright: (c) 2017-2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

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
            "import sys; "
            "sys.stdout.buffer.write(b'latex output: \\x9d\\n'); "
            "raise SystemExit(12)",
        ],
        isolate=False,
    )

    assert result["return_code"] == 12
    assert "latex output: \ufffd\n" in result["stdout"]


def test_latex_to_pdf_replaces_invalid_utf8_in_log_files(tmp_path, monkeypatch):
    (tmp_path / "main.log").write_bytes(b"latex log: \x9d\n")

    def fake_run_command(directory, command, shell_escape=False):
        return fake_command_result(command)

    monkeypatch.setattr(compiler, "run_command", fake_run_command)
    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["log_files"] == {"main.log": "latex log: \ufffd\n"}


def test_latex_to_pdf_disables_shell_escape_by_default(tmp_path, monkeypatch):
    calls = []

    def fake_run_command(directory, command, shell_escape=False):
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

    def fake_run_command(directory, command, shell_escape=False):
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


def test_bubblewrap_startup_failure_is_not_a_latex_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        compiler,
        "build_sandbox_command",
        lambda *_args, **_kwargs: [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('bwrap: No permissions to create namespace'); "
            "raise SystemExit(1)",
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


def test_generated_pdf_symlink_is_not_followed(tmp_path):
    secret = tmp_path / "secret"
    secret.write_bytes(b"host secret")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.pdf").symlink_to(secret)

    assert compiler._read_generated_file(workspace / "main.pdf", 100) is None


def test_generated_file_size_is_bounded(tmp_path):
    output = tmp_path / "main.pdf"
    output.write_bytes(b"0123456789")

    assert compiler._read_generated_file(output, 9) is None


def test_timeout_kills_descendant_processes(tmp_path):
    result = compiler.run_command(
        tmp_path,
        [
            sys.executable,
            "-c",
            "import subprocess, sys, time; "
            "subprocess.Popen([sys.executable, '-c', "
            "'import pathlib,time; time.sleep(0.8); "
            'pathlib.Path("child-survived").write_text("yes")\']); '
            "time.sleep(30)",
        ],
        timeout=0.3,
        isolate=False,
    )

    assert result["is_timeout"] is True
    time.sleep(1)
    assert not (tmp_path / "child-survived").exists()
