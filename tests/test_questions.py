import asyncio

import pandas as pd

import anketa


def write_questions_file(path, rows):
    pd.DataFrame(rows).to_excel(path, header=False, index=False)


def test_get_new_questions_validates_and_converts_workbook(tmp_path, monkeypatch):
    source = tmp_path / "questions.xlsx"
    write_questions_file(
        source,
        [
            ["header", "Survey title", "logo.jpg"],
            ["simple", "Your name"],
            ["select", "Choose", "First", "Second"],
            ["text", "Additional comment"],
        ],
    )
    monkeypatch.setattr(anketa, "exist_file", lambda name: asyncio.sleep(0, result=name == "logo.jpg"))

    types, questions, warnings = asyncio.run(anketa.get_new_questions(source))

    assert warnings == ""
    assert types["Survey title"] == "header"
    assert questions["Choose"] == ["First", "Second"]
    assert types["ID4T_1_Additional comment"] == "text"


def test_get_new_questions_rejects_unknown_question_type(tmp_path):
    source = tmp_path / "questions.xlsx"
    write_questions_file(source, [["unknown", "Question"]])

    assert asyncio.run(anketa.get_new_questions(source)) == (False, False, False)


def test_get_new_questions_rejects_oversized_file(tmp_path, monkeypatch):
    source = tmp_path / "questions.xlsx"
    source.write_bytes(b"not a valid workbook")
    monkeypatch.setattr(anketa.sts, "MAX_UPLOAD_BYTES", 1)

    assert asyncio.run(anketa.get_new_questions(source)) == (False, False, False)


def test_get_new_questions_warns_for_missing_image(tmp_path, monkeypatch):
    source = tmp_path / "questions.xlsx"
    write_questions_file(source, [["header", "Title", "missing.jpg"]])
    monkeypatch.setattr(anketa, "exist_file", lambda name: asyncio.sleep(0, result=False))

    types, questions, warnings = asyncio.run(anketa.get_new_questions(source))

    assert types == {"Title": "header"}
    assert questions == {"Title": [""]}
    assert "missing.jpg" in warnings


def test_get_new_questions_rejects_too_many_columns(tmp_path, monkeypatch):
    source = tmp_path / "questions.xlsx"
    monkeypatch.setattr(anketa.sts, "MAX_EXCEL_COLUMNS", 2)
    write_questions_file(source, [["simple", "Question", "unexpected", "extra"]])

    assert asyncio.run(anketa.get_new_questions(source)) == (False, False, False)


def test_get_new_questions_rejects_long_question(tmp_path, monkeypatch):
    source = tmp_path / "questions.xlsx"
    monkeypatch.setattr(anketa.sts, "MAX_EXCEL_COLUMNS", 4)
    write_questions_file(source, [["simple", "x" * 4097]])

    assert asyncio.run(anketa.get_new_questions(source)) == (False, False, False)


def test_get_new_questions_rejects_invalid_workbook(tmp_path):
    source = tmp_path / "questions.xlsx"
    source.write_bytes(b"not an xlsx file")

    assert asyncio.run(anketa.get_new_questions(source)) == (False, False, False)
