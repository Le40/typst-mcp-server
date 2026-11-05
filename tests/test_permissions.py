import pytest
import tools


@pytest.fixture
def project(tmp_path, monkeypatch):
    read_dir = tmp_path / "source"
    create_dir = tmp_path / "generated"

    read_dir.mkdir()
    create_dir.mkdir()

    (read_dir / "example.typ").write_text(
        "= Example document", encoding="utf-8"
    )

    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tools, "READ_PATHS", ["source/"])
    monkeypatch.setattr(tools, "CREATE_PATHS", ["generated/"])

    return tmp_path


def test_allowed_read(project):
    result = tools.read_file("source/example.typ")
    assert result == "= Example document"


def test_forbidden_read(project):
    with pytest.raises(ValueError, match="Access denied"):
        tools.read_file("../secrets.txt")


def test_allowed_creation(project):
    result = tools.create_file("generated/new.typ", "= New document")

    assert result["success"] is True
    assert (project / "generated" / "new.typ").is_file()


def test_prevent_overwrite(project):
    tools.create_file("generated/new.typ", "= Original")

    result = tools.create_file("generated/new.typ", "= Replacement")

    assert result["success"] is False
    assert (project / "generated" / "new.typ").read_text() == "= Original"


def test_forbidden_creation(project):
    result = tools.create_file("source/unauthorized.typ", "= Test")

    assert result["success"] is False
    assert not (project / "source" / "unauthorized.typ").exists()

def test_symlink_escape(project, tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()

    (outside / "secret.typ").write_text("SECRET")

    link = project / "source" / "external"

    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not available on this system")

    with pytest.raises(ValueError, match="Access denied"):
        tools.read_project_file("source/external/secret.typ")