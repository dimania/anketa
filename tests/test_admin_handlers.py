import pytest

import anketa


class FakeEvent:
    def __init__(self):
        self.responses = []
        self.deleted = False

    async def respond(self, message, **kwargs):
        self.responses.append((message, kwargs))

    async def delete(self):
        self.deleted = True


@pytest.mark.asyncio
async def test_show_stats_reports_empty_database(monkeypatch):
    event = FakeEvent()

    class EmptyDatabase:
        def __init__(self, _db_file):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get_info_by_users(self):
            return False

    monkeypatch.setattr(anketa.dbm, "DatabaseBot", EmptyDatabase)

    assert await anketa.show_stats(event) is False
    assert "нет информаци" in event.responses[0][0]


@pytest.mark.asyncio
async def test_show_stats_lists_users(monkeypatch):
    event = FakeEvent()

    class Database:
        def __init__(self, _db_file):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get_info_by_users(self):
            return [{"name_user": "Alice"}, {"name_user": "Bob"}]

    monkeypatch.setattr(anketa.dbm, "DatabaseBot", Database)

    assert await anketa.show_stats(event) is True
    assert "Alice" in event.responses[0][0]
    assert "Bob" in event.responses[0][0]


@pytest.mark.asyncio
async def test_del_admins_reports_when_no_deletable_admins(monkeypatch):
    event = FakeEvent()
    monkeypatch.setattr(anketa.sts, "Admins", {1: ("owner", "Owner")})
    monkeypatch.setattr(anketa.sts, "Admin_ids", {1})

    async def create_admin_menu(*args):
        pass

    monkeypatch.setattr(anketa, "create_admin_menu", create_admin_menu)

    assert await anketa.del_admins(event) is False
    assert "Нет админов" in event.responses[0][0]


@pytest.mark.asyncio
async def test_del_admins_creates_buttons(monkeypatch):
    event = FakeEvent()
    monkeypatch.setattr(
        anketa.sts,
        "Admins",
        {1: ("owner", "Owner"), 2: ("alice", "Alice")},
    )
    monkeypatch.setattr(anketa.sts, "Admin_ids", {1})

    assert await anketa.del_admins(event) is True
    assert "Выберете админа" in event.responses[0][0]
    assert len(event.responses[0][1]["buttons"]) == 1


@pytest.mark.asyncio
async def test_show_admins_formats_builtin_and_regular_admins(monkeypatch):
    event = FakeEvent()
    monkeypatch.setattr(
        anketa.sts,
        "Admins",
        {1: ("owner", "Owner"), 2: ("alice", "Alice")},
    )

    async def create_admin_menu(*args):
        pass

    monkeypatch.setattr(anketa, "create_admin_menu", create_admin_menu)

    await anketa.show_admins(event)

    message = event.responses[0][0]
    assert "Owner" in message
    assert "@alice" in message
    assert "(2)" in message


@pytest.mark.asyncio
async def test_check_nickname_returns_entity_data(monkeypatch):
    class Entity:
        id = 42
        username = "alice"
        first_name = "Alice"

    class Bot:
        async def get_entity(self, username):
            assert username == "alice"
            return Entity()

    monkeypatch.setattr(anketa, "bot", Bot())

    assert await anketa.check_nickname("alice") == {42: ("alice", "Alice")}


@pytest.mark.asyncio
async def test_check_nickname_returns_false_for_missing_entity(monkeypatch):
    class Bot:
        async def get_entity(self, username):
            raise ValueError("not found")

    monkeypatch.setattr(anketa, "bot", Bot())

    assert await anketa.check_nickname("missing") is False


@pytest.mark.asyncio
async def test_check_nickname_returns_false_for_unexpected_error(monkeypatch):
    class Bot:
        async def get_entity(self, username):
            raise RuntimeError("network failure")

    monkeypatch.setattr(anketa, "bot", Bot())

    assert await anketa.check_nickname("broken") is False


@pytest.mark.asyncio
async def test_show_admins_handles_empty_admin_list(monkeypatch):
    event = FakeEvent()
    monkeypatch.setattr(anketa.sts, "Admins", {})

    async def create_admin_menu(*args):
        pass

    monkeypatch.setattr(anketa, "create_admin_menu", create_admin_menu)

    await anketa.show_admins(event)

    assert "Cписок текущих Админов" in event.responses[0][0]


@pytest.mark.asyncio
async def test_create_admin_menu_deletes_old_message_and_sends_menu():
    event = FakeEvent()

    await anketa.create_admin_menu(0, event)

    assert event.deleted is True
    assert "Режим" in event.responses[0][0]
    assert event.responses[0][1]["parse_mode"] == "md"


@pytest.mark.asyncio
async def test_show_files_sends_all_file_names():
    event = FakeEvent()

    await anketa.show_files(event, ["one.pdf", "two.xlsx"])

    assert event.responses == [("one.pdf\ntwo.xlsx\n", {})]


@pytest.mark.asyncio
async def test_show_questions_formats_question_types(monkeypatch):
    event = FakeEvent()
    monkeypatch.setattr(
        anketa,
        "all_questions",
        {
            "Welcome": ["logo.jpg"],
            "Choose": ["Yes", "No"],
            "ID4T_1_Comment": [],
            "Done": [],
        },
    )
    monkeypatch.setattr(
        anketa,
        "type_questions",
        {
            "Welcome": "header",
            "Choose": "select",
            "ID4T_1_Comment": "text",
            "Done": "footer",
        },
    )

    async def create_admin_menu(*args):
        pass

    monkeypatch.setattr(anketa, "create_admin_menu", create_admin_menu)

    await anketa.show_qusetions(event)

    message = event.responses[0][0]
    assert "Choose" in message
    assert "Comment" in message
    assert "Yes" in message
    assert "Done" in message
