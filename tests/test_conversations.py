from types import SimpleNamespace

import pytest

import anketa


class FakeConversation:
    def __init__(self, response=None, events=None, response_error=None, event_error=None):
        self.response = response
        self.events = list(events or [])
        self.response_error = response_error
        self.event_error = event_error
        self.sent = []
        self.cancelled = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def send_message(self, message, **kwargs):
        self.sent.append((message, kwargs))

    async def get_response(self, **kwargs):
        if self.response_error:
            raise self.response_error
        return SimpleNamespace(text=self.response)

    async def wait_event(self, *args, **kwargs):
        if self.event_error:
            raise self.event_error
        return self.events.pop(0)

    def cancel(self):
        self.cancelled = True


class FakeBot:
    def __init__(self, conversation):
        self.fake_conversation = conversation
        self.edited = []

    def conversation(self, _user_id):
        return self.fake_conversation

    async def edit_message(self, *args, **kwargs):
        self.edited.append((args, kwargs))


class FakeEventBot:
    async def get_sender(self):
        return SimpleNamespace(id=42)


@pytest.mark.asyncio
async def test_unv_simple_conversation_returns_text(monkeypatch):
    conversation = FakeConversation(response="hello")
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_simple_conversation(7, None, "Question")

    assert result == "hello"
    assert conversation.sent[0][0] == "Question"
    assert conversation.cancelled is True


@pytest.mark.asyncio
async def test_unv_simple_conversation_rejects_empty_text(monkeypatch):
    conversation = FakeConversation(response="")
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_simple_conversation(7, None, "Question")

    assert result is False
    assert "Ответ должен содержать" in conversation.sent[-1][0]


@pytest.mark.asyncio
async def test_unv_simple_conversation_handles_timeout(monkeypatch):
    conversation = FakeConversation(response_error=TimeoutError())
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_simple_conversation(7, None, "Question")

    assert result is False
    assert "истекло" in conversation.sent[-1][0]


@pytest.mark.asyncio
async def test_simple_conversation_returns_numbered_answer(monkeypatch):
    conversation = FakeConversation(response="answer")
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.simple_conversation(7, None, 2, 1, "Question")

    assert result[2] == ["answer"]
    assert "Вопрос 2" in conversation.sent[0][0]


@pytest.mark.asyncio
async def test_simple_conversation_rejects_oversized_answer(monkeypatch):
    conversation = FakeConversation(response="x" * 4097)
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.simple_conversation(7, None, 1, 0, "Question")

    assert result is False
    assert "Ответ должен содержать" in conversation.sent[-1][0]


@pytest.mark.asyncio
async def test_simple_conversation_handles_timeout(monkeypatch):
    conversation = FakeConversation(response_error=TimeoutError())
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.simple_conversation(7, None, 1, 0, "Question")

    assert result is False
    assert "истекло" in conversation.sent[-1][0]


@pytest.mark.asyncio
async def test_unv_onlyone_conversation_returns_selected_variant(monkeypatch):
    event = SimpleNamespace(data=b"VARIANT_2")
    conversation = FakeConversation(events=[event])
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_onlyone_conversation(
        7, FakeEventBot(), "Choose", ["1", "2"]
    )

    assert result == "2"
    assert conversation.cancelled is True


@pytest.mark.asyncio
async def test_unv_onlyone_conversation_rejects_unknown_variant(monkeypatch):
    event = SimpleNamespace(data=b"VARIANT_9")
    conversation = FakeConversation(events=[event])
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_onlyone_conversation(
        7, FakeEventBot(), "Choose", ["1", "2"]
    )

    assert result is False


@pytest.mark.asyncio
async def test_unv_onlyone_conversation_handles_timeout(monkeypatch):
    conversation = FakeConversation(event_error=TimeoutError())
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_onlyone_conversation(
        7, FakeEventBot(), "Choose", ["1", "2"]
    )

    assert result is False
    assert "истекло" in conversation.sent[-1][0]


@pytest.mark.asyncio
async def test_unv_select_conversation_collects_selected_variants(monkeypatch):
    query = SimpleNamespace(user_id=7, msg_id=10)
    events = [
        SimpleNamespace(data=b"VARIANT_1", query=query),
        SimpleNamespace(data=b"INVALID", query=query),
        SimpleNamespace(data=b"VARIANT_2", query=query),
        SimpleNamespace(data=b"ANSWER", query=query),
    ]
    conversation = FakeConversation(events=events)
    bot = FakeBot(conversation)
    monkeypatch.setattr(anketa, "bot", bot)

    result = await anketa.unv_select_conversation(
        7, FakeEventBot(), "Choose", "Finish", ["1", "2"]
    )

    assert result == ["1", "2"]
    assert len(bot.edited) == 2
    assert conversation.cancelled is True


@pytest.mark.asyncio
async def test_unv_select_conversation_handles_timeout(monkeypatch):
    conversation = FakeConversation(event_error=TimeoutError())
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))

    result = await anketa.unv_select_conversation(
        7, FakeEventBot(), "Choose", "Finish", ["1", "2"]
    )

    assert result is False
    assert "истекло" in conversation.sent[-1][0]


@pytest.mark.asyncio
async def test_onlyone_conversation_returns_variant_number(monkeypatch):
    event = SimpleNamespace(data=b"VARIANT_0_2")
    conversation = FakeConversation(events=[event])
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))
    monkeypatch.setattr(anketa, "all_questions", {"Question": ["A", "B"]})

    result = await anketa.onlyone_conversation(
        7, FakeEventBot(), 1, 0, "Question"
    )

    assert result[1] == ["2"]


@pytest.mark.asyncio
async def test_onlyone_conversation_handles_timeout(monkeypatch):
    conversation = FakeConversation(event_error=TimeoutError())
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))
    monkeypatch.setattr(anketa, "all_questions", {"Question": ["A", "B"]})

    result = await anketa.onlyone_conversation(
        7, FakeEventBot(), 1, 0, "Question"
    )

    assert result is False


@pytest.mark.asyncio
async def test_select_conversation_collects_and_sorts_variants(monkeypatch):
    query = SimpleNamespace(user_id=7, msg_id=10)
    events = [
        SimpleNamespace(data=b"VARIANT_0_2", query=query),
        SimpleNamespace(data=b"VARIANT_0_1", query=query),
        SimpleNamespace(data=b"ANSWER_0", query=query),
    ]
    conversation = FakeConversation(events=events)
    bot = FakeBot(conversation)
    monkeypatch.setattr(anketa, "bot", bot)
    monkeypatch.setattr(anketa, "all_questions", {"Question": ["A", "B"]})

    result = await anketa.select_conversation(
        7, FakeEventBot(), 1, 0, "Question"
    )

    assert result[1] == ["1", "2"]
    assert len(bot.edited) == 2


@pytest.mark.asyncio
async def test_select_conversation_handles_timeout(monkeypatch):
    conversation = FakeConversation(event_error=TimeoutError())
    monkeypatch.setattr(anketa, "bot", FakeBot(conversation))
    monkeypatch.setattr(anketa, "all_questions", {"Question": ["A", "B"]})

    result = await anketa.select_conversation(
        7, FakeEventBot(), 1, 0, "Question"
    )

    assert result is False
