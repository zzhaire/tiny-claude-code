import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

from config import MODEL, WORKDIR, MAX_TOKENS
from tools import TOOLS, TOOL_HANDLERS
from ui import print_tool_call, print_tool_result

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
SYSTEM = (
    f"You are a coding assistant. Current working directory: {WORKDIR}. "
    "Always use RELATIVE paths (e.g. 'hello.py', 'src/main.py'). "
    "Use tools to read, write, and run code. Act directly, don't explain unless asked."
)


def _serialize(content) -> list:
    """Convert Pydantic SDK objects to plain dicts so any API proxy can handle them."""
    result = []
    for block in content:
        if hasattr(block, "model_dump"):
            result.append(block.model_dump())
        else:
            result.append(block)
    return result


def agent_loop(messages: list) -> tuple[str, dict | None]:
    usage = {"input_tokens": 0, "output_tokens": 0}

    while True:
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
                final = stream.get_final_message()
        except Exception as e:
            print(f"\n[API error: {e}]")
            break

        messages.append({"role": "assistant", "content": _serialize(final.content)})
        usage["input_tokens"] += final.usage.input_tokens
        usage["output_tokens"] += final.usage.output_tokens

        if final.stop_reason != "tool_use":
            break

        results = []
        for block in final.content:
            if block.type != "tool_use":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            print_tool_call(block.name, block.input)
            output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
            print_tool_result(output)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        messages.append({"role": "user", "content": results})

    return "", usage
