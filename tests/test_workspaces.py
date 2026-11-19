from pathlib import Path

from latexonhttp.workspaces import filesystem


def test_path_check_rejects_sibling_with_common_string_prefix(tmp_path):
    workspace = tmp_path / "job"
    workspace.mkdir()
    sibling = tmp_path / "job-other" / "resource.tex"

    assert not filesystem.is_safe_path(workspace, sibling)


def test_path_check_resolves_symlinks(tmp_path):
    workspace = tmp_path / "job"
    workspace.mkdir()
    outside = tmp_path / "outside.tex"
    outside.write_text("secret")
    candidate = workspace / "main.tex"
    candidate.symlink_to(outside)

    assert not filesystem.is_safe_path(workspace, candidate)
    assert filesystem.is_safe_path(workspace, candidate, follow_symlinks=False)


def test_persist_resource_rejects_symlinked_parent(tmp_path, monkeypatch):
    monkeypatch.setattr(filesystem, "WORKSPACE_DIRECTORY", str(tmp_path))
    filesystem.make_workspace("job")
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = Path(filesystem.get_workspace_root_path("job"))
    (workspace / "uploads").symlink_to(outside, target_is_directory=True)

    result = filesystem.persist_resource_to_workspace(
        "job",
        {"build_path": "uploads/main.tex", "data_spec": {"size": 1}},
        b"x",
    )

    assert result == "INVALID_PATH"
    assert not (outside / "main.tex").exists()


def test_persist_resource_accepts_nested_job_path(tmp_path, monkeypatch):
    monkeypatch.setattr(filesystem, "WORKSPACE_DIRECTORY", str(tmp_path))
    filesystem.make_workspace("job")

    result = filesystem.persist_resource_to_workspace(
        "job",
        {"build_path": "chapters/main.tex", "data_spec": {"size": 1}},
        b"x",
    )

    assert result is None
    workspace = Path(filesystem.get_workspace_root_path("job"))
    assert (workspace / "chapters" / "main.tex").read_bytes() == b"x"


def test_read_generated_file_returns_regular_file_bytes(tmp_path):
    output = tmp_path / "main.pdf"
    output.write_bytes(b"%PDF-1.7")

    data, error = filesystem.read_generated_file(tmp_path, output, 100)

    assert data == b"%PDF-1.7"
    assert error is None


def test_generated_file_outside_workspace_is_not_read(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"not a workspace output")

    data, error = filesystem.read_generated_file(workspace, outside, 100)

    assert data is None
    assert error == {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "outside_workspace",
            "path": "../outside.pdf",
        },
    }


def test_generated_pdf_symlink_is_not_followed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    original = workspace / "original.pdf"
    original.write_bytes(b"original output")
    (workspace / "main.pdf").symlink_to(original)

    data, error = filesystem.read_generated_file(workspace, workspace / "main.pdf", 100)

    assert data is None
    assert error == {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "symlink",
            "path": "main.pdf",
        },
    }


def test_generated_file_size_is_bounded(tmp_path):
    output = tmp_path / "main.pdf"
    output.write_bytes(b"0123456789")

    data, error = filesystem.read_generated_file(tmp_path, output, 9)

    assert data is None
    assert error == {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "too_large",
            "path": "main.pdf",
        },
    }


def test_missing_generated_file_returns_not_found_error(tmp_path):
    data, error = filesystem.read_generated_file(
        tmp_path, tmp_path / "missing.pdf", 100
    )

    assert data is None
    assert error["file_read_error"]["reason"] == "not_found"


def test_generated_directory_returns_not_regular_error(tmp_path):
    data, error = filesystem.read_generated_file(tmp_path, tmp_path, 100)

    assert data is None
    assert error["file_read_error"]["reason"] == "not_regular"


def test_generated_file_os_error_returns_read_error(tmp_path, monkeypatch):
    output = tmp_path / "main.pdf"
    output.write_bytes(b"%PDF-1.7")

    def fail_open(*args):
        raise PermissionError("read denied")

    monkeypatch.setattr(filesystem.os, "open", fail_open)

    data, error = filesystem.read_generated_file(tmp_path, output, 100)

    assert data is None
    assert error == {
        "error": "GENERATED_FILE_READ_ERROR",
        "file_read_error": {
            "reason": "read_error",
            "path": "main.pdf",
        },
    }
