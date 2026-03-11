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
