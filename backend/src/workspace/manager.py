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
