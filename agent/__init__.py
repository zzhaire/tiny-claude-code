import json
import os
import time
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

from config import MODEL, WORKDIR, MAX_TOKENS, TOKEN_THRESHOLD, TRANSCRIPT_DIR
from tools import TOOLS, TOOL_HANDLERS
from ui import print_tool_call, print_tool_result, print_tool_denied, print_info
from permissions import is_allowed

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
SYSTEM = (
    f"You are a coding assistant. Current working directory: {WORKDIR}. "
    "Always use RELATIVE paths (e.g. 'hello.py', 'src/main.py'). "
    "Use tools to read, write, and run code. Act directly, don't explain unless asked."
)


def _serialize(content) -> list:
    """Normalize content blocks to the minimal API spec fields.

    Strips Pydantic metadata and any extra fields that some proxy APIs reject.
    """
    result = []
    for block in content:
        raw = block.model_dump() if hasattr(block, "model_dump") else block
        t = raw.get("type")
        if t == "text":
            result.append({"type": "text", "text": raw["text"]})
        elif t == "tool_use":
            result.append({
                "type": "tool_use",
                "id": raw["id"],
                "name": raw["name"],
                "input": raw["input"],
            })
        # skip unknown block types (e.g. thinking blocks from extended thinking)
    return result


def estimate_tokens(messages: list) -> int:
    """Rough estimate: ~4 chars per token."""
    return len(str(messages)) // 4


def auto_compact(messages: list) -> list:
    """Layer 2/3: save transcript to disk, summarise with LLM, return compressed history."""
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")

    full_text = json.dumps(messages, default=str)
    summary = ""

    # Try with progressively shorter text if the proxy rejects the request
    for char_limit in (80_000, 20_000, 5_000):
        text = full_text[-char_limit:]
        try:
            response = client.messages.create(
                model=MODEL,
                messages=[{"role": "user", "content": (
                    "Summarize this conversation for continuity. Include: "
                    "1) What was accomplished, 2) Current state of files/code, "
                    "3) Key decisions made. Be concise but preserve critical details.\n\n"
                    + text
                )}],
                max_tokens=2000,
            )
            summary = next((b.text for b in response.content if hasattr(b, "text")), "")
            break
        except Exception:
            continue

    if summary:
        print_info(f"compacted → {path}\n")
        content = f"[Context compacted. Transcript: {path}]\n\n{summary}"
    else:
        # Fallback: no LLM summary — keep just the last assistant reply as context
        print_info(f"compacted (fallback, no summary) → {path}\n")
        last_assistant = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "assistant"), ""
        )
        content = (
            f"[Context compacted. Transcript: {path}. Summary unavailable.]\n\n"
            f"Last assistant response:\n{str(last_assistant)[-2000:]}"
        )

    return [{"role": "user", "content": content}]


def _call(messages: list) -> object | None:
    """Stream one API turn. Returns final message or None on unrecoverable error.

    On a 400 (proxy context/turn limit) with enough history, compact and retry
    once automatically so the user never has to intervene.
    """
    # Remember the last user message so we can re-attach it after a compact
    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)

    for attempt in range(2):
        try:
            with client.messages.stream(
                model=MODEL,
                system=SYSTEM,
                messages=messages,
                tools=TOOLS,
                max_tokens=MAX_TOKENS,
            ) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                print()
                return stream.get_final_message()

        except Exception as e:
            is_400 = "400" in str(e)
            has_history = len(messages) > 1   # more than just the current question

            if attempt == 0 and is_400 and has_history:
                # Proxy hit its turn/context limit — compact and retry once
                print_info("proxy limit reached, compacting context and retrying...")
                messages[:] = auto_compact(messages)
                # Re-attach the question that triggered this call
                if last_user and (not messages or messages[-1] != last_user):
                    messages.append(last_user)
            else:
                print(f"\n[API error: {e}]")
                return None

    return None   # should be unreachable


def agent_loop(messages: list) -> tuple[str, dict | None]:
    """Run the agent loop until the model stops calling tools.

    Messages are stored as plain strings (never tool_use / tool_result blocks)
    so the history is compatible with any proxy.  On 400 errors we compact
    and retry automatically.
    """
    usage = {"input_tokens": 0, "output_tokens": 0}

    while True:
        # Layer 2: proactive auto-compact before hitting proxy limit
        if estimate_tokens(messages) > TOKEN_THRESHOLD:
            print_info("context too large — auto-compacting...")
            messages[:] = auto_compact(messages)

        final = _call(messages)
        if final is None:
            break

        usage["input_tokens"] += final.usage.input_tokens
        usage["output_tokens"] += final.usage.output_tokens

        blocks = _serialize(final.content)
        text_parts = [b["text"] for b in blocks if b.get("type") == "text"]
        tool_blocks = [b for b in blocks if b.get("type") == "tool_use"]

        if final.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": "\n".join(text_parts)})
            break

        # ── Tool-use turn ──────────────────────────────────────────────────
        call_desc = ", ".join(
            f"{b['name']}({b['input'].get('command') or b['input'].get('path', '')})"
            for b in tool_blocks
        )
        assistant_text = "\n".join(text_parts)
        assistant_text += f"\n[Calling: {call_desc}]" if assistant_text else f"[Calling: {call_desc}]"
        messages.append({"role": "assistant", "content": assistant_text})

        result_lines = []
        for block in final.content:
            if block.type != "tool_use":
                continue
            handler = TOOL_HANDLERS.get(block.name)

            if not is_allowed(block.name, block.input):
                print_tool_denied(block.name, block.input)
                output = "Action denied by user."
            else:
                print_tool_call(block.name, block.input)
                output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                print_tool_result(output)

            result_lines.append(f"[{block.name} result]\n{output}")

        messages.append({"role": "user", "content": "\n\n".join(result_lines)})

    return "", usage
