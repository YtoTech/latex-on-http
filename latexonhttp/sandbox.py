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
# ConTeXt (luametatex-based) launches its Lua machinery through stub files
# loaded relative to the invoked binary: running `context` looks for
# `context.lua` (or `.lmt`) in the directory of argv[0], and that stub then
# loads `mtxrun.lua` from the same directory. In TeX Live these are symlinks
# from the bin directories into texmf-dist/scripts. As executable directories
# are hidden and rebuilt from the curated list, the stubs must be bound too:
# without them the engine falls back to plain TeX mode and fails with
# "startup error : no format file given, quitting".
LAUNCHER_STUB_SUFFIXES = (".lua", ".lmt")
# Nobody else uses the argv[0]-relative Lua launcher mechanism. Constraining
# this list also prevents script trees from being mistaken for TeX bin dirs:
# a candidate such as scripts/extractbb/extractbb remains on a read-only tree.
LUA_LAUNCHER_COMMANDS = ("context", "contextjit", "mtxrun", "mtxrunjit")
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
            real_path = os.path.realpath(public_path)
            bindings.append((public_path, real_path))
            launcher_path = _compilation_executable(public_path)
            if launcher_path != public_path:
                # Preserve the basename selecting the ConTeXt launcher, but
                # execute it from the real bin directory instead of /usr/local/bin.
                bindings.append((launcher_path, real_path))
    bindings.extend(_companion_stub_bindings(bindings))
    return bindings


def _launcher_stub_paths(base_path):
    """Return the Lua launcher stubs adjacent to one executable alias."""
    return [
        base_path + suffix
        for suffix in LAUNCHER_STUB_SUFFIXES
        if os.path.isfile(base_path + suffix)
    ]


def _compilation_executable(public_path):
    """Locate Lua launchers in their real TeX bin directory, keeping argv[0].

    ConTeXt computes SELFAUTOPARENT from the parent of dirname(argv[0]) without
    resolving its public /usr/local/bin alias. The real luametatex path cannot
    be used either, because the launcher is selected from the context/mtxrun
    basename. Run <real-bin-directory>/context instead, where both context.lua
    and /usr/local/texlive links are present.
    """
    if os.path.basename(public_path) not in LUA_LAUNCHER_COMMANDS:
        return public_path
    real_directory = os.path.dirname(os.path.realpath(public_path))
    launcher_path = os.path.join(real_directory, os.path.basename(public_path))
    if _launcher_stub_paths(launcher_path):
        return launcher_path
    return public_path


def _companion_stub_bindings(bindings):
    """Return launcher stub bindings sitting next to curated executables."""
    stubs = []
    seen = set()
    for public_path, real_path in bindings:
        for base_path in (public_path, real_path):
            if os.path.basename(base_path) not in LUA_LAUNCHER_COMMANDS:
                continue
            for stub_path in _launcher_stub_paths(base_path):
                if stub_path in seen:
                    continue
                seen.add(stub_path)
                stubs.append((stub_path, os.path.realpath(stub_path)))
    return stubs


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
    executable = _compilation_executable(_public_executable(command[0]))

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
            executable,
            *command[1:],
        ]
    )
    return arguments
