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
