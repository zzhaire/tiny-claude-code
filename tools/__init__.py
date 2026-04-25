from .bash import run_bash
from .filesystem import (
    run_read, run_write, run_edit, run_delete,
    run_list, run_mkdir, run_cd, run_cwd,
)

TOOL_HANDLERS = {
    "bash":        lambda **kw: run_bash(kw["command"]),
    "read_file":   lambda **kw: run_read(kw["path"], kw.get("limit"), kw.get("offset", 0)),
    "write_file":  lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":   lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "delete":      lambda **kw: run_delete(kw["path"]),
    "list_dir":    lambda **kw: run_list(kw.get("path", ".")),
    "make_dir":    lambda **kw: run_mkdir(kw["path"]),
    "change_dir":  lambda **kw: run_cd(kw["path"]),
    "get_cwd":     lambda **kw: run_cwd(),
}

TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command in the current working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents with line numbers. Supports offset and limit for large files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "offset": {"type": "integer", "description": "Start from this line (0-indexed)"},
                "limit":  {"type": "integer", "description": "Max number of lines to return"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a file. Creates parent directories as needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path":    {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace the first occurrence of exact text in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path":     {"type": "string"},
                "old_text": {"type": "string", "description": "Exact text to find (must be unique)"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "delete",
        "description": "Delete a file or directory (recursive for directories).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_dir",
        "description": "List directory contents showing file sizes. Directories shown first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path (default: current directory)"},
            },
        },
    },
    {
        "name": "make_dir",
        "description": "Create a directory and any missing parent directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "change_dir",
        "description": "Change the current working directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_cwd",
        "description": "Get the current working directory path.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]
