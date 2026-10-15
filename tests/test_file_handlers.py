from pathlib import Path
from types import SimpleNamespace

import pytest

import anketa


class FileEvent:
    def __init__(self):
        self.responses = []
        self.query = SimpleNamespace(user_id=42)

    async def respond(self, message, **kwargs):
        self.responses.append((message, kwargs))


@pytest.mark.asyncio
async def test_ui_list_files_reports_files(tmp_path):
    (tmp_path / "report.pdf").write_bytes(b"report")
    event = FileEvent()

    await anketa.ui_list_files(event, tmp_path, "Reports")

    assert event.responses == [("Reports\nreport.pdf\n", {})]


@pytest.mark.asyncio
async def test_ui_list_files_reports_empty_directory(tmp_path):
    event = FileEvent()

    await anketa.ui_list_files(event, tmp_path, "Reports")

    assert event.responses == [("Нет файлов", {})]


@pytest.mark.asyncio
async def test_ui_delete_files_deletes_selected_files(tmp_path, monkeypatch):
    target = tmp_path / "report.pdf"
    target.write_bytes(b"report")
    event = FileEvent()

    async def select_files(*args):
        return ["report.pdf"]

    monkeypatch.setattr(anketa, "unv_select_conversation", select_files)

    await anketa.ui_del_files(event, tmp_path, "Delete")

    assert not target.exists()
    assert event.responses == [("Файлы удалены.", {})]


@pytest.mark.asyncio
async def test_ui_delete_files_reports_empty_directory(tmp_path):
    event = FileEvent()

    await anketa.ui_del_files(event, tmp_path, "Delete")

    assert event.responses == [("Нет файлов", {})]


@pytest.mark.asyncio
async def test_ui_get_files_sends_selected_file(tmp_path, monkeypatch):
    target = tmp_path / "report.pdf"
    target.write_bytes(b"report")
    event = FileEvent()
    sent = []

    async def select_files(*args):
        return ["report.pdf"]

    class Bot:
        async def send_file(self, user_id, filename):
            sent.append((user_id, filename))

    async def no_sleep(_delay):
        pass

    monkeypatch.setattr(anketa, "unv_select_conversation", select_files)
    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.asyncio, "sleep", no_sleep)

    await anketa.ui_get_files(event, tmp_path, "Download")

    assert sent == [(42, str(target))]


@pytest.mark.asyncio
async def test_ui_get_files_ignores_path_traversal_selection(tmp_path, monkeypatch):
    outside = tmp_path.parent / "outside-report.pdf"
    outside.write_bytes(b"outside")
    event = FileEvent()
    sent = []

    async def select_files(*args):
        return ["../outside-report.pdf"]

    class Bot:
        async def send_file(self, user_id, filename):
            sent.append((user_id, filename))

    monkeypatch.setattr(anketa, "unv_select_conversation", select_files)
    monkeypatch.setattr(anketa, "bot", Bot())

    await anketa.ui_get_files(event, tmp_path, "Download")

    assert sent == []
