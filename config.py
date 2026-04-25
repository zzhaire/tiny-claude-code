import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

MODEL = os.environ.get("MODEL_ID", "claude-sonnet-4-6")
WORKDIR = Path.cwd()
MAX_TOKENS = 8000

# Context compression
TOKEN_THRESHOLD = 50_000          # auto-compact when estimated tokens exceed this
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
