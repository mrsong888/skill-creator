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
