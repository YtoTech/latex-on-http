"""Tests for operational diagnostics from sandboxed process failures."""

from unittest.mock import MagicMock

import pytest

from latexonhttp import compiler
from latexonhttp.sandbox import DEFAULT_ALLOWED_COMMANDS
from latexonhttp.sandbox_diagnostics import (
    SandboxDiagnostic,
    find_sandbox_process_issue,
    report_sandbox_diagnostic,
    sandbox_unavailable_issue,
)


@pytest.mark.parametrize(
    ("line", "kind", "binary"),
    [
        ("/usr/bin/ps2pdf: 1: dirname: not found", "missing_binary", "dirname"),
        (
            "/usr/bin/ps2pdf: 12: exec: ps2pdf14: not found",
            "missing_binary",
            "ps2pdf14",
        ),
        (
            'Can\'t exec "/bin/sh": No such file or directory at latexmk line 14071.',
            "missing_binary",
            "sh",
        ),
        ("/usr/bin/ps2pdfwr: 9: gs: Permission denied", "permission_denied", "gs"),
        (
            "bwrap: No permissions to create a new namespace",
            "permission_denied",
            "bubblewrap",
        ),
    ],
)
def test_recognizes_sandbox_process_failures(line, kind, binary):
    diagnostic = find_sandbox_process_issue(line, DEFAULT_ALLOWED_COMMANDS)

    assert diagnostic == SandboxDiagnostic(kind, binary, line)


@pytest.mark.parametrize(
    "output",
    [
        "! LaTeX Error: File `missing-package.sty' not found.",
        "! I can't find file `missing-document.tex'.",
        "minted: Using Python 3.13.1",
        "This is pdfTeX, Version 3.141592653",
    ],
)
def test_ignores_ordinary_tex_errors(output):
    assert find_sandbox_process_issue(output, DEFAULT_ALLOWED_COMMANDS) is None


def test_ignores_unconfigured_shell_command_not_found():
    assert (
        find_sandbox_process_issue("sh: 1: curl: not found", DEFAULT_ALLOWED_COMMANDS)
        is None
    )


def test_reports_scoped_metadata_and_preserves_parent_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    new_scope = MagicMock()
    scope = new_scope.return_value.__enter__.return_value
    monkeypatch.setattr(
        "latexonhttp.sandbox_diagnostics.sentry_sdk.new_scope", new_scope
    )

    result = report_sandbox_diagnostic(
        SandboxDiagnostic("missing_binary", "ps2pdf14", "ps2pdf14: not found"),
        command=["latexmk", "-pdfps", "main.tex"],
        directory=str(tmp_path / "build-id"),
        compiler="uplatex",
    )

    assert result is True
    scope.clear.assert_not_called()
    scope.add_event_processor.assert_not_called()
    scope.set_tag.assert_any_call("sandbox.issue", "missing_binary")
    scope.set_tag.assert_any_call("sandbox.binary", "ps2pdf14")
    scope.set_fingerprint.assert_called_once_with(
        ["latex-on-http", "sandbox", "missing_binary", "ps2pdf14"]
    )
    context = dict(call.args for call in scope.set_context.call_args_list)
    assert context["sandbox"] == {
        "backend": "bubblewrap",
        "detail": "ps2pdf14: not found",
        "shell_escape": False,
    }
    assert context["compilation"] == {
        "command": "latexmk -pdfps main.tex",
        "compiler": "uplatex",
        "workspace_id": "build-id",
    }
    scope.capture_message.assert_called_once_with(
        "Sandbox missing binary: ps2pdf14", level="error"
    )


def test_does_not_report_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    new_scope = MagicMock()
    monkeypatch.setattr(
        "latexonhttp.sandbox_diagnostics.sentry_sdk.new_scope", new_scope
    )

    assert (
        report_sandbox_diagnostic(SandboxDiagnostic("unavailable", "bubblewrap", ""))
        is False
    )
    new_scope.assert_not_called()


def test_reporting_failure_does_not_escape(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "configured")
    monkeypatch.setattr(
        "latexonhttp.sandbox_diagnostics.sentry_sdk.new_scope",
        MagicMock(side_effect=RuntimeError("Sentry transport failure")),
    )

    assert (
        report_sandbox_diagnostic(
            SandboxDiagnostic("unavailable", "bubblewrap", "error")
        )
        is False
    )


def test_startup_permission_failure_is_classified():
    assert sandbox_unavailable_issue(
        "bwrap: pivot_root: Operation not permitted"
    ) == SandboxDiagnostic(
        "permission_denied", "bubblewrap", "bwrap: pivot_root: Operation not permitted"
    )


def test_failed_sandbox_command_preserves_result_and_reports(tmp_path, monkeypatch):
    output = "/usr/bin/ps2pdf: 1: dirname: not found\n"
    reported = []

    class FakeProcess:
        pid = 123

        def communicate(self, timeout=None):
            return output, None

        def wait(self):
            return 127

    monkeypatch.setattr(
        compiler.subprocess, "Popen", lambda *args, **kwargs: FakeProcess()
    )
    monkeypatch.setattr(
        compiler, "build_sandbox_command", lambda *args, **kwargs: ["latexmk"]
    )
    monkeypatch.setattr(
        compiler,
        "report_sandbox_diagnostic",
        lambda diagnostic, **context: reported.append((diagnostic, context)),
    )

    result = compiler.run_command(
        tmp_path, ["latexmk"], isolate=True, compiler_name="uplatex"
    )

    assert result["return_code"] == 127
    assert result["stdout"] == output
    assert reported[0][0].binary == "dirname"
    assert reported[0][1]["directory"] == tmp_path
    assert reported[0][1]["compiler"] == "uplatex"
