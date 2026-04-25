import os
import platform
import subprocess

# Detected once at startup, never changes during the session
OS = platform.system()   # "Darwin" | "Linux" | "Windows"

DANGEROUS = [
    "rm -rf /",
    "sudo rm",
    "shutdown",
    "reboot",
    "> /dev/",
    "dd if=",
    "mkfs",
    ":(){ :|:& };:",  # fork bomb
    "format c:",       # Windows disk format
    "del /f /s /q",   # Windows recursive force-delete
]


def _run(command: str) -> subprocess.CompletedProcess:
    """Invoke the right shell for the current OS."""
    cwd = os.getcwd()
    common = dict(capture_output=True, text=True, timeout=120, cwd=cwd)

    if OS == "Windows":
        # PowerShell gives us utf-8 and modern cmdlets (Get-ChildItem etc.)
        return subprocess.run(
            ["powershell", "-NonInteractive", "-Command", command],
            **common,
        )
    elif OS == "Darwin":
        return subprocess.run(command, shell=True, executable="/bin/zsh", **common)
    else:
        # Linux and anything else
        return subprocess.run(command, shell=True, executable="/bin/bash", **common)


def run_bash(command: str) -> str:
    if any(d in command for d in DANGEROUS):
        return "Error: Dangerous command blocked"
    try:
        r = _run(command)
        out = (r.stdout + r.stderr).strip()
        return out[:50_000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except OSError as e:
        return f"Error: {e}"
