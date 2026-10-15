import pytest
from types import SimpleNamespace

import anketa


class EmptyEvent:
    def __init__(self):
        self.responses = []

    async def respond(self, message, **kwargs):
        self.responses.append((message, kwargs))


class EmptyDatabase:
    def __init__(self, _db_file):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def db_exist_id_user(self, _user_id):
        return None


class ExistingDatabase(EmptyDatabase):
    async def db_exist_id_user(self, _user_id):
        return {"id": 1}

    
class ExistingDatabaseWithDelete(ExistingDatabase):
    async def db_del_user_answers(self, _user_id):
        return []


@pytest.mark.asyncio
async def test_check_user_run_anketa_starts_new_user(monkeypatch):
    event = EmptyEvent()
    called = {}

    async def run_anketa(user_id, event_bot, menu):
        called.update(user_id=user_id, event=event_bot, menu=menu)

    monkeypatch.setattr(anketa.dbm, "DatabaseBot", EmptyDatabase)
    monkeypatch.setattr(anketa, "run_anketa", run_anketa)

    result = await anketa.check_user_run_anketa(42, event, True)

    assert result == 2
    assert called == {"user_id": 42, "event": event, "menu": True}


@pytest.mark.asyncio
async def test_run_anketa_returns_false_for_empty_questionnaire(monkeypatch):
    class Bot:
        async def get_entity(self, _user_id):
            return type("Entity", (), {"username": "alice", "first_name": "Alice"})()

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa, "all_questions", {})
    monkeypatch.setattr(anketa, "type_questions", {})

    result = await anketa.run_anketa(42, EmptyEvent(), False)

    assert result is False


@pytest.mark.asyncio
async def test_check_user_run_anketa_prompts_existing_user(monkeypatch):
    event = EmptyEvent()
    monkeypatch.setattr(anketa.dbm, "DatabaseBot", ExistingDatabase)

    class Bot:
        def on(self, *_args, **_kwargs):
            def decorator(handler):
                return handler

            return decorator

    monkeypatch.setattr(anketa, "bot", Bot())

    result = await anketa.check_user_run_anketa(42, event, False)

    assert result is None
    assert "уже отвечали" in event.responses[0][0]


@pytest.mark.asyncio
async def test_existing_user_can_decline_restart(monkeypatch):
    event = EmptyEvent()
    handlers = []

    class Bot:
        def on(self, *_args, **_kwargs):
            def decorator(handler):
                handlers.append(handler)
                return handler

            return decorator

        def remove_event_handler(self, handler):
            handlers.remove(handler)

    monkeypatch.setattr(anketa.dbm, "DatabaseBot", ExistingDatabase)
    monkeypatch.setattr(anketa, "bot", Bot())

    await anketa.check_user_run_anketa(42, event, False)
    callback_event = SimpleNamespace(sender_id=42, message_id=None, data=b"/no")
    await handlers[0](callback_event)

    assert "До свидания" in event.responses[-1][0]


@pytest.mark.asyncio
async def test_existing_user_can_restart_and_answers_are_deleted(monkeypatch):
    event = EmptyEvent()
    handlers = []
    restarted = []

    class Bot:
        def on(self, *_args, **_kwargs):
            def decorator(handler):
                handlers.append(handler)
                return handler

            return decorator

        def remove_event_handler(self, handler):
            handlers.remove(handler)

    async def run_anketa(user_id, event_bot, menu):
        restarted.append((user_id, event_bot, menu))

    monkeypatch.setattr(anketa.dbm, "DatabaseBot", ExistingDatabaseWithDelete)
    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa, "run_anketa", run_anketa)

    await anketa.check_user_run_anketa(42, event, True)
    callback_event = SimpleNamespace(sender_id=42, message_id=None, data=b"/yes")
    await handlers[0](callback_event)

    assert restarted == [(42, event, True)]


