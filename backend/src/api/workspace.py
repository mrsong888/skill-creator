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
