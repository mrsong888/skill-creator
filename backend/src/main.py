from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.chat import router as chat_router
from src.api.memory import router as memory_router
from src.api.skill_creator import router as skill_creator_router
from src.api.skill_templates import router as skill_templates_router
from src.api.skill_chat import router as skill_chat_router
from src.api.skills import router as skills_router
from src.api.sql_assistant import router as sql_assistant_router
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
app.include_router(skill_chat_router)
app.include_router(skill_creator_router)
app.include_router(skill_templates_router)
app.include_router(memory_router)
app.include_router(sql_assistant_router)
app.include_router(workspace_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