@pytest.mark.asyncio
async def test_main_initializes_admins_and_loads_questions(monkeypatch):
    class Database:
        def __init__(self, _db_file):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def db_create(self):
            pass

        async def db_load_questions(self):
            return {"Question": "simple"}, {"Question": []}

        async def db_load_admins(self):
            return [{
                "admin_id": 2,
                "admin_nickname": "alice",
                "admin_firstname": "Alice",
            }]

    started = []

    async def main_frontend():
        started.append(True)

    monkeypatch.setattr(anketa.dbm, "DatabaseBot", Database)
    monkeypatch.setattr(anketa, "main_frontend", main_frontend)
    monkeypatch.setattr(anketa.sts, "Admin_ids", {1})
    monkeypatch.setattr(anketa.sts, "Admins", {})
    monkeypatch.setattr(anketa, "all_questions", {})
    monkeypatch.setattr(anketa, "type_questions", {})

    await anketa.main()

    assert anketa.sts.Admins == {1: ("", ""), 2: ("alice", "Alice")}
    assert anketa.all_questions == {"Question": []}
    assert anketa.type_questions == {"Question": "simple"}
    assert started == [True]


@pytest.mark.asyncio
async def test_main_requires_an_admin(monkeypatch):
    monkeypatch.setattr(anketa.sts, "Admin_ids", set())
    monkeypatch.setattr(anketa.sts, "Admins", {})

    with pytest.raises(RuntimeError, match="No administrator IDs configured"):
        await anketa.main()


@pytest.mark.asyncio
async def test_main_frontend_routes_start_for_regular_user(monkeypatch):
    handlers = []
    called = []

    class Bot:
        def on(self, *_args, **_kwargs):
            def decorator(handler):
                handlers.append(handler)
                return handler

            return decorator

    async def check_user(user_id, event, menu):
        called.append((user_id, event, menu))

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.sts, "Admins", {})
    monkeypatch.setattr(anketa, "check_user_run_anketa", check_user)

    await anketa.main_frontend()
    event = SimpleNamespace(
        is_private=True,
        sender_id=42,
        message=SimpleNamespace(message="/start"),
    )
    await handlers[0](event)

    assert called == [(42, event, 0)]


@pytest.mark.asyncio
async def test_main_frontend_ignores_non_admin_callback(monkeypatch):
    handlers = []

    class Bot:
        def on(self, *_args, **_kwargs):
            def decorator(handler):
                handlers.append(handler)
                return handler

            return decorator

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.sts, "Admins", {})

    await anketa.main_frontend()
    event = SimpleNamespace(query=SimpleNamespace(user_id=42), data=b"/am_stats")

    assert await handlers[1](event) == 0


@pytest.mark.asyncio
async def test_main_frontend_routes_admin_stats_callback(monkeypatch):
    handlers = []
    called = []

    class Bot:
        def on(self, *_args, **_kwargs):
            def decorator(handler):
                handlers.append(handler)
                return handler

            return decorator

    async def show_stats(event):
        called.append(("stats", event))

    async def create_admin_menu(level, event):
        called.append(("menu", level, event))

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.sts, "Admins", {42: ("", "")})
    monkeypatch.setattr(anketa, "show_stats", show_stats)
    monkeypatch.setattr(anketa, "create_admin_menu", create_admin_menu)

    await anketa.main_frontend()
    event = SimpleNamespace(query=SimpleNamespace(user_id=42), data=b"/am_stats")
    await handlers[1](event)

    assert called == [("stats", event), ("menu", 0, event)]


@pytest.mark.asyncio
async def test_run_anketa_saves_answer_and_sends_report(monkeypatch, tmp_path):
    saved = {}
    sent_files = []

    class Conversation:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def send_message(self, message, **kwargs):
            pass

        async def get_response(self, **kwargs):
            return SimpleNamespace(text="Alice's answer")

        def cancel(self):
            pass

    class Database:
        def __init__(self, _db_file):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def db_add_answer(self, user_id, first_name, nickname, answers):
            saved.update(
                user_id=user_id,
                first_name=first_name,
                nickname=nickname,
                answers=dict(answers),
            )
            return True

    class Bot:
        def conversation(self, _user_id):
            return Conversation()

        async def get_entity(self, _user_id):
            return SimpleNamespace(username="alice", first_name="Alice")

        async def send_message(self, *args, **kwargs):
            pass

        async def send_file(self, user_id, filename, **kwargs):
            sent_files.append((user_id, filename))

    async def fake_gen_pdf(answers, filename):
        tmp_path.joinpath("generated.pdf").write_bytes(b"pdf")

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.dbm, "DatabaseBot", Database)
    monkeypatch.setattr(anketa, "all_questions", {"Question": [], "Done": []})
    monkeypatch.setattr(
        anketa,
        "type_questions",
        {"Question": "simple", "Done": "footer"},
    )
    monkeypatch.setattr(anketa.sts, "timeout_warning", False)
    monkeypatch.setattr(anketa, "gen_pdf", fake_gen_pdf)
    monkeypatch.setattr(anketa, "REPORT_DIR", tmp_path)

    result = await anketa.run_anketa(42, EmptyEvent(), False)

    assert result is True
    assert saved["user_id"] == 42
    assert saved["answers"] == {1: ["Alice's answer"]}
    assert sent_files and sent_files[0][0] == 42


