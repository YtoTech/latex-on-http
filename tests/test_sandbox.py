import os
from pathlib import Path
import shutil

import pytest

from latexonhttp import compiler, sandbox


BWRAP_AVAILABLE = shutil.which("bwrap") is not None
if os.getenv("LATEX_REQUIRE_SANDBOX_TESTS") == "1" and not BWRAP_AVAILABLE:
    raise RuntimeError("Sandbox tests are required, but Bubblewrap is not installed")


def test_missing_bubblewrap_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("LATEX_BWRAP_PATH", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _command: None)

    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.build_sandbox_command(tmp_path, ["latexmk", "main.tex"])


def test_rootless_override_is_limited_to_latex_container():
    override = (Path(__file__).parents[1] / "docker-compose.rootless.yml").read_text()

    assert override.count("- SYS_ADMIN") == 1
    assert "privileged: true" not in override
    assert "seccomp=unconfined" not in override
    assert "cap_add" in override


def test_sandbox_mounts_only_current_workspace_and_allowlisted_binaries(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LATEX_BWRAP_PATH", "/usr/bin/bwrap")
    monkeypatch.setattr(
        sandbox, "_public_executable", lambda command: f"/usr/bin/{command}"
    )

    command = sandbox.build_sandbox_command(tmp_path, ["latexmk", "main.tex"])
    separator = command.index("--")

    assert command[separator + 1 :] == ["/usr/bin/latexmk", "main.tex"]
    assert "--clearenv" in command
    assert "--unshare-net" in command
    assert "--unshare-pid" in command
    assert "--proc" not in command
    assert "--cap-drop" in command
    assert ["--bind", str(tmp_path), "/work"] == command[
        command.index("--bind") : command.index("--bind") + 3
    ]
    assert len([value for value in command if value == "--bind"]) == 1
    assert "main.tex" not in command[:separator]
    assert "--no-shell-escape" not in command


def test_shell_helpers_are_only_exposed_for_shell_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("LATEX_BWRAP_PATH", "/usr/bin/bwrap")
    monkeypatch.setattr(
        sandbox, "_public_executable", lambda command: f"/usr/bin/{command}"
    )

    normal = sandbox.build_sandbox_command(tmp_path, ["latexmk"])
    enabled = sandbox.build_sandbox_command(tmp_path, ["latexmk"], shell_escape=True)

    assert "/usr/bin/python3" not in normal
    assert "python" not in normal
    assert "/usr/bin/python3" in enabled
    assert "/usr/bin/pygmentize" in enabled
    assert "/usr/bin/curl" not in enabled


@pytest.mark.skipif(not BWRAP_AVAILABLE, reason="Bubblewrap is not installed")
def test_real_sandbox_hides_host_files_network_and_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SANDBOX_TEST_SECRET", "must-not-leak")
    result = compiler.run_command(
        tmp_path,
        [
            "python3",
            "-c",
            "import os, pathlib, socket; "
            "pathlib.Path('job-output').write_text('ok'); "
            "print('ENV_SECRET=' + os.getenv('SANDBOX_TEST_SECRET', '')); "
            "print('PROCFS_VISIBLE=' + str(pathlib.Path('/proc').exists())); "
            "\nfor filename in ['/etc/hostname', '/app/latex-on-http/pyproject.toml']:\n"
            "    try:\n"
            "        pathlib.Path(filename).read_text()\n"
            "        print('HOST_FILE_READ=YES')\n"
            "    except OSError:\n"
            "        print('HOST_FILE_READ=NO')\n"
            "try:\n"
            "    socket.create_connection(('127.0.0.1', 1), timeout=0.1)\n"
            "    print('NETWORK=YES')\n"
            "except OSError:\n"
            "    print('NETWORK=NO')",
        ],
        shell_escape=True,
    )

    assert result["return_code"] == 0, result["stdout"]
    assert result["stdout"].count("HOST_FILE_READ=NO") == 2
    assert "PROCFS_VISIBLE=False" in result["stdout"]
    assert "NETWORK=NO" in result["stdout"]
    assert "ENV_SECRET=\n" in result["stdout"]
    assert "must-not-leak" not in result["stdout"]
    assert (tmp_path / "job-output").read_text() == "ok"
