# -*- coding: utf-8 -*-
"""Bubblewrap sandbox for untrusted compilation process trees."""

import os
import shlex
import shutil

WORKSPACE_MOUNT = "/work"
SANDBOX_PATH = "/usr/local/bin:/usr/bin:/bin"
DEFAULT_READ_ONLY_PATHS = (
    "/usr",
    "/lib",
    "/lib64",
    "/etc/fonts",
    "/etc/texmf",
    "/var/lib/texmf",
    "/var/cache/fontconfig",
    "/opt/texlive",
)
DEFAULT_ALLOWED_COMMANDS = (
    "latexmk",
    "context",
    "pdflatex",
    "pdftex",
    "xelatex",
    "xetex",
    "lualatex",
    "luatex",
    "latex",
    "platex",
    "ptex",
    "eptex",
    "uplatex",
    "uptex",
    "euptex",
    "kpsewhich",
    "perl",
    "texlua",
    "texluac",
    "mtxrun",
    "mtx-context",
    "luametatex",
    "bibtex",
    "bibtex8",
    "biber",
    "makeindex",
    "upmendex",
    "dvipdfmx",
    "dvips",
    "ps2pdf",
    "gs",
    "epstopdf",
    "repstopdf",
    "extractbb",
    "mpost",
    "xdvipdfmx",
)
SHELL_ESCAPE_COMMANDS = ("sh", "python3", "pygmentize")
PRIVATE_BIN_DIRECTORIES = (
    "/usr/local/bin",
    "/usr/local/sbin",
    "/usr/bin",
    "/usr/sbin",
)


class SandboxUnavailable(RuntimeError):
    """Raised when the configured sandbox cannot safely be used."""


def sandbox_enabled(isolate=None):
    if isolate is not None:
        return isolate
    return os.getenv("LATEX_SANDBOX_BACKEND", "bubblewrap").lower() != "none"


def _configured_commands(shell_escape):
    commands = list(DEFAULT_ALLOWED_COMMANDS)
    if shell_escape:
        commands.extend(SHELL_ESCAPE_COMMANDS)
        commands.extend(shlex.split(os.getenv("LATEX_SHELL_ESCAPE_EXTRA_COMMANDS", "")))
    commands.extend(shlex.split(os.getenv("LATEX_SANDBOX_EXTRA_COMMANDS", "")))
    return tuple(dict.fromkeys(commands))


def _public_executable(command):
    return shutil.which(command, path=SANDBOX_PATH)


def _add_read_only_paths(arguments):
    configured_paths = shlex.split(os.getenv("LATEX_SANDBOX_READ_ONLY_PATHS", ""))
    for path in configured_paths or DEFAULT_READ_ONLY_PATHS:
        if os.path.exists(path):
            arguments.extend(["--ro-bind", path, path])


def prepare_workspace(directory):
    """Create job-local directories used by runtime caches."""
    os.makedirs(os.path.join(directory, ".home"), mode=0o700, exist_ok=True)
    for cache_directory in ("texmf", "texmf-var", "texmf-config"):
        os.makedirs(
            os.path.join(directory, ".texlive", cache_directory),
            mode=0o700,
            exist_ok=True,
        )


def build_sandbox_command(directory, command, shell_escape=False):
    """Prefix a command and all of its descendants with an offline sandbox."""
    if not command or not isinstance(command[0], str):
        raise ValueError("A non-empty command argument list is required")
    bwrap = os.getenv("LATEX_BWRAP_PATH") or shutil.which("bwrap")
    if not bwrap:
        raise SandboxUnavailable(
            "Bubblewrap is required for compilation isolation. Install bubblewrap "
            "or explicitly set LATEX_SANDBOX_BACKEND=none for a trusted environment."
        )
    if not os.path.isdir(directory):
        raise ValueError("The compilation workspace must be an existing directory")
    if not _public_executable(command[0]):
        raise SandboxUnavailable(
            f"Compilation command {command[0]!r} was not found in the sandbox path"
        )

    arguments = [
        bwrap,
        "--unshare-user",
        "--unshare-ipc",
        "--unshare-pid",
        "--unshare-uts",
        "--unshare-net",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--uid",
        "65534",
        "--gid",
        "65534",
        "--clearenv",
        "--setenv",
        "PATH",
        SANDBOX_PATH,
        "--setenv",
        "HOME",
        f"{WORKSPACE_MOUNT}/.home",
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--setenv",
        "LANG",
        "C.UTF-8",
        "--setenv",
        "LC_ALL",
        "C.UTF-8",
        "--setenv",
        "TEXMFVAR",
        f"{WORKSPACE_MOUNT}/.texlive/texmf-var",
        "--setenv",
        "TEXMFCONFIG",
        f"{WORKSPACE_MOUNT}/.texlive/texmf-config",
        "--setenv",
        "TEXMFHOME",
        f"{WORKSPACE_MOUNT}/.texlive/texmf",
    ]
    _add_read_only_paths(arguments)

    # Hide normal executable directories, then restore individual commands.
    # Bind mounts follow symlinks, which preserves the public engine name while
    # exposing its resolved executable.
    for bin_directory in PRIVATE_BIN_DIRECTORIES:
        if os.path.isdir(bin_directory):
            arguments.extend(["--tmpfs", bin_directory])
    for public_command in _configured_commands(shell_escape):
        public_path = _public_executable(public_command)
        if public_path:
            arguments.extend(["--ro-bind", os.path.realpath(public_path), public_path])

    arguments.extend(
        [
            "--symlink",
            "usr/bin",
            "/bin",
            "--symlink",
            "usr/sbin",
            "/sbin",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--tmpfs",
            "/tmp",
            "--bind",
            os.path.abspath(directory),
            WORKSPACE_MOUNT,
            "--chdir",
            WORKSPACE_MOUNT,
            "--",
            _public_executable(command[0]),
            *command[1:],
        ]
    )
    return arguments
