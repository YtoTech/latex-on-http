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
    # latexmk's #!/usr/bin/env perl shebang needs env and perl. Latexmk also
    # invokes /bin/sh to launch engine commands even with -no-shell-escape.
    # These fixed tools do not expose shell-escape helpers or arbitrary binaries.
    "env",
    "perl",
    "sh",
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
    # Ghostscript wrapper chain: ps2pdf -> ps2pdf14 -> ps2pdfwr -> gs.
    # Its shell launchers also locate companions with dirname and derive
    # default output filenames with basename. Mount only those dependencies.
    "basename",
    "dirname",
    "ps2pdf",
    "ps2pdf12",
    "ps2pdf13",
    "ps2pdf14",
    "ps2pdfwr",
    "gs",
    "epstopdf",
    "repstopdf",
    "extractbb",
    "mpost",
    "xdvipdfmx",
)
SHELL_ESCAPE_COMMANDS = ("python3", "pygmentize")
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


def _executable_bindings(shell_escape):
    """Return public names and their targets without relocating TeX engines."""
    bindings = []
    for command in _configured_commands(shell_escape):
        public_path = _public_executable(command)
        if public_path:
            bindings.append((public_path, os.path.realpath(public_path)))
    return bindings


def _private_bin_directories(bindings):
    directories = set(PRIVATE_BIN_DIRECTORIES)
    for _public_path, real_path in bindings:
        real_directory = os.path.dirname(real_path)
        parent_name = os.path.basename(real_directory)
        grandparent_name = os.path.basename(os.path.dirname(real_directory))
        # TeX Live uses bin/<architecture>. Script resources elsewhere must
        # remain readable, but directories of real executables are restricted.
        if parent_name in ("bin", "sbin") or grandparent_name in ("bin", "sbin"):
            directories.add(real_directory)
    return sorted(directories)


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

    # Hide public executable directories and the real TeX Live bin directories.
    # Restore curated binaries at their real paths so SELFAUTO/Kpathsea can
    # still locate texmf.cnf, then recreate their public symlink aliases.
    executable_bindings = _executable_bindings(shell_escape)
    for bin_directory in _private_bin_directories(executable_bindings):
        if os.path.isdir(bin_directory):
            arguments.extend(["--tmpfs", bin_directory])
    bound_real_paths = set()
    for public_path, real_path in executable_bindings:
        if real_path not in bound_real_paths:
            arguments.extend(["--ro-bind", real_path, real_path])
            bound_real_paths.add(real_path)
        if public_path != real_path:
            arguments.extend(["--symlink", real_path, public_path])

    # TeX and its supported helpers do not need procfs. Avoid mounting a new
    # instance: container runtimes mask the outer /proc, which can make procfs
    # mounts fail inside nested PID namespaces (including rootless Docker and
    # Podman). The private PID namespace itself is still used for containment.
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
