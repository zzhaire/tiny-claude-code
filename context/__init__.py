"""User input pre-processing: @file references, skill loading, plan injection."""

import re
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent.parent / "skills"


def list_skills() -> list[dict]:
    """Scan skills/ directory and return [{name, description}]."""
    result = []
    if not _SKILLS_DIR.exists():
        return result
    for f in sorted(_SKILLS_DIR.glob("*.md")):
        name = f.stem
        description = ""
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
            in_front = False
            for line in lines:
                if line.strip() == "---":
                    if not in_front:
                        in_front = True
                        continue
                    else:
                        break
                if in_front and line.startswith("description:"):
                    description = line[len("description:"):].strip()
        except OSError:
            pass
        result.append({"name": name, "description": description})
    return result


def load_skill(name: str) -> dict | None:
    """Load a skill by name. Returns {name, description, prompt} or None."""
    path = _SKILLS_DIR / f"{name}.md"
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = text.splitlines()
    meta = {"name": name, "description": ""}
    body_lines = []
    in_front = False
    front_done = False
    for line in lines:
        if not front_done:
            if line.strip() == "---":
                if not in_front:
                    in_front = True
                    continue
                else:
                    front_done = True
                    continue
            if in_front:
                if line.startswith("name:"):
                    meta["name"] = line[len("name:"):].strip()
                elif line.startswith("description:"):
                    meta["description"] = line[len("description:"):].strip()
        else:
            body_lines.append(line)

    meta["prompt"] = "\n".join(body_lines).strip()
    return meta

# Match @path — stops at whitespace, comma, or closing punctuation
_AT_RE = re.compile(r"@([\w./\\-]+)")

_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "tsx",   ".jsx": "jsx",       ".java": "java",
    ".cpp": "cpp",   ".c": "c",           ".h": "c",
    ".go": "go",     ".rs": "rust",       ".rb": "ruby",
    ".sh": "bash",   ".zsh": "bash",      ".md": "markdown",
    ".json": "json", ".yaml": "yaml",     ".yml": "yaml",
    ".toml": "toml", ".sql": "sql",       ".html": "html",
    ".css": "css",
}


def _lang(path: str) -> str:
    return _LANG_MAP.get(Path(path).suffix.lower(), "")


def resolve_at_refs(text: str) -> tuple[str, list[str]]:
    """Expand every @path in text by appending the file content.

    Returns:
        (expanded_text, loaded_paths)  — loaded_paths is empty if nothing matched.
    """
    matches = _AT_RE.findall(text)
    if not matches:
        return text, []

    loaded: list[str] = []
    appended: list[str] = []

    for path_str in dict.fromkeys(matches):   # preserve order, deduplicate
        fp = (Path.cwd() / path_str).resolve()
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue                           # skip missing files silently

        lang = _lang(path_str)
        appended.append(f"\n[File: {path_str}]\n```{lang}\n{content}\n```")
        loaded.append(path_str)

    if not appended:
        return text, []

    return text + "\n" + "\n".join(appended), loaded
