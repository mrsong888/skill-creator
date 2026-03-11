# Agent Skill Extension — Backend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend for the Agent + Skill Chrome Extension platform, providing chat (SSE), skill management, memory system, and workspace isolation.

**Architecture:** Single FastAPI service with SQLite for persistence, LiteLLM for multi-model LLM access, filesystem-based skill storage (SKILL.md format compatible with deer-flow), and JSON-file memory storage. Per-thread workspace isolation for file management.

**Tech Stack:** Python 3.12+, FastAPI, Uvicorn, LiteLLM, aiosqlite, SQLAlchemy (async), Pydantic v2, SSE (sse-starlette), APScheduler (reserved)

**Spec:** `/Users/songheng/docs/superpowers/specs/2026-03-12-agent-skill-chrome-extension-design.md`

---

## File Structure

```
agent-skill-extension/backend/
├── pyproject.toml
├── config.yaml
├── Makefile
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, CORS, router registration
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Pydantic Settings (app config, model config, paths)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py            # Async SQLAlchemy engine + session factory
│   │   ├── models.py              # ORM models: Thread, Message, Setting
│   │   └── repository.py          # CRUD operations for threads/messages/settings
│   ├── workspace/
│   │   ├── __init__.py
│   │   ├── manager.py             # Thread directory lifecycle (create/get/cleanup)
│   │   └── files.py               # File upload, download, listing
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── store.py               # Load/save memory.json, atomic writes
│   │   ├── updater.py             # LLM-driven fact extraction + context update
│   │   ├── injector.py            # Format memory for system prompt injection
│   │   ├── queue.py               # Debounced async update queue
│   │   └── prompt.py              # Prompt templates for memory updates
│   ├── skill/
│   │   ├── __init__.py
│   │   ├── types.py               # Skill dataclass / Pydantic model
│   │   ├── loader.py              # Parse SKILL.md (YAML frontmatter + markdown body)
│   │   ├── manager.py             # List/get/enable/disable/install/uninstall
│   │   └── creator.py             # Skill creation flow (draft/test/iterate/install)
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py                # Agent loop: LLM call → tool dispatch → stream
│   │   ├── prompt.py              # System prompt assembly (persona + memory + skill + page)
│   │   └── tools.py               # Built-in tool definitions + registry
│   └── api/
│       ├── __init__.py
│       ├── chat.py                # POST /api/chat (SSE), GET history, GET thread
│       ├── skills.py              # CRUD + install/uninstall endpoints
│       ├── skill_creator.py       # Skill creation flow endpoints
│       ├── memory.py              # GET/PUT/POST reload
│       └── workspace.py           # File list/download/upload
├── skills/
│   ├── public/                    # Built-in skills (e.g., skill-creator)
│   └── custom/                    # User-created skills
├── data/                          # Runtime data (gitignored)
│   ├── memory.json
│   ├── app.db
│   └── threads/
└── tests/
    ├── __init__.py
    ├── conftest.py                # Shared fixtures (async client, temp dirs, test db)
    ├── test_config.py
    ├── test_database.py
    ├── test_workspace.py
    ├── test_memory_store.py
    ├── test_memory_updater.py
    ├── test_memory_injector.py
    ├── test_skill_loader.py
    ├── test_skill_manager.py
    ├── test_agent_prompt.py
    ├── test_agent_core.py
    ├── test_api_chat.py
    ├── test_api_skills.py
    ├── test_api_memory.py
    └── test_api_workspace.py
```

---

## Chunk 1: Project Scaffolding, Config, and Database

### Task 1: Project Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/Makefile`
- Create: `backend/src/__init__.py`
- Create: `backend/src/main.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "agent-skill-extension-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sse-starlette>=2.0.0",
    "litellm>=1.50.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "aiosqlite>=0.20.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0",
    "python-multipart>=0.0.9",
    "aiofiles>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.format]
quote-style = "double"
```

- [ ] **Step 2: Create Makefile**

```makefile
.PHONY: install dev test lint format

install:
	uv sync --all-extras

dev:
	PYTHONPATH=. uv run uvicorn src.main:app --reload --port 8001

test:
	PYTHONPATH=. uv run pytest -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
```

- [ ] **Step 3: Create minimal FastAPI app**

`backend/src/__init__.py`: empty file

`backend/src/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(title="Agent Skill Extension", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Install dependencies and verify**

```bash
cd /Users/songheng/agent-skill-extension/backend && uv sync --all-extras
```

- [ ] **Step 5: Run the server to verify health endpoint**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run uvicorn src.main:app --port 8001 &
sleep 2 && curl http://localhost:8001/health
# Expected: {"status":"ok"}
kill %1
```

- [ ] **Step 6: Initialize git and commit**

```bash
cd /Users/songheng/agent-skill-extension
git init
echo -e "data/\n__pycache__/\n*.pyc\n.venv/\n*.egg-info/\n.ruff_cache/" > .gitignore
git add -A
git commit -m "chore: initial project scaffolding with FastAPI"
```

---

### Task 2: Configuration System

**Files:**
- Create: `backend/src/config/__init__.py`
- Create: `backend/src/config/settings.py`
- Create: `backend/config.yaml`
- Create: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_config.py`:

```python
import os
import tempfile

import yaml

from src.config.settings import AppSettings, load_settings


