import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.agent.core import AgentCore
from src.agent.prompt import build_system_prompt
from src.config.settings import get_settings
from src.db.database import get_session
from src.db.repository import MessageRepository, ThreadRepository
from src.memory.injector import format_memory_for_injection
from src.memory.store import MemoryStore
from src.skill.manager import SkillManager

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    skill_name: str | None = None
    page_context: str | None = None


def get_agent() -> AgentCore:
    settings = get_settings()
    return AgentCore(
        model=settings.llm.model,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
    )


@router.post("")
async def chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()
    thread_repo = ThreadRepository(session)
    msg_repo = MessageRepository(session)

    if req.thread_id:
        thread = await thread_repo.get(req.thread_id)
        if not thread:
            thread = await thread_repo.create(title=None, skill_name=req.skill_name)
    else:
        thread = await thread_repo.create(title=None, skill_name=req.skill_name)

    await msg_repo.create(thread_id=thread.id, role="user", content=req.message)

    db_messages = await msg_repo.list_by_thread(thread.id)
    messages = [{"role": m.role, "content": m.content} for m in db_messages]

    memory_text = None
    if settings.memory.enabled:
        store = MemoryStore(storage_path=settings.memory.storage_path)
        memory = store.load()
        memory_text = format_memory_for_injection(memory)

    skill_content = None
    skill_name = req.skill_name or thread.skill_name
    if skill_name:
        mgr = SkillManager(public_path=settings.skills.public_path, custom_path=settings.skills.custom_path)
        skill = mgr.get_skill(skill_name)
        if skill and skill.enabled:
            skill_content = skill.content

    system_prompt = build_system_prompt(
        memory_text=memory_text or None,
        skill_content=skill_content,
        page_context=req.page_context,
    )

    agent = get_agent()

    async def event_generator():
        full_response = ""
        yield {"event": "message_start", "data": json.dumps({"thread_id": thread.id})}

        async for event in agent.run(messages, system_prompt=system_prompt):
            event_type = event["type"]
            yield {"event": event_type, "data": json.dumps(event["data"])}

            if event_type == "content_delta":
                full_response += event["data"].get("delta", "")

        if full_response:
            await msg_repo.create(thread_id=thread.id, role="assistant", content=full_response)

    return EventSourceResponse(event_generator())


@router.get("/history")
async def chat_history(session: AsyncSession = Depends(get_session)):
    repo = ThreadRepository(session)
    threads = await repo.list_all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "skill_name": t.skill_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in threads
    ]


@router.get("/{thread_id}")
async def get_thread_messages(thread_id: str, session: AsyncSession = Depends(get_session)):
    msg_repo = MessageRepository(session)
    messages = await msg_repo.list_by_thread(thread_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "metadata": m.metadata_,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
