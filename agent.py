import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

from config import MODEL, WORKDIR, MAX_TOKENS

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
SYSTEM = f"You are a coding assistant working in {WORKDIR}. Help with tasks concisely and directly."


def agent_loop(messages: list) -> tuple[str, dict | None]:
    usage = {"input_tokens": 0, "output_tokens": 0}

    while True:
        with client.messages.stream(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            max_tokens=MAX_TOKENS,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
            print()
            final = stream.get_final_message()

        messages.append({"role": "assistant", "content": final.content})
        usage["input_tokens"] += final.usage.input_tokens
        usage["output_tokens"] += final.usage.output_tokens

        if final.stop_reason != "tool_use":
            break

        # Tool execution — Step 3

    return "", usage
