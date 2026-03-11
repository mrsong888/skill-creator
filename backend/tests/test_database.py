from src.db.repository import MessageRepository, ThreadRepository


async def test_create_thread(db_session):
    repo = ThreadRepository(db_session)
    thread = await repo.create(title="Test Thread")
    assert thread.id is not None
    assert thread.title == "Test Thread"
    assert thread.skill_name is None


async def test_create_thread_with_skill(db_session):
    repo = ThreadRepository(db_session)
    thread = await repo.create(title="Skill Chat", skill_name="code-reviewer")
    assert thread.skill_name == "code-reviewer"


async def test_list_threads(db_session):
    repo = ThreadRepository(db_session)
    await repo.create(title="Thread 1")
    await repo.create(title="Thread 2")
    threads = await repo.list_all()
    assert len(threads) == 2


async def test_create_message(db_session):
    thread_repo = ThreadRepository(db_session)
    thread = await thread_repo.create(title="Test")

    msg_repo = MessageRepository(db_session)
    msg = await msg_repo.create(thread_id=thread.id, role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


async def test_list_messages(db_session):
    thread_repo = ThreadRepository(db_session)
    thread = await thread_repo.create(title="Test")

    msg_repo = MessageRepository(db_session)
    await msg_repo.create(thread_id=thread.id, role="user", content="Hi")
    await msg_repo.create(thread_id=thread.id, role="assistant", content="Hello!")

    messages = await msg_repo.list_by_thread(thread.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