@pytest.mark.asyncio
async def test_run_anketa_processes_select_and_onlyone_questions(monkeypatch, tmp_path):
    saved = {}

    class Database:
        def __init__(self, _db_file):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def db_add_answer(self, user_id, first_name, nickname, answers):
            saved["answers"] = dict(answers)
            return True

    class Bot:
        async def get_entity(self, _user_id):
            return SimpleNamespace(username="alice", first_name="Alice")

        async def send_message(self, *args, **kwargs):
            pass

        async def send_file(self, *args, **kwargs):
            pass

    async def fake_pdf(answers, filename):
        pass

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.dbm, "DatabaseBot", Database)
    monkeypatch.setattr(
        anketa,
        "all_questions",
        {"Text": [], "Colors": ["Red", "Blue"], "Size": ["S", "L"], "Done": []},
    )
    monkeypatch.setattr(
        anketa,
        "type_questions",
        {"Text": "simple", "Colors": "select", "Size": "onlyone", "Done": "footer"},
    )
    monkeypatch.setattr(anketa.sts, "timeout_warning", False)
    async def simple_answer(*args):
        return "text"

    async def selected_answers(*args):
        return ["Red"]

    async def one_answer(*args):
        return "L"

    monkeypatch.setattr(anketa, "unv_simple_conversation", simple_answer)
    monkeypatch.setattr(anketa, "unv_select_conversation", selected_answers)
    monkeypatch.setattr(anketa, "unv_onlyone_conversation", one_answer)
    monkeypatch.setattr(anketa, "gen_pdf", fake_pdf)
    monkeypatch.setattr(anketa, "REPORT_DIR", tmp_path)

    result = await anketa.run_anketa(42, EmptyEvent(), False)

    assert result is True
    assert saved["answers"] == {1: ["text"], 2: ["1"], 3: "2"}


@pytest.mark.asyncio
async def test_run_anketa_shows_header_and_footer(monkeypatch, tmp_path):
    messages = []
    sent_files = []

    class Database:
        def __init__(self, _db_file):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def db_add_answer(self, *args):
            return True

    class Bot:
        async def get_entity(self, _user_id):
            return SimpleNamespace(username="alice", first_name="Alice")

        async def send_message(self, user_id, message, **kwargs):
            messages.append((user_id, message))

        async def send_file(self, user_id, filename, **kwargs):
            sent_files.append((user_id, filename))

    async def simple_answer(*args):
        return "answer"

    async def fake_pdf(answers, filename):
        tmp_path.joinpath("report.pdf").write_bytes(b"pdf")

    monkeypatch.setattr(anketa, "bot", Bot())
    monkeypatch.setattr(anketa.dbm, "DatabaseBot", Database)
    monkeypatch.setattr(
        anketa,
        "all_questions",
        {"Welcome": ["logo.jpg"], "Question": [], "Finished": ["done.jpg"]},
    )
    monkeypatch.setattr(
        anketa,
        "type_questions",
        {"Welcome": "header", "Question": "simple", "Finished": "footer"},
    )
    monkeypatch.setattr(anketa.sts, "timeout_warning", False)
    monkeypatch.setattr(anketa, "exist_file", lambda name: __import__("asyncio").sleep(0, result=False))
    monkeypatch.setattr(anketa, "unv_simple_conversation", simple_answer)
    monkeypatch.setattr(anketa, "gen_pdf", fake_pdf)
    monkeypatch.setattr(anketa, "REPORT_DIR", tmp_path)

    assert await anketa.run_anketa(42, EmptyEvent(), False) is True
    assert any("Welcome" in message for _, message in messages)
    assert any("Finished" in message for _, message in messages)
