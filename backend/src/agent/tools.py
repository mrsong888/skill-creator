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
