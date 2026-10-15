import pytest

from anketa import excel_safe, safe_path


def test_safe_path_accepts_file_in_directory(tmp_path):
    path = tmp_path / "image.jpg"
    path.write_bytes(b"image")

    assert safe_path(tmp_path, "image.jpg") == path


@pytest.mark.parametrize("name", ["../secret.txt", "/etc/passwd"])
def test_safe_path_rejects_escape(tmp_path, name):
    with pytest.raises(ValueError):
        safe_path(tmp_path, name)


def test_safe_path_accepts_nested_file(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "file.txt").write_text("content")

    assert safe_path(tmp_path, "nested/file.txt") == nested / "file.txt"


def test_safe_path_rejects_symlink(tmp_path):
    (tmp_path / "outside.txt").write_text("secret")
    (tmp_path / "link.txt").symlink_to(tmp_path / "outside.txt")

    with pytest.raises(ValueError):
        safe_path(tmp_path, "link.txt")


@pytest.mark.parametrize("value", ["=SUM(A1)", "+1", "-1", "@cmd"])
def test_excel_safe_quotes_formula_like_values(value):
    assert excel_safe(value) == "'" + value


def test_excel_safe_keeps_regular_values():
    assert excel_safe("ordinary text") == "ordinary text"
    assert excel_safe(42) == 42
