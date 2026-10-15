from datetime import datetime

import pandas as pd
import pytest

import anketa


class FakeDatabase:
    def __init__(self, _db_file):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def get_info_for_report(self):
        return [
            {
                "name_user": "Alice",
                "nick_user": "alice",
                "question_id": "1",
                "answer_user": "Good answer",
                "date": "2026-10-15T18:30:00",
            }
        ]


def test_dataframe_sheet1_supports_iso_dates(monkeypatch):
    monkeypatch.setattr(anketa, "all_questions", {"Question": []})

    import asyncio

    result = asyncio.run(
        anketa.set_dataframe_sheet1(
            [
                {
                    "name_user": "Alice",
                    "nick_user": "alice",
                    "question_id": "1",
                    "answer_user": "Good answer",
                    "date": "2026-10-15T18:30:00",
                }
            ]
        )
    )

    assert result["date"] == ["15.10.2026"]
    assert result["time"] == ["18:30"]


def test_dataframe_sheet2_maps_select_variants(monkeypatch):
    monkeypatch.setattr(anketa, "all_questions", {"Choice": ["Yes", "No"]})

    import asyncio

    result = asyncio.run(
        anketa.set_dataframe_sheet2(
            [
                {
                    "name_user": "Alice",
                    "nick_user": "alice",
                    "question_id": "1",
                    "answer_user": "1, 2",
                    "date": "2026-10-15T18:30:00",
                }
            ]
        )
    )

    assert result["Choice"][:2] == ["Yes", "No"]


@pytest.mark.asyncio
async def test_gen_pdf_creates_report(tmp_path, monkeypatch):
    monkeypatch.setattr(anketa, "all_questions", {"Question": []})
    monkeypatch.setattr(anketa, "type_questions", {"Question": "simple"})
    monkeypatch.setattr(anketa.sts, "report_logo", "logo.jpg")
    monkeypatch.setattr(anketa.sts, "report_title", "Survey")

    report = tmp_path / "report.pdf"
    await anketa.gen_pdf({1: ["A useful answer"]}, str(report))

    assert report.is_file()
    assert report.stat().st_size > 0


@pytest.mark.asyncio
async def test_gen_excel_creates_report_with_iso_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(anketa.dbm, "DatabaseBot", FakeDatabase)
    monkeypatch.setattr(anketa, "all_questions", {"Question": []})
    monkeypatch.setattr(anketa, "type_questions", {"Question": "simple"})

    report = tmp_path / "report.xlsx"
    assert await anketa.gen_excel(str(report)) is True

    sheets = pd.read_excel(report, sheet_name=None, header=None)
    assert "По вопросам" in sheets
    assert "По пользователям" in sheets
    assert "Good answer" in sheets["По вопросам"].to_string()
