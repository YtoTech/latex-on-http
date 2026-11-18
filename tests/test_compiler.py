# -*- coding: utf-8 -*-
"""
tests.test_compiler
~~~~~~~~~~~~~~~~~~~
Check compiler process output and log decoding.

:copyright: (c) 2017-2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import sys

from latexonhttp import compiler


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
    )

    assert result["return_code"] == 12
    assert "latex output: \ufffd\n" in result["stdout"]


def test_latex_to_pdf_replaces_invalid_utf8_in_log_files(tmp_path, monkeypatch):
    (tmp_path / "main.log").write_bytes(b"latex log: \x9d\n")

    def fake_run_command(directory, command):
        return {
            "command": command,
            "return_code": 12,
            "stdout": "",
            "duration": 0,
            "is_timeout": False,
        }

    monkeypatch.setattr(compiler, "run_command", fake_run_command)

    result = compiler.latexToPdf(
        "pdflatex",
        str(tmp_path),
        {"build_path": "main.tex", "output_path": "main.pdf"},
        "test-workspace",
    )

    assert result["log_files"] == {"main.log": "latex log: \ufffd\n"}
