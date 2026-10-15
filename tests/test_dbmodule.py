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
