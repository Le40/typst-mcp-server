
from pathlib import Path

import pytest

import tools


@pytest.fixture
def project(tmp_path, monkeypatch):
    source = tmp_path / "source"
    generated = tmp_path / "generated"
    inbox = tmp_path / "inbox"

    source.mkdir()
    generated.mkdir()
    inbox.mkdir()

    (source / "example.typ").write_text(
        "= Example document", encoding="utf-8"
    )
    (source / "notes.md").write_text(
        "# Notes", encoding="utf-8"
    )
    (source / "script.py").write_text(
        "print('test')", encoding="utf-8"
    )
    (inbox / "job.md").write_text(
        "# Job description", encoding="utf-8"
    )

    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)

    monkeypatch.setattr(tools, "READ_RULES", {
        "source/": [".typ", ".md"],
        "inbox/": [".md"],
    })

    monkeypatch.setattr(tools, "CREATE_RULES", {
        "generated/": [".typ"],
        "inbox/": [".md"],
    })

    return tmp_path


# READ PERMISSIONS

def test_allowed_read(project):
    path = tools.get_permitted_file(
        "source/example.typ", tools.READ_RULES
    )
    assert path.read_text(encoding="utf-8") == "= Example document"


def test_allowed_markdown_read(project):
    path = tools.get_permitted_file(
        "inbox/job.md", tools.READ_RULES
    )
    assert path.is_file()


def test_forbidden_extension_read(project):
    with pytest.raises(ValueError):
        tools.get_permitted_file(
            "source/script.py", tools.READ_RULES
        )


def test_forbidden_path_read(project):
    with pytest.raises(ValueError):
        tools.get_permitted_file(
            "../secret.typ", tools.READ_RULES
        )


# CREATE PERMISSIONS

def test_allowed_create(project):
    result = tools.create_file("generated/new.typ", "= New")
    assert result["success"] is True
    assert (project / "generated/new.typ").exists()


def test_allowed_markdown_create(project):
    result = tools.create_file("inbox/new-job.md", "# New job")
    assert result["success"] is True
    assert (project / "inbox/new-job.md").exists()


def test_forbidden_extension_create(project):
    result = tools.create_file("generated/test.md", "# Not allowed")
    assert result["success"] is False
    assert not (project / "generated/test.md").exists()


def test_forbidden_path_create(project):
    result = tools.create_file("source/new.typ", "= Not allowed")
    assert result["success"] is False
    assert not (project / "source/new.typ").exists()


def test_prevent_overwrite(project):
    file = project / "generated/existing.typ"
    file.write_text("Original", encoding="utf-8")

    result = tools.create_file("generated/existing.typ", "Changed")

    assert result["success"] is False
    assert file.read_text(encoding="utf-8") == "Original"


# FILE LISTING

def test_list_only_permitted_files(project):
    result = tools.list_project_files()
    files = result["files"] if isinstance(result, dict) else result

    assert "source/example.typ" in files
    assert "source/notes.md" in files
    assert "inbox/job.md" in files

    assert "source/script.py" not in files


# SYMLINK SECURITY

def test_symlink_escape(project):
    outside = project.parent / f"{project.name}-outside.typ"
    outside.write_text("Secret", encoding="utf-8")

    link = project / "source/linked.typ"

    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks unavailable on this system")

    with pytest.raises(ValueError):
        tools.get_permitted_file(
            "source/linked.typ", tools.READ_RULES
        )
