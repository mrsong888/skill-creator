import json
from pathlib import Path

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


def _safe_resolve(base: Path, user_path: str) -> Path | None:
    """Resolve a user-provided path and ensure it stays within the base directory."""
    try:
        resolved = (base / user_path).resolve()
        base_resolved = base.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            return None
        return resolved
    except (ValueError, OSError):
        return None


async def execute_tool(name: str, arguments: dict, workspace_root: Path | None = None) -> str:
    """Execute a built-in tool and return the result as a string."""
    if workspace_root is None:
        return "Error: No workspace available. File operations require an active workspace."

    base = workspace_root

    if name == "read_file":
        path = _safe_resolve(base, arguments["path"])
        if path is None:
            return "Error: Access denied. You can only access files within your workspace."
        if not path.exists():
            return f"Error: File not found: {arguments['path']}"
        return path.read_text(encoding="utf-8")

    elif name == "write_file":
        path = _safe_resolve(base, arguments["path"])
        if path is None:
            return "Error: Access denied. You can only write files within your workspace."
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(arguments["content"], encoding="utf-8")
        return f"Written to {arguments['path']}"

    elif name == "list_files":
        path = _safe_resolve(base, arguments["path"])
        if path is None:
            return "Error: Access denied. You can only list files within your workspace."
        if not path.exists():
            return f"Error: Directory not found: {arguments['path']}"
        entries = []
        for entry in sorted(path.iterdir()):
            prefix = "[dir]" if entry.is_dir() else "[file]"
            entries.append(f"{prefix} {entry.name}")
        return "\n".join(entries) or "(empty directory)"

    return f"Error: Unknown tool: {name}"