def test_load_settings_from_yaml():
    config = {
        "llm": {"model": "gpt-4o", "api_key": "test-key"},
        "memory": {"enabled": True, "debounce_seconds": 30},
        "skills": {"public_path": "skills/public", "custom_path": "skills/custom"},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        f.flush()
        settings = load_settings(f.name)

    assert settings.llm.model == "gpt-4o"
    assert settings.llm.api_key == "test-key"
    assert settings.memory.enabled is True
    assert settings.memory.debounce_seconds == 30
    os.unlink(f.name)


def test_load_settings_defaults():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({}, f)
        f.flush()
        settings = load_settings(f.name)

    assert settings.llm.model == "gpt-4o"
    assert settings.memory.enabled is True
    os.unlink(f.name)


def test_env_var_resolution():
    os.environ["TEST_API_KEY"] = "resolved-key"
    config = {"llm": {"model": "gpt-4o", "api_key": "$TEST_API_KEY"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        f.flush()
        settings = load_settings(f.name)

    assert settings.llm.api_key == "resolved-key"
    os.unlink(f.name)
    del os.environ["TEST_API_KEY"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_config.py -v
```
Expected: FAIL (module not found)

- [ ] **Step 3: Implement configuration system**

`backend/src/config/__init__.py`: empty file

`backend/src/config/settings.py`:

```python
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _resolve_env_vars(value):
    """Resolve values starting with $ as environment variables."""
    if isinstance(value, str) and value.startswith("$"):
        return os.environ.get(value[1:], value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


@dataclass
class LLMConfig:
    model: str = "gpt-4o"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class MemoryConfig:
    enabled: bool = True
    debounce_seconds: int = 30
    max_facts: int = 100
    fact_confidence_threshold: float = 0.7
    max_injection_tokens: int = 2000
    storage_path: str = "data/memory.json"


@dataclass
class SkillsConfig:
    public_path: str = "skills/public"
    custom_path: str = "skills/custom"


@dataclass
class DatabaseConfig:
    url: str = "sqlite+aiosqlite:///data/app.db"


@dataclass
class WorkspaceConfig:
    base_path: str = "data/threads"


@dataclass
class AppSettings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)


def load_settings(config_path: str | None = None) -> AppSettings:
    """Load settings from a YAML config file."""
    if config_path is None:
        for candidate in ["config.yaml", "../config.yaml"]:
            if Path(candidate).exists():
                config_path = candidate
                break

    raw = {}
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    raw = _resolve_env_vars(raw)

    llm_data = raw.get("llm", {})
    memory_data = raw.get("memory", {})
    skills_data = raw.get("skills", {})
    database_data = raw.get("database", {})
    workspace_data = raw.get("workspace", {})

    return AppSettings(
        llm=LLMConfig(**{k: v for k, v in llm_data.items() if k in LLMConfig.__dataclass_fields__}),
        memory=MemoryConfig(**{k: v for k, v in memory_data.items() if k in MemoryConfig.__dataclass_fields__}),
        skills=SkillsConfig(**{k: v for k, v in skills_data.items() if k in SkillsConfig.__dataclass_fields__}),
        database=DatabaseConfig(**{k: v for k, v in database_data.items() if k in DatabaseConfig.__dataclass_fields__}),
        workspace=WorkspaceConfig(**{k: v for k, v in workspace_data.items() if k in WorkspaceConfig.__dataclass_fields__}),
    )


# Singleton
_settings: AppSettings | None = None


def get_settings(config_path: str | None = None) -> AppSettings:
    global _settings
    if _settings is None:
        _settings = load_settings(config_path)
    return _settings
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_config.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Create default config.yaml**

`backend/config.yaml`:

```yaml
llm:
  model: gpt-4o
  api_key: $OPENAI_API_KEY
  temperature: 0.7
  max_tokens: 4096

memory:
  enabled: true
  debounce_seconds: 30
  max_facts: 100

skills:
  public_path: skills/public
  custom_path: skills/custom
```

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/config/ backend/config.yaml backend/tests/test_config.py
git commit -m "feat: add configuration system with YAML loading and env var resolution"
```

---

### Task 3: Database Layer

**Files:**
- Create: `backend/src/db/__init__.py`
- Create: `backend/src/db/database.py`
- Create: `backend/src/db/models.py`
- Create: `backend/src/db/repository.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_database.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/__init__.py`: empty file

`backend/tests/conftest.py`:

```python
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base


@pytest.fixture
async def db_session():
    """Create a temporary in-memory database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for workspace tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
```

`backend/tests/test_database.py`:

```python
from src.db.repository import ThreadRepository, MessageRepository


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_database.py -v
```
Expected: FAIL (module not found)

- [ ] **Step 3: Implement database models**

`backend/src/db/__init__.py`: empty file

`backend/src/db/models.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    skill_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    thread_id: Mapped[str] = mapped_column(String, ForeignKey("threads.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
```

- [ ] **Step 4: Implement database connection**

`backend/src/db/database.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base

_engine = None
_session_factory = None


async def init_db(database_url: str = "sqlite+aiosqlite:///data/app.db"):
    global _engine, _session_factory
    _engine = create_async_engine(database_url)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with _session_factory() as session:
        yield session


async def close_db():
    global _engine
    if _engine:
        await _engine.dispose()
```

- [ ] **Step 5: Implement repository**

`backend/src/db/repository.py`:

```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_database.py -v
```
Expected: 5 tests PASS

- [ ] **Step 7: Wire database into FastAPI lifespan**

Update `backend/src/main.py` lifespan:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Agent Skill Extension", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/db/ backend/tests/
git commit -m "feat: add SQLite database layer with Thread, Message, Setting models"
```

---

## Chunk 2: Workspace and Memory

### Task 4: Workspace Manager

**Files:**
- Create: `backend/src/workspace/__init__.py`
- Create: `backend/src/workspace/manager.py`
- Create: `backend/src/workspace/files.py`
- Create: `backend/tests/test_workspace.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_workspace.py`:

```python
from pathlib import Path

from src.workspace.manager import WorkspaceManager


def test_get_thread_dir(temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    thread_dir = wm.get_thread_dir("thread-123")
    assert thread_dir == temp_dir / "thread-123"


def test_ensure_thread_dirs(temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    dirs = wm.ensure_thread_dirs("thread-123")
    assert (temp_dir / "thread-123" / "workspace").is_dir()
    assert (temp_dir / "thread-123" / "uploads").is_dir()
    assert (temp_dir / "thread-123" / "outputs").is_dir()
    assert dirs["workspace"].is_dir()


def test_list_files(temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    dirs = wm.ensure_thread_dirs("thread-456")
    (dirs["workspace"] / "hello.txt").write_text("hello")
    (dirs["outputs"] / "result.json").write_text("{}")

    files = wm.list_files("thread-456")
    filenames = [f["name"] for f in files]
    assert "hello.txt" in filenames
    assert "result.json" in filenames
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_workspace.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement workspace manager**

`backend/src/workspace/__init__.py`: empty file

`backend/src/workspace/manager.py`:

```python
from pathlib import Path


class WorkspaceManager:
    SUBDIRS = ("workspace", "uploads", "outputs")

    def __init__(self, base_path: str | Path = "data/threads"):
        self.base_path = Path(base_path)

    def get_thread_dir(self, thread_id: str) -> Path:
        return self.base_path / thread_id

    def ensure_thread_dirs(self, thread_id: str) -> dict[str, Path]:
        thread_dir = self.get_thread_dir(thread_id)
        result = {}
        for sub in self.SUBDIRS:
            path = thread_dir / sub
            path.mkdir(parents=True, exist_ok=True)
            result[sub] = path
        return result

    def list_files(self, thread_id: str) -> list[dict]:
        thread_dir = self.get_thread_dir(thread_id)
        files = []
        for sub in self.SUBDIRS:
            sub_dir = thread_dir / sub
            if not sub_dir.exists():
                continue
            for f in sub_dir.iterdir():
                if f.is_file():
                    files.append({
                        "name": f.name,
                        "path": str(f.relative_to(thread_dir)),
                        "size": f.stat().st_size,
                        "category": sub,
                    })
        return files
```

`backend/src/workspace/files.py`:

```python
from pathlib import Path

import aiofiles


async def save_upload(upload_dir: Path, filename: str, content: bytes) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)
    return dest


async def read_file(file_path: Path) -> bytes:
    async with aiofiles.open(file_path, "rb") as f:
        return await f.read()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_workspace.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/workspace/ backend/tests/test_workspace.py
git commit -m "feat: add workspace manager with per-thread directory isolation"
```

---

### Task 5: Memory Store

**Files:**
- Create: `backend/src/memory/__init__.py`
- Create: `backend/src/memory/store.py`
- Create: `backend/tests/test_memory_store.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_memory_store.py`:

```python
import json
from pathlib import Path

from src.memory.store import MemoryStore


def test_load_empty(temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    data = store.load()
    assert data["version"] == "1.0"
    assert data["context"]["workContext"]["summary"] == ""
    assert data["facts"] == []


def test_save_and_load(temp_dir):
    path = temp_dir / "memory.json"
    store = MemoryStore(storage_path=path)
    data = store.load()
    data["context"]["workContext"]["summary"] = "Works on AI tools"
    data["facts"].append({
        "id": "fact_1",
        "content": "Prefers Python",
        "category": "preference",
        "confidence": 0.9,
        "createdAt": "2026-03-12T00:00:00Z",
        "source": "thread_1",
    })
    store.save(data)

    reloaded = store.load()
    assert reloaded["context"]["workContext"]["summary"] == "Works on AI tools"
    assert len(reloaded["facts"]) == 1
    assert reloaded["facts"][0]["content"] == "Prefers Python"


def test_atomic_save(temp_dir):
    """Save should be atomic (write to temp then rename)."""
    path = temp_dir / "memory.json"
    store = MemoryStore(storage_path=path)
    data = store.load()
    data["facts"].append({
        "id": "fact_2",
        "content": "Uses VSCode",
        "category": "preference",
        "confidence": 0.8,
        "createdAt": "2026-03-12T00:00:00Z",
        "source": "thread_2",
    })
    store.save(data)
    assert path.exists()
    content = json.loads(path.read_text())
    assert len(content["facts"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_memory_store.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement memory store**

`backend/src/memory/__init__.py`: empty file

`backend/src/memory/store.py`:

```python
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _empty_memory() -> dict:
    return {
        "version": "1.0",
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }


class MemoryStore:
    def __init__(self, storage_path: str | Path = "data/memory.json"):
        self.storage_path = Path(storage_path)
        self._cache: dict | None = None

    def load(self) -> dict:
        if self._cache is not None:
            return self._cache
        if not self.storage_path.exists():
            self._cache = _empty_memory()
            return self._cache
        with open(self.storage_path) as f:
            self._cache = json.load(f)
        return self._cache

    def save(self, data: dict) -> None:
        data["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to temp file then rename
        fd, tmp_path = tempfile.mkstemp(dir=self.storage_path.parent, suffix=".tmp")
        try:
            with open(fd, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            Path(tmp_path).replace(self.storage_path)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        self._cache = data

    def invalidate_cache(self) -> None:
        self._cache = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_memory_store.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/memory/ backend/tests/test_memory_store.py
git commit -m "feat: add memory store with atomic JSON persistence"
```

---

### Task 6: Memory Injector

**Files:**
- Create: `backend/src/memory/injector.py`
- Create: `backend/tests/test_memory_injector.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_memory_injector.py`:

```python
from src.memory.injector import format_memory_for_injection


def test_format_empty_memory():
    memory = {
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }
    result = format_memory_for_injection(memory)
    assert result == ""


def test_format_with_context():
    memory = {
        "context": {
            "workContext": {"summary": "Building AI tools", "updatedAt": "2026-03-12"},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "Launching Chrome extension", "updatedAt": "2026-03-12"},
        },
        "facts": [],
    }
    result = format_memory_for_injection(memory)
    assert "Building AI tools" in result
    assert "Launching Chrome extension" in result


def test_format_with_facts():
    memory = {
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [
            {"id": "f1", "content": "Prefers Python", "category": "preference", "confidence": 0.95},
            {"id": "f2", "content": "Uses dark mode", "category": "preference", "confidence": 0.5},
        ],
    }
    result = format_memory_for_injection(memory, min_confidence=0.7)
    assert "Prefers Python" in result
    assert "Uses dark mode" not in result


def test_max_facts_limit():
    memory = {
        "context": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "facts": [
            {"id": f"f{i}", "content": f"Fact {i}", "category": "knowledge", "confidence": 0.9}
            for i in range(20)
        ],
    }
    result = format_memory_for_injection(memory, max_facts=5)
    # Should only include 5 facts
    assert result.count("Fact ") == 5
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_memory_injector.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement memory injector**

`backend/src/memory/injector.py`:

```python
def format_memory_for_injection(
    memory: dict,
    max_facts: int = 15,
    min_confidence: float = 0.7,
) -> str:
    parts = []

    # Context sections
    context = memory.get("context", {})
    for key, label in [
        ("workContext", "Work Context"),
        ("personalContext", "Personal Context"),
        ("topOfMind", "Top of Mind"),
    ]:
        summary = context.get(key, {}).get("summary", "")
        if summary:
            parts.append(f"**{label}:** {summary}")

    # Facts (filtered by confidence, limited by max_facts)
    facts = memory.get("facts", [])
    filtered = sorted(
        [f for f in facts if f.get("confidence", 0) >= min_confidence],
        key=lambda f: f.get("confidence", 0),
        reverse=True,
    )[:max_facts]

    if filtered:
        fact_lines = [f"- [{f['category']}] {f['content']}" for f in filtered]
        parts.append("**Known Facts:**\n" + "\n".join(fact_lines))

    return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_memory_injector.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/memory/injector.py backend/tests/test_memory_injector.py
git commit -m "feat: add memory injector for system prompt formatting"
```

---

### Task 7: Memory Update Queue and Updater

**Files:**
- Create: `backend/src/memory/queue.py`
- Create: `backend/src/memory/updater.py`
- Create: `backend/src/memory/prompt.py`
- Create: `backend/tests/test_memory_updater.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_memory_updater.py`:

```python
import json

from src.memory.updater import parse_memory_update_response


def test_parse_update_response_with_facts():
    response = json.dumps({
        "context_updates": {
            "workContext": "Now building a Chrome extension"
        },
        "new_facts": [
            {"content": "Prefers TypeScript for frontend", "category": "preference", "confidence": 0.85}
        ],
        "remove_fact_ids": []
    })
    result = parse_memory_update_response(response)
    assert result["context_updates"]["workContext"] == "Now building a Chrome extension"
    assert len(result["new_facts"]) == 1
    assert result["new_facts"][0]["content"] == "Prefers TypeScript for frontend"


def test_parse_update_response_empty():
    response = json.dumps({
        "context_updates": {},
        "new_facts": [],
        "remove_fact_ids": []
    })
    result = parse_memory_update_response(response)
    assert result["context_updates"] == {}
    assert result["new_facts"] == []


def test_parse_invalid_response():
    result = parse_memory_update_response("not json")
    assert result["context_updates"] == {}
    assert result["new_facts"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_memory_updater.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement memory prompt**

`backend/src/memory/prompt.py`:

```python
MEMORY_UPDATE_SYSTEM_PROMPT = """You are a memory extraction system. Analyze the conversation and extract:

1. **Context updates** — Updates to the user's work context, personal context, or top-of-mind priorities.
2. **New facts** — Discrete facts about the user (preferences, knowledge, behaviors, goals).
3. **Facts to remove** — IDs of previously stored facts that are now outdated or contradicted.

Respond with a JSON object:
```json
{
  "context_updates": {
    "workContext": "optional updated summary",
    "personalContext": "optional updated summary",
    "topOfMind": "optional updated summary"
  },
  "new_facts": [
    {"content": "fact text", "category": "preference|knowledge|context|behavior|goal", "confidence": 0.0-1.0}
  ],
  "remove_fact_ids": ["fact_id_1"]
}
```

Only include fields that need updating. Omit unchanged fields from context_updates.
Confidence should reflect how certain you are about the fact (0.7+ to store).
"""


def build_memory_update_prompt(conversation: list[dict], existing_memory: dict) -> str:
    conv_text = "\n".join(f"[{m['role']}]: {m['content']}" for m in conversation)
    existing_facts = "\n".join(
        f"- [{f['id']}] [{f['category']}] {f['content']}"
        for f in existing_memory.get("facts", [])
    )
    return f"""## Existing Memory

### Context
- Work: {existing_memory.get('context', {}).get('workContext', {}).get('summary', '')}
- Personal: {existing_memory.get('context', {}).get('personalContext', {}).get('summary', '')}
- Top of Mind: {existing_memory.get('context', {}).get('topOfMind', {}).get('summary', '')}

### Known Facts
{existing_facts or '(none)'}

## Recent Conversation
{conv_text}

Extract memory updates from this conversation."""
```

- [ ] **Step 4: Implement memory updater**

`backend/src/memory/updater.py`:

```python
import json
import uuid
from datetime import datetime, timezone

import litellm

from src.memory.prompt import MEMORY_UPDATE_SYSTEM_PROMPT, build_memory_update_prompt
from src.memory.store import MemoryStore


def parse_memory_update_response(response_text: str) -> dict:
    """Parse LLM response into structured memory update."""
    try:
        # Try to extract JSON from response (may be wrapped in markdown code block)
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        return {"context_updates": {}, "new_facts": [], "remove_fact_ids": []}


def apply_memory_update(memory: dict, update: dict) -> dict:
    """Apply parsed update to memory data."""
    now = datetime.now(timezone.utc).isoformat()

    # Apply context updates
    for key, summary in update.get("context_updates", {}).items():
        if key in memory.get("context", {}):
            memory["context"][key] = {"summary": summary, "updatedAt": now}

    # Remove outdated facts
    remove_ids = set(update.get("remove_fact_ids", []))
    if remove_ids:
        memory["facts"] = [f for f in memory.get("facts", []) if f["id"] not in remove_ids]

    # Add new facts
    for fact in update.get("new_facts", []):
        memory["facts"].append({
            "id": f"fact_{uuid.uuid4().hex[:8]}",
            "content": fact["content"],
            "category": fact.get("category", "knowledge"),
            "confidence": fact.get("confidence", 0.8),
            "createdAt": now,
            "source": fact.get("source", ""),
        })

    return memory


async def run_memory_update(
    conversation: list[dict],
    store: MemoryStore,
    model: str = "gpt-4o",
) -> None:
    """Run LLM-driven memory update from a conversation."""
    memory = store.load()
    prompt = build_memory_update_prompt(conversation, memory)

    response = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": MEMORY_UPDATE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    update = parse_memory_update_response(response.choices[0].message.content)
    memory = apply_memory_update(memory, update)
    store.save(memory)
```

- [ ] **Step 5: Implement update queue**

`backend/src/memory/queue.py`:

```python
import asyncio
import logging
from collections import defaultdict

from src.memory.store import MemoryStore
from src.memory.updater import run_memory_update

logger = logging.getLogger(__name__)


class MemoryUpdateQueue:
    def __init__(self, store: MemoryStore, debounce_seconds: float = 30.0, model: str = "gpt-4o"):
        self.store = store
        self.debounce_seconds = debounce_seconds
        self.model = model
        self._pending: dict[str, list[dict]] = defaultdict(list)
        self._timers: dict[str, asyncio.Task] = {}

    def enqueue(self, thread_id: str, messages: list[dict]) -> None:
        """Queue conversation messages for memory update (debounced per thread)."""
        self._pending[thread_id].extend(messages)

        # Cancel existing timer for this thread
        if thread_id in self._timers:
            self._timers[thread_id].cancel()

        # Start new debounce timer
        self._timers[thread_id] = asyncio.create_task(self._debounced_update(thread_id))

    async def _debounced_update(self, thread_id: str) -> None:
        await asyncio.sleep(self.debounce_seconds)
        messages = self._pending.pop(thread_id, [])
        self._timers.pop(thread_id, None)
        if not messages:
            return
        try:
            await run_memory_update(messages, self.store, model=self.model)
        except Exception:
            logger.exception(f"Memory update failed for thread {thread_id}")
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_memory_updater.py -v
```
Expected: 3 tests PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/memory/ backend/tests/test_memory_updater.py
git commit -m "feat: add memory updater with LLM extraction and debounced queue"
```

---

## Chunk 3: Skill System

### Task 8: Skill Types and Loader

**Files:**
- Create: `backend/src/skill/__init__.py`
- Create: `backend/src/skill/types.py`
- Create: `backend/src/skill/loader.py`
- Create: `backend/tests/test_skill_loader.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_skill_loader.py`:

```python
from pathlib import Path

from src.skill.loader import parse_skill_md
from src.skill.types import Skill


def test_parse_skill_md(temp_dir):
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill
license: MIT
allowed-tools:
  - bash
  - read_file
---

# Test Skill

You are a test assistant. Follow these instructions carefully.
""")

    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert skill.license == "MIT"
    assert skill.allowed_tools == ["bash", "read_file"]
    assert "You are a test assistant" in skill.content


def test_parse_skill_md_minimal(temp_dir):
    skill_dir = temp_dir / "minimal"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: minimal
description: Minimal skill
---

Do something simple.
""")

    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill.name == "minimal"
    assert skill.allowed_tools == []
    assert "Do something simple" in skill.content


def test_parse_skill_md_no_frontmatter(temp_dir):
    skill_dir = temp_dir / "nofm"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Just content\n\nNo frontmatter here.")

    skill = parse_skill_md(skill_dir / "SKILL.md")
    assert skill.name == "nofm"  # Falls back to directory name
    assert "Just content" in skill.content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_skill_loader.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement skill types**

`backend/src/skill/__init__.py`: empty file

`backend/src/skill/types.py`:

```python
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str = ""
    license: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    content: str = ""
    path: str = ""
    category: str = "custom"  # "public" or "custom"
    enabled: bool = True
```

- [ ] **Step 4: Implement skill loader**

`backend/src/skill/loader.py`:

```python
from pathlib import Path

import yaml

from src.skill.types import Skill


def parse_skill_md(skill_md_path: Path) -> Skill:
    """Parse a SKILL.md file into a Skill object."""
    text = skill_md_path.read_text(encoding="utf-8")
    frontmatter = {}
    content = text

    # Parse YAML frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                frontmatter = {}
            content = parts[2].strip()

    # Fall back to directory name if no name in frontmatter
    name = frontmatter.get("name", skill_md_path.parent.name)

    return Skill(
        name=name,
        description=frontmatter.get("description", ""),
        license=frontmatter.get("license", ""),
        allowed_tools=frontmatter.get("allowed-tools", []),
        content=content,
        path=str(skill_md_path.parent),
    )


def scan_skills_directory(skills_dir: Path, category: str = "custom") -> list[Skill]:
    """Scan a directory for skill subdirectories containing SKILL.md."""
    skills = []
    if not skills_dir.exists():
        return skills
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if entry.is_dir() and skill_md.exists():
            skill = parse_skill_md(skill_md)
            skill.category = category
            skills.append(skill)
    return skills
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_skill_loader.py -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/skill/ backend/tests/test_skill_loader.py
git commit -m "feat: add skill types and SKILL.md parser with YAML frontmatter"
```

---

### Task 9: Skill Manager

**Files:**
- Create: `backend/src/skill/manager.py`
- Create: `backend/tests/test_skill_manager.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_skill_manager.py`:

```python
import json
from pathlib import Path

from src.skill.manager import SkillManager


def _create_skill(base: Path, category: str, name: str, desc: str = "Test"):
    d = base / category / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\nContent for {name}.")


def test_list_skills(temp_dir):
    _create_skill(temp_dir, "public", "reviewer", "Code reviewer")
    _create_skill(temp_dir, "custom", "my-tool", "My custom tool")

    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    skills = mgr.list_skills()
    names = [s.name for s in skills]
    assert "reviewer" in names
    assert "my-tool" in names


def test_get_skill(temp_dir):
    _create_skill(temp_dir, "public", "reviewer", "Code reviewer")
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    skill = mgr.get_skill("reviewer")
    assert skill is not None
    assert skill.description == "Code reviewer"


def test_get_skill_not_found(temp_dir):
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    assert mgr.get_skill("nonexistent") is None


def test_enable_disable_skill(temp_dir):
    _create_skill(temp_dir, "custom", "my-tool")
    config_path = temp_dir / "extensions.json"

    mgr = SkillManager(
        public_path=temp_dir / "public",
        custom_path=temp_dir / "custom",
        extensions_config_path=config_path,
    )
    mgr.set_enabled("my-tool", False)
    skills = mgr.list_skills()
    my_tool = next(s for s in skills if s.name == "my-tool")
    assert my_tool.enabled is False

    mgr.set_enabled("my-tool", True)
    skills = mgr.list_skills()
    my_tool = next(s for s in skills if s.name == "my-tool")
    assert my_tool.enabled is True


def test_uninstall_custom_skill(temp_dir):
    _create_skill(temp_dir, "custom", "my-tool")
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    assert mgr.uninstall_skill("my-tool") is True
    assert mgr.get_skill("my-tool") is None


def test_uninstall_public_skill_fails(temp_dir):
    _create_skill(temp_dir, "public", "reviewer")
    mgr = SkillManager(public_path=temp_dir / "public", custom_path=temp_dir / "custom")
    assert mgr.uninstall_skill("reviewer") is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_skill_manager.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement skill manager**

`backend/src/skill/manager.py`:

```python
import json
import shutil
from pathlib import Path

from src.skill.loader import scan_skills_directory
from src.skill.types import Skill


class SkillManager:
    def __init__(
        self,
        public_path: str | Path = "skills/public",
        custom_path: str | Path = "skills/custom",
        extensions_config_path: str | Path | None = None,
    ):
        self.public_path = Path(public_path)
        self.custom_path = Path(custom_path)
        self.extensions_config_path = Path(extensions_config_path) if extensions_config_path else None

    def _load_enabled_state(self) -> dict[str, bool]:
        if not self.extensions_config_path or not self.extensions_config_path.exists():
            return {}
        with open(self.extensions_config_path) as f:
            data = json.load(f)
        return {name: cfg.get("enabled", True) for name, cfg in data.get("skills", {}).items()}

    def _save_enabled_state(self, states: dict[str, bool]) -> None:
        if not self.extensions_config_path:
            return
        data = {}
        if self.extensions_config_path.exists():
            with open(self.extensions_config_path) as f:
                data = json.load(f)
        data.setdefault("skills", {})
        for name, enabled in states.items():
            data["skills"].setdefault(name, {})["enabled"] = enabled
        self.extensions_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.extensions_config_path, "w") as f:
            json.dump(data, f, indent=2)

    def list_skills(self) -> list[Skill]:
        enabled_states = self._load_enabled_state()
        skills = []
        for skill in scan_skills_directory(self.public_path, category="public"):
            skill.enabled = enabled_states.get(skill.name, True)
            skills.append(skill)
        for skill in scan_skills_directory(self.custom_path, category="custom"):
            skill.enabled = enabled_states.get(skill.name, True)
            skills.append(skill)
        return skills

    def get_skill(self, name: str) -> Skill | None:
        for skill in self.list_skills():
            if skill.name == name:
                return skill
        return None

    def set_enabled(self, name: str, enabled: bool) -> None:
        states = self._load_enabled_state()
        states[name] = enabled
        self._save_enabled_state(states)

    def install_skill(self, skill_dir: Path) -> Skill | None:
        """Install a skill from a directory into custom skills."""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return None
        from src.skill.loader import parse_skill_md
        skill = parse_skill_md(skill_md)
        dest = self.custom_path / skill.name
        if dest.exists():
            shutil.rmtree(dest)
        self.custom_path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, dest)
        skill.path = str(dest)
        skill.category = "custom"
        return skill

    def uninstall_skill(self, name: str) -> bool:
        """Uninstall a custom skill. Returns False if skill is public or not found."""
        skill = self.get_skill(name)
        if not skill or skill.category != "custom":
            return False
        shutil.rmtree(skill.path)
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_skill_manager.py -v
```
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/skill/manager.py backend/tests/test_skill_manager.py
git commit -m "feat: add skill manager with list/get/enable/install/uninstall"
```

---

## Chunk 4: Agent Core

### Task 10: System Prompt Assembly

**Files:**
- Create: `backend/src/agent/__init__.py`
- Create: `backend/src/agent/prompt.py`
- Create: `backend/tests/test_agent_prompt.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_agent_prompt.py`:

```python
from src.agent.prompt import build_system_prompt


def test_base_prompt_only():
    prompt = build_system_prompt()
    assert "You are a helpful AI assistant" in prompt


def test_with_memory():
    memory_text = "**Work Context:** Building AI tools"
    prompt = build_system_prompt(memory_text=memory_text)
    assert "<memory>" in prompt
    assert "Building AI tools" in prompt


def test_with_skill():
    skill_content = "You are a code reviewer. Review code carefully."
    prompt = build_system_prompt(skill_content=skill_content)
    assert "<skill>" in prompt
    assert "code reviewer" in prompt


def test_with_page_context():
    page = "Title: Example\nContent: This is a web page about Python."
    prompt = build_system_prompt(page_context=page)
    assert "<page_context>" in prompt
    assert "Python" in prompt


def test_full_assembly():
    prompt = build_system_prompt(
        memory_text="Work: AI",
        skill_content="Review code",
        page_context="Page about JS",
    )
    assert "<memory>" in prompt
    assert "<skill>" in prompt
    assert "<page_context>" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_agent_prompt.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement prompt assembly**

`backend/src/agent/__init__.py`: empty file

`backend/src/agent/prompt.py`:

```python
BASE_SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a Chrome extension. You assist employees with their daily tasks, answer questions, and execute skills when bound to a conversation.

You have access to tools for file operations and other tasks. Use them when appropriate.

Be concise, accurate, and helpful. When a skill is active, follow its instructions precisely."""


def build_system_prompt(
    memory_text: str | None = None,
    skill_content: str | None = None,
    page_context: str | None = None,
) -> str:
    parts = [BASE_SYSTEM_PROMPT]

    if memory_text:
        parts.append(f"<memory>\n{memory_text}\n</memory>")

    if skill_content:
        parts.append(f"<skill>\n{skill_content}\n</skill>")

    if page_context:
        parts.append(f"<page_context>\n{page_context}\n</page_context>")

    return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_agent_prompt.py -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/agent/ backend/tests/test_agent_prompt.py
git commit -m "feat: add system prompt assembly with memory/skill/page injection"
```

---

### Task 11: Agent Core (LLM + Tool Use + Streaming)

**Files:**
- Create: `backend/src/agent/tools.py`
- Create: `backend/src/agent/core.py`
- Create: `backend/tests/test_agent_core.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_agent_core.py`:

```python
from unittest.mock import AsyncMock, patch

from src.agent.core import AgentCore


async def test_agent_simple_response():
    """Test agent produces a response from a simple message."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "Hello! How can I help?"
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.acompletion", return_value=mock_response) as mock_llm:
        agent = AgentCore(model="gpt-4o")
        chunks = []
        async for event in agent.run([{"role": "user", "content": "Hi"}]):
            chunks.append(event)

        assert any(e["type"] == "content_delta" for e in chunks)
        assert any(e["type"] == "message_end" for e in chunks)


async def test_agent_with_system_prompt():
    """Test agent uses provided system prompt."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "I'm a reviewer."
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].finish_reason = "stop"

    with patch("litellm.acompletion", return_value=mock_response) as mock_llm:
        agent = AgentCore(model="gpt-4o")
        chunks = []
        async for event in agent.run(
            [{"role": "user", "content": "Who are you?"}],
            system_prompt="You are a code reviewer.",
        ):
            chunks.append(event)

        call_args = mock_llm.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "code reviewer" in messages[0]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_agent_core.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement built-in tools**

`backend/src/agent/tools.py`:

```python
import json
from pathlib import Path

# Tool definitions for LLM function calling
BUILT_IN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                },
                "required": ["path"],
            },
        },
    },
]


async def execute_tool(name: str, arguments: dict, workspace_root: Path | None = None) -> str:
    """Execute a built-in tool and return the result as a string."""
    base = workspace_root or Path(".")

    if name == "read_file":
        path = base / arguments["path"]
        if not path.exists():
            return f"Error: File not found: {arguments['path']}"
        return path.read_text(encoding="utf-8")

    elif name == "write_file":
        path = base / arguments["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(arguments["content"], encoding="utf-8")
        return f"Written to {arguments['path']}"

    elif name == "list_files":
        path = base / arguments["path"]
        if not path.exists():
            return f"Error: Directory not found: {arguments['path']}"
        entries = []
        for entry in sorted(path.iterdir()):
            prefix = "[dir]" if entry.is_dir() else "[file]"
            entries.append(f"{prefix} {entry.name}")
        return "\n".join(entries) or "(empty directory)"

    return f"Error: Unknown tool: {name}"
```

- [ ] **Step 4: Implement agent core**

`backend/src/agent/core.py`:

```python
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import litellm

from src.agent.tools import BUILT_IN_TOOLS, execute_tool


class AgentCore:
    def __init__(self, model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def run(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        workspace_root: Path | None = None,
        max_tool_rounds: int = 10,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run the agent loop, yielding SSE-compatible events."""
        all_tools = list(BUILT_IN_TOOLS)
        if tools:
            all_tools.extend(tools)

        llm_messages = []
        if system_prompt:
            llm_messages.append({"role": "system", "content": system_prompt})
        llm_messages.extend(messages)

        for _ in range(max_tool_rounds):
            response = await litellm.acompletion(
                model=self.model,
                messages=llm_messages,
                tools=all_tools if all_tools else None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            # If there are tool calls, execute them
            if assistant_msg.tool_calls:
                llm_messages.append({"role": "assistant", "content": assistant_msg.content, "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in assistant_msg.tool_calls
                ]})

                for tc in assistant_msg.tool_calls:
                    yield {
                        "type": "tool_use",
                        "data": {"tool": tc.function.name, "input": json.loads(tc.function.arguments), "status": "running"},
                    }

                    args = json.loads(tc.function.arguments)
                    result = await execute_tool(tc.function.name, args, workspace_root)

                    yield {
                        "type": "tool_result",
                        "data": {"tool": tc.function.name, "output": result},
                    }

                    llm_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

                continue  # Next round with tool results

            # No tool calls — emit content and finish
            if assistant_msg.content:
                yield {"type": "content_delta", "data": {"delta": assistant_msg.content}}

            yield {"type": "message_end", "data": {"finish_reason": choice.finish_reason}}
            return

        # Exceeded max tool rounds
        yield {"type": "message_end", "data": {"finish_reason": "max_tool_rounds"}}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_agent_core.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/agent/ backend/tests/test_agent_core.py
git commit -m "feat: add agent core with LLM tool-use loop and SSE event generation"
```

---

## Chunk 5: API Layer

### Task 12: Chat API

**Files:**
- Create: `backend/src/api/__init__.py`
- Create: `backend/src/api/chat.py`
- Create: `backend/tests/test_api_chat.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_chat.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_chat_history(client):
    response = await client.get("/api/chat/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_chat_creates_thread(client):
    """POST /api/chat with no thread_id creates a new thread."""
    async def mock_agent_run(*args, **kwargs):
        yield {"type": "content_delta", "data": {"delta": "Hi"}}
        yield {"type": "message_end", "data": {"finish_reason": "stop"}}

    with patch("src.api.chat.get_agent") as mock_get_agent:
        mock_agent = AsyncMock()
        mock_agent.run = mock_agent_run
        mock_get_agent.return_value = mock_agent

        response = await client.post("/api/chat", json={
            "message": "Hello",
        })
        assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_chat.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement chat API**

`backend/src/api/__init__.py`: empty file

`backend/src/api/chat.py`:

```python
import json

from fastapi import APIRouter, Depends, Request
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

    # Get or create thread
    if req.thread_id:
        thread = await thread_repo.get(req.thread_id)
        if not thread:
            thread = await thread_repo.create(title=None, skill_name=req.skill_name)
    else:
        thread = await thread_repo.create(title=None, skill_name=req.skill_name)

    # Save user message
    await msg_repo.create(thread_id=thread.id, role="user", content=req.message)

    # Load conversation history
    db_messages = await msg_repo.list_by_thread(thread.id)
    messages = [{"role": m.role, "content": m.content} for m in db_messages]

    # Build system prompt
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

        # Save assistant response
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
```

- [ ] **Step 4: Register router in main.py**

Update `backend/src/main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.chat import router as chat_router
from src.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Agent Skill Extension", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_chat.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/api/chat.py backend/src/api/__init__.py backend/src/main.py backend/tests/test_api_chat.py
git commit -m "feat: add chat API with SSE streaming and conversation persistence"
```

---

### Task 13: Skills API

**Files:**
- Create: `backend/src/api/skills.py`
- Create: `backend/tests/test_api_skills.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_skills.py`:

```python
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.skill.manager import SkillManager


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def skill_dirs(temp_dir):
    public = temp_dir / "public"
    custom = temp_dir / "custom"
    public.mkdir()
    custom.mkdir()
    # Create a test skill
    sd = public / "test-skill"
    sd.mkdir()
    (sd / "SKILL.md").write_text("---\nname: test-skill\ndescription: Test\n---\n\nContent.")
    return public, custom


async def test_list_skills(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.get("/api/skills")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-skill"


async def test_get_skill(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.get("/api/skills/test-skill")
    assert response.status_code == 200
    assert response.json()["name"] == "test-skill"


async def test_get_skill_not_found(client, skill_dirs):
    public, custom = skill_dirs
    with patch("src.api.skills.get_skill_manager", return_value=SkillManager(public, custom)):
        response = await client.get("/api/skills/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_skills.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement skills API**

`backend/src/api/skills.py`:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config.settings import get_settings
from src.skill.manager import SkillManager

router = APIRouter(prefix="/api/skills", tags=["skills"])


def get_skill_manager() -> SkillManager:
    settings = get_settings()
    return SkillManager(
        public_path=settings.skills.public_path,
        custom_path=settings.skills.custom_path,
    )


@router.get("")
async def list_skills():
    mgr = get_skill_manager()
    skills = mgr.list_skills()
    return [
        {
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "enabled": s.enabled,
        }
        for s in skills
    ]


@router.get("/{name}")
async def get_skill(name: str):
    mgr = get_skill_manager()
    skill = mgr.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {
        "name": skill.name,
        "description": skill.description,
        "license": skill.license,
        "allowed_tools": skill.allowed_tools,
        "content": skill.content,
        "category": skill.category,
        "enabled": skill.enabled,
    }


class EnableRequest(BaseModel):
    enabled: bool


@router.put("/{name}")
async def update_skill_enabled(name: str, req: EnableRequest):
    mgr = get_skill_manager()
    skill = mgr.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    mgr.set_enabled(name, req.enabled)
    return {"name": name, "enabled": req.enabled}


@router.delete("/{name}")
async def uninstall_skill(name: str):
    mgr = get_skill_manager()
    if not mgr.uninstall_skill(name):
        raise HTTPException(status_code=400, detail="Cannot uninstall: skill not found or is a public skill")
    return {"deleted": name}
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/src/main.py`:

```python
from src.api.skills import router as skills_router
# ... after chat_router registration
app.include_router(skills_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_skills.py -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/api/skills.py backend/src/main.py backend/tests/test_api_skills.py
git commit -m "feat: add skills API with list/get/enable/uninstall endpoints"
```

---

### Task 14: Memory API

**Files:**
- Create: `backend/src/api/memory.py`
- Create: `backend/tests/test_api_memory.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_memory.py`:

```python
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.memory.store import MemoryStore


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_memory(client, temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    with patch("src.api.memory.get_memory_store", return_value=store):
        response = await client.get("/api/memory")
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert "facts" in data


async def test_reload_memory(client, temp_dir):
    store = MemoryStore(storage_path=temp_dir / "memory.json")
    with patch("src.api.memory.get_memory_store", return_value=store):
        response = await client.post("/api/memory/reload")
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_memory.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement memory API**

`backend/src/api/memory.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel

from src.config.settings import get_settings
from src.memory.store import MemoryStore

router = APIRouter(prefix="/api/memory", tags=["memory"])


def get_memory_store() -> MemoryStore:
    settings = get_settings()
    return MemoryStore(storage_path=settings.memory.storage_path)


@router.get("")
async def get_memory():
    store = get_memory_store()
    return store.load()


@router.post("/reload")
async def reload_memory():
    store = get_memory_store()
    store.invalidate_cache()
    return store.load()


class MemoryUpdateRequest(BaseModel):
    context: dict | None = None
    facts: list[dict] | None = None


@router.put("")
async def update_memory(req: MemoryUpdateRequest):
    store = get_memory_store()
    data = store.load()
    if req.context:
        for key, value in req.context.items():
            if key in data["context"]:
                data["context"][key] = value
    if req.facts is not None:
        data["facts"] = req.facts
    store.save(data)
    return data
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/src/main.py`:

```python
from src.api.memory import router as memory_router
app.include_router(memory_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_memory.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/api/memory.py backend/src/main.py backend/tests/test_api_memory.py
git commit -m "feat: add memory API with get/reload/update endpoints"
```

---

### Task 15: Workspace API

**Files:**
- Create: `backend/src/api/workspace.py`
- Create: `backend/tests/test_api_workspace.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_workspace.py`:

```python
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.workspace.manager import WorkspaceManager


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_list_workspace_files(client, temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    dirs = wm.ensure_thread_dirs("thread-1")
    (dirs["workspace"] / "test.txt").write_text("hello")

    with patch("src.api.workspace.get_workspace_manager", return_value=wm):
        response = await client.get("/api/workspace/thread-1/files")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test.txt"


async def test_upload_file(client, temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    wm.ensure_thread_dirs("thread-1")

    with patch("src.api.workspace.get_workspace_manager", return_value=wm):
        response = await client.post(
            "/api/workspace/thread-1/upload",
            files={"file": ("test.txt", b"file content", "text/plain")},
        )
    assert response.status_code == 200
    assert response.json()["filename"] == "test.txt"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_workspace.py -v
```
Expected: FAIL

- [ ] **Step 3: Implement workspace API**

`backend/src/api/workspace.py`:

```python
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from src.config.settings import get_settings
from src.workspace.manager import WorkspaceManager

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def get_workspace_manager() -> WorkspaceManager:
    settings = get_settings()
    return WorkspaceManager(base_path=settings.workspace.base_path)


@router.get("/{thread_id}/files")
async def list_files(thread_id: str):
    wm = get_workspace_manager()
    return wm.list_files(thread_id)


@router.get("/{thread_id}/file")
async def download_file(thread_id: str, path: str):
    wm = get_workspace_manager()
    thread_dir = wm.get_thread_dir(thread_id)
    file_path = thread_dir / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@router.post("/{thread_id}/upload")
async def upload_file(thread_id: str, file: UploadFile):
    wm = get_workspace_manager()
    dirs = wm.ensure_thread_dirs(thread_id)
    content = await file.read()
    dest = dirs["uploads"] / file.filename
    dest.write_bytes(content)
    return {"filename": file.filename, "size": len(content), "path": f"uploads/{file.filename}"}
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/src/main.py`:

```python
from src.api.workspace import router as workspace_router
app.include_router(workspace_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest tests/test_api_workspace.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/api/workspace.py backend/src/main.py backend/tests/test_api_workspace.py
git commit -m "feat: add workspace API with file list/download/upload"
```

---

## Chunk 6: Skill Creator and Final Integration

### Task 16: Skill Creator

**Files:**
- Create: `backend/src/skill/creator.py`
- Create: `backend/src/api/skill_creator.py`

- [ ] **Step 1: Implement skill creator**

`backend/src/skill/creator.py`:

```python
from pathlib import Path

from src.skill.types import Skill


def generate_skill_draft(name: str, description: str, content: str, allowed_tools: list[str] | None = None) -> str:
    """Generate a SKILL.md file content from structured input."""
    frontmatter_lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
    ]
    if allowed_tools:
        frontmatter_lines.append("allowed-tools:")
        for tool in allowed_tools:
            frontmatter_lines.append(f"  - {tool}")
    frontmatter_lines.append("---")
    frontmatter_lines.append("")
    frontmatter_lines.append(content)
    return "\n".join(frontmatter_lines)


def save_skill_draft(workspace_dir: Path, skill_md_content: str, name: str) -> Path:
    """Save a skill draft to the workspace."""
    draft_dir = workspace_dir / "skill-draft" / name
    draft_dir.mkdir(parents=True, exist_ok=True)
    skill_path = draft_dir / "SKILL.md"
    skill_path.write_text(skill_md_content, encoding="utf-8")
    return draft_dir
```

- [ ] **Step 2: Implement skill creator API**

`backend/src/api/skill_creator.py`:

```python
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.agent.core import AgentCore
from src.config.settings import get_settings
from src.skill.creator import generate_skill_draft, save_skill_draft
from src.skill.manager import SkillManager
from src.workspace.manager import WorkspaceManager

router = APIRouter(prefix="/api/skill-creator", tags=["skill-creator"])

SKILL_CREATOR_PROMPT = """You are a skill creation assistant. Help the user create a new skill by:
1. Understanding their requirements
2. Generating a SKILL.md file with appropriate frontmatter and instructions
3. Suggesting test cases to validate the skill

A skill is defined by a SKILL.md file with YAML frontmatter (name, description, allowed-tools) and markdown content that serves as instructions for the AI agent when the skill is active."""


class StartRequest(BaseModel):
    message: str
    thread_id: str | None = None


class InstallRequest(BaseModel):
    thread_id: str
    skill_name: str


@router.post("/start")
async def start_creation(req: StartRequest):
    settings = get_settings()
    agent = AgentCore(model=settings.llm.model)

    async def event_generator():
        async for event in agent.run(
            [{"role": "user", "content": req.message}],
            system_prompt=SKILL_CREATOR_PROMPT,
        ):
            yield {"event": event["type"], "data": json.dumps(event["data"])}

    return EventSourceResponse(event_generator())


@router.post("/install")
async def install_from_draft(req: InstallRequest):
    settings = get_settings()
    wm = WorkspaceManager(base_path=settings.workspace.base_path)
    draft_dir = wm.get_thread_dir(req.thread_id) / "workspace" / "skill-draft" / req.skill_name

    if not (draft_dir / "SKILL.md").exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Skill draft not found")

    mgr = SkillManager(public_path=settings.skills.public_path, custom_path=settings.skills.custom_path)
    skill = mgr.install_skill(draft_dir)
    if not skill:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Failed to install skill")

    return {"name": skill.name, "installed": True}
```

- [ ] **Step 3: Register router in main.py**

Add to `backend/src/main.py`:

```python
from src.api.skill_creator import router as skill_creator_router
app.include_router(skill_creator_router)
```

- [ ] **Step 4: Commit**

```bash
cd /Users/songheng/agent-skill-extension
git add backend/src/skill/creator.py backend/src/api/skill_creator.py backend/src/main.py
git commit -m "feat: add skill creator with draft generation and install flow"
```

---

### Task 17: Final Integration and Smoke Test

**Files:**
- Modify: `backend/src/main.py` (final version with all routers)
- Create: `backend/.gitignore`

- [ ] **Step 1: Finalize main.py with all routers**

`backend/src/main.py` (final):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.chat import router as chat_router
from src.api.memory import router as memory_router
from src.api.skill_creator import router as skill_creator_router
from src.api.skills import router as skills_router
from src.api.workspace import router as workspace_router
from src.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Agent Skill Extension", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(skills_router)
app.include_router(skill_creator_router)
app.include_router(memory_router)
app.include_router(workspace_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Create backend .gitignore**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
.ruff_cache/
data/
```

- [ ] **Step 3: Create skills directories**

```bash
mkdir -p /Users/songheng/agent-skill-extension/backend/skills/{public,custom}
touch /Users/songheng/agent-skill-extension/backend/skills/public/.gitkeep
touch /Users/songheng/agent-skill-extension/backend/skills/custom/.gitkeep
mkdir -p /Users/songheng/agent-skill-extension/backend/data
```

- [ ] **Step 4: Run full test suite**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run pytest -v
```
Expected: All tests PASS

- [ ] **Step 5: Run the server smoke test**

```bash
cd /Users/songheng/agent-skill-extension/backend && PYTHONPATH=. uv run uvicorn src.main:app --port 8001 &
sleep 2
curl -s http://localhost:8001/health
curl -s http://localhost:8001/api/skills
curl -s http://localhost:8001/api/memory
kill %1
```
Expected: All return valid JSON

- [ ] **Step 6: Final commit**

```bash
cd /Users/songheng/agent-skill-extension
git add -A
git commit -m "feat: complete backend MVP with all API endpoints and tests"
```

---

## Summary

| Chunk | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-3 | Project scaffolding, config, database |
| 2 | 4-7 | Workspace manager, memory system |
| 3 | 8-9 | Skill types, loader, manager |
| 4 | 10-11 | Agent core (prompt assembly, LLM loop) |
| 5 | 12-15 | API layer (chat, skills, memory, workspace) |
| 6 | 16-17 | Skill creator, final integration |

**Total: 17 tasks, ~85 steps**

After completion, the backend will support:
- SSE streaming chat with LLM (POST /api/chat)
- Skill management (list/get/enable/install/uninstall)
- Memory system (context + facts, LLM-driven updates, prompt injection)
- Workspace isolation (per-thread file management)
- Skill creation flow (draft/install)
