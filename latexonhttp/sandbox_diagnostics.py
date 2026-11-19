"""Recognize and report sandbox infrastructure failures without hiding them."""

import logging
import os
import re
import shlex
from dataclasses import dataclass

import sentry_sdk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SandboxDiagnostic:
    kind: str
    binary: str
    detail: str


_EXECUTABLE_PATTERNS = (
    re.compile(r"Can't exec \"(?P<binary>[A-Za-z0-9_./+-]+)\":"),
    re.compile(r"(?:^|:\s)(?:exec:\s*)?(?P<binary>[A-Za-z0-9_./+-]+):"),
    re.compile(r"^bwrap: execvp (?P<binary>[A-Za-z0-9_./+-]+):"),
)
_PERMISSION_REASONS = (
    "permission denied",
    "operation not permitted",
    "no permissions to create",
)


def _process_failure_from_line(line):
    """Extract the failing executable, not the wrapper mentioned earlier."""
    for pattern in _EXECUTABLE_PATTERNS:
        for match in pattern.finditer(line):
            suffix = line[match.end() :].lstrip().lower()
            if suffix.startswith("no such file or directory") or re.match(
                r"(?:command\s+)?not found\b", suffix
            ):
                kind = "missing_binary"
            elif suffix.startswith("permission denied"):
                kind = "permission_denied"
            else:
                continue
            return os.path.basename(match.group("binary")), kind
    return None, None


def find_sandbox_process_issue(output, allowed_commands):
    """Find a trusted launcher diagnostic in an otherwise untrusted TeX log.

    Only failures naming a curated executable are reported. TeX errors such as
    a missing input file, or an arbitrary shell-escape command, are not system
    dependency failures and must not produce operational alerts.
    """
    if not output:
        return None
    allowed_commands = set(allowed_commands)
    for line in output.splitlines():
        if line.lstrip().startswith("bwrap:"):
            if any(reason in line.lower() for reason in _PERMISSION_REASONS):
                return SandboxDiagnostic("permission_denied", "bubblewrap", line[:1000])
            if "no such file or directory" in line.lower():
                match = _EXECUTABLE_PATTERNS[-1].search(line)
                binary = (
                    os.path.basename(match.group("binary")) if match else "bubblewrap"
                )
                return SandboxDiagnostic("missing_binary", binary, line[:1000])
        binary, kind = _process_failure_from_line(line)
        if kind and binary in allowed_commands:
            return SandboxDiagnostic(kind, binary, line[:1000])
    return None


def sandbox_unavailable_issue(error):
    """Classify the already-trusted error emitted while starting Bubblewrap."""
    detail = str(error)[:1000]
    lower_detail = detail.lower()
    if any(reason in lower_detail for reason in _PERMISSION_REASONS):
        return SandboxDiagnostic("permission_denied", "bubblewrap", detail)
    if (
        "no such file or directory" in lower_detail
        or "cannot start bubblewrap" in lower_detail
    ):
        binary, _kind = _process_failure_from_line(detail)
        return SandboxDiagnostic("missing_binary", binary or "bubblewrap", detail)
    return SandboxDiagnostic("unavailable", "bubblewrap", detail)


def report_sandbox_diagnostic(
    diagnostic, command=(), directory="", shell_escape=False, compiler=None
):
    """Report one operational issue, without letting telemetry alter a build."""
    if not os.getenv("SENTRY_DSN"):
        return False
    try:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("sandbox.issue", diagnostic.kind)
            scope.set_tag("sandbox.binary", diagnostic.binary)
            scope.set_fingerprint(
                ["latex-on-http", "sandbox", diagnostic.kind, diagnostic.binary]
            )
            scope.set_context(
                "sandbox",
                {
                    "backend": "bubblewrap",
                    "detail": diagnostic.detail,
                    "shell_escape": bool(shell_escape),
                },
            )
            scope.set_context(
                "compilation",
                {
                    "command": shlex.join(command),
                    "compiler": compiler or (command[0] if command else None),
                    "workspace_id": (
                        os.path.basename(os.path.abspath(directory))
                        if directory
                        else None
                    ),
                },
            )
            scope.capture_message(
                f"Sandbox {diagnostic.kind.replace('_', ' ')}: {diagnostic.binary}",
                level="error",
            )
        return True
    except Exception:
        logger.exception("Unable to report sandbox diagnostic to Sentry")
        return False
