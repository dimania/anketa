import pytest

from dbmodule import DatabaseBot


@pytest.mark.asyncio
async def test_database_creates_schema_and_stores_answers(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()
        result = await database.db_add_answer(
            "user-1", "Alice", "alice", {"question-1": ["answer-1", "answer-2"]}
        )

        assert result is True
        assert await database.db_exist_id_user("user-1") is not None
        rows = await database.get_info_for_report()
        assert len(rows) == 1
        assert rows[0]["answer_user"] == "answer-1, answer-2"


@pytest.mark.asyncio
async def test_database_rewrites_questions(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()
        await database.db_rewrite_new_questions(
            {"Question": ["Yes", "No"]}, {"Question": "select"}
        )

        question_types, questions = await database.db_load_questions()

        assert question_types == {"Question": "select"}
        assert questions == {"Question": ["Yes", "No"]}


@pytest.mark.asyncio
async def test_database_rewrite_replaces_previous_questions(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()
        await database.db_rewrite_new_questions(
            {"Old question": []}, {"Old question": "simple"}
        )
        await database.db_rewrite_new_questions(
            {"New question": ["Answer"]}, {"New question": "select"}
        )

        question_types, questions = await database.db_load_questions()

        assert question_types == {"New question": "select"}
        assert questions == {"New question": ["Answer"]}


@pytest.mark.asyncio
async def test_database_adds_and_loads_admins(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()
        admin_id = await database.db_add_admins(
            {123: ["alice", "Alice"]}
        )

        admins = await database.db_load_admins()

        assert admin_id == "1"
        assert len(admins) == 1
        assert admins[0]["admin_id"] == 123
        assert admins[0]["admin_nickname"] == "alice"


@pytest.mark.asyncio
async def test_database_deletes_user_answers(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()
        await database.db_add_answer("user-1", "Alice", "alice", {"q": "yes"})
        assert await database.db_exist_id_user("user-1") is not None

        await database.db_del_user_answers("user-1")

        assert await database.db_exist_id_user("user-1") is None


@pytest.mark.asyncio
async def test_database_empty_queries_return_false(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()

        assert await database.db_load_questions() == (False, False)
        assert await database.db_load_admins() is False
        assert await database.get_info_by_users() is False
        assert await database.get_info_for_report() is False


@pytest.mark.asyncio
async def test_database_rejects_duplicate_admin(tmp_path):
    db_file = tmp_path / "anketa.sqlite3"

    async with DatabaseBot(str(db_file)) as database:
        await database.db_create()
        assert await database.db_add_admins({123: ["alice", "Alice"]}) == "1"
        assert await database.db_add_admins({123: ["alice", "Alice"]}) is False
