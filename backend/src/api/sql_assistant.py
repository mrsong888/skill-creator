import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.sql_assistant.connectors import create_connector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sql", tags=["sql"])


class TestConnectionRequest(BaseModel):
    engine: str
    host: str
    port: int
    username: str = "default"
    password: str = ""
    database: str = "default"


@router.post("/test-connection")
async def test_connection(req: TestConnectionRequest):
    try:
        connector = create_connector(req.engine, req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ok, msg = connector.test_connection()
    if ok:
        try:
            tables = connector.list_tables()
            return {"status": "ok", "message": msg, "tables": tables, "table_count": len(tables)}
        except Exception as e:
            return {"status": "ok", "message": msg, "tables": [], "table_count": 0, "warning": str(e)}
    else:
        return {"status": "error", "message": msg}
