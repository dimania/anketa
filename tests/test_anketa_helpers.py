import pytest

import pandas as pd

import anketa
from anketa import delete_files, excel_safe, exist_file, get_excel_data, list_files4selection, safe_path


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


@pytest.mark.asyncio
async def test_list_files_ignores_symlinks_and_excluded_files(tmp_path):
    (tmp_path / "keep.jpg").write_bytes(b"image")
    (tmp_path / "skip.jpg").write_bytes(b"image")
    (tmp_path / "outside.jpg").write_bytes(b"outside")
    (tmp_path / "link.jpg").symlink_to(tmp_path / "outside.jpg")

    files = await list_files4selection(tmp_path, exclude=["skip.jpg"])

    assert set(files) == {"keep.jpg", "outside.jpg"}
    assert "link.jpg" not in files


@pytest.mark.asyncio
async def test_delete_files_removes_managed_files_only(tmp_path):
    managed = tmp_path / "managed.txt"
    outside = tmp_path / "outside.txt"
    managed.write_text("managed")
    outside.write_text("outside")

    assert await delete_files(tmp_path, ["managed.txt"]) is True
    assert not managed.exists()

    assert await delete_files(tmp_path, ["../outside.txt"]) is False
    assert outside.exists()


@pytest.mark.asyncio
async def test_exist_file_accepts_only_files_from_image_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(anketa, "IMAGE_DIR", tmp_path)
    (tmp_path / "logo.jpg").write_bytes(b"image")

    assert await exist_file("logo.jpg") == str(tmp_path / "logo.jpg")
    assert await exist_file("../logo.jpg") is False
    assert await exist_file("") is False


@pytest.mark.asyncio
async def test_get_excel_data_reads_rows(tmp_path):
    source = tmp_path / "questions.xlsx"
    pd.DataFrame([["Question", "Answer"], ["What?", "Yes"]]).to_excel(
        source, header=False, index=False
    )

    result = await get_excel_data(str(source))

    assert result["data"] == [["Question", "Answer"], ["What?", "Yes"]]


@pytest.mark.asyncio
async def test_get_excel_data_returns_false_for_missing_file(tmp_path):
    assert await get_excel_data(str(tmp_path / "missing.xlsx")) is False
