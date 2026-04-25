import os
import shutil
import platform
from pathlib import Path

# Immutable workspace root — set once at startup
ROOT = Path.cwd().resolve()


def safe_path(p: str) -> Path:
    """Resolve path and ensure it stays within ROOT."""
    raw = Path(p)
    path = (raw if raw.is_absolute() else (Path.cwd() / raw)).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Path {p!r} is outside workspace {ROOT}")
    return path


def run_read(path: str, limit: int = None, offset: int = 0) -> str:
    try:
        text = safe_path(path).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if offset:
            lines = lines[offset:]
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        numbered = [f"{i + 1 + offset}\t{l}" for i, l in enumerate(lines)]
        return "\n".join(numbered)[:50_000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_delete(path: str) -> str:
    try:
        fp = safe_path(path)
        if fp.is_dir():
            shutil.rmtree(fp)
            return f"Deleted directory {path}"
        fp.unlink()
        return f"Deleted {path}"
    except Exception as e:
        return f"Error: {e}"


def run_list(path: str = ".") -> str:
    try:
        fp = safe_path(path)
        entries = sorted(fp.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        if not entries:
            return "(empty directory)"
        lines = []
        for e in entries:
            if e.is_dir():
                lines.append(f"  {e.name}/")
            else:
                size = e.stat().st_size
                lines.append(f"  {e.name:<40} {size:>10,} bytes")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def run_mkdir(path: str) -> str:
    try:
        safe_path(path).mkdir(parents=True, exist_ok=True)
        return f"Created directory {path}"
    except Exception as e:
        return f"Error: {e}"


def run_cd(path: str) -> str:
    try:
        fp = safe_path(path)
        if not fp.is_dir():
            return f"Error: Not a directory: {path}"
        os.chdir(fp)
        return f"Now in {Path.cwd()}"
    except Exception as e:
        return f"Error: {e}"


def run_cwd() -> str:
    return str(Path.cwd())
