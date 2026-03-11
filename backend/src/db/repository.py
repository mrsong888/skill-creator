from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Message, Setting, Thread


class ThreadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, title: str | None = None, skill_name: str | None = None) -> Thread:
        thread = Thread(title=title, skill_name=skill_name)
        self.session.add(thread)
        await self.session.commit()
        await self.session.refresh(thread)
        return thread

    async def get(self, thread_id: str) -> Thread | None:
        return await self.session.get(Thread, thread_id)

    async def list_all(self) -> list[Thread]:
        result = await self.session.execute(select(Thread).order_by(Thread.updated_at.desc()))
        return list(result.scalars().all())


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, thread_id: str, role: str, content: str, metadata: dict | None = None) -> Message:
        msg = Message(thread_id=thread_id, role=role, content=content, metadata_=metadata)
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def list_by_thread(self, thread_id: str) -> list[Message]:
        result = await self.session.execute(
            select(Message).where(Message.thread_id == thread_id).order_by(Message.created_at)
        )
        return list(result.scalars().all())


class SettingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> str | None:
        setting = await self.session.get(Setting, key)
        return setting.value if setting else None

    async def set(self, key: str, value: str) -> Setting:
        setting = await self.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
        await self.session.commit()
        return setting
