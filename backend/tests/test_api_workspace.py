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


async def test_list_workspace_files_empty(client, temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    with patch("src.api.workspace.get_workspace_manager", return_value=wm):
        response = await client.get("/api/workspace/nonexistent/files")
    assert response.status_code == 200
    assert response.json() == []


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
    assert response.json()["size"] == 12


async def test_download_file(client, temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    dirs = wm.ensure_thread_dirs("thread-1")
    (dirs["workspace"] / "hello.txt").write_text("hello world")

    with patch("src.api.workspace.get_workspace_manager", return_value=wm):
        response = await client.get("/api/workspace/thread-1/file?path=workspace/hello.txt")
    assert response.status_code == 200


async def test_download_file_not_found(client, temp_dir):
    wm = WorkspaceManager(base_path=temp_dir)
    with patch("src.api.workspace.get_workspace_manager", return_value=wm):
        response = await client.get("/api/workspace/thread-1/file?path=nope.txt")
    assert response.status_code == 404
