CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def print_banner(model: str, workdir: str):
    print(f"\n {BOLD}tiny-claude-code{RESET} v0.1\n")
    print(f"{DIM} - model: {model}  \n - cwd: {workdir}{RESET}")
    print(f"{DIM} >> type your request, or /help for commands{RESET}\n")


def _rl(s: str) -> str:
    """Wrap an ANSI sequence so readline counts it as zero-width."""
    return f"\001{s}\002"


def prompt_symbol() -> str:
    # \001...\002 tells readline these bytes are invisible — fixes cursor
    # position when long input wraps to the next line
    return f"{_rl(CYAN)}>> {_rl(RESET)}"


def print_error(msg: str):
    print(f"{RED}error:{RESET} {msg}")


def print_info(msg: str):
    print(f"{DIM}{msg}{RESET}")


def print_token_usage(input_tok: int, output_tok: int, total_in: int, total_out: int):
    turn = f"-- Token count  (this message): in {input_tok:,}  out {output_tok:,}"
    total = f" Σ: in {total_in:,}  out {total_out:,} --"
    print(f"{DIM}  {turn}  │  {total}{RESET}\n")


def print_tool_call(name: str, args: dict):
    key = args.get("command") or args.get("path") or ""
    print(f"\n{YELLOW}⚙ {name}{RESET}  {DIM}{key}{RESET}")


def print_tool_result(output: str, max_len: int = 400):
    preview = output[:max_len] + ("…" if len(output) > max_len else "")
    print(f"{DIM}{preview}{RESET}")


def print_tool_denied(name: str, args: dict):
    key = args.get("command") or args.get("path") or ""
    print(f"  {RED}✗ denied{RESET}  {DIM}{name}  {key}{RESET}")


def print_loaded_files(paths: list[str]) -> None:
    from pathlib import Path
    for p in paths:
        try:
            lines = len(Path(p).read_text(encoding="utf-8", errors="replace").splitlines())
            print(f"  {GREEN}@{p}{RESET}  {DIM}{lines} lines{RESET}")
        except OSError:
            print(f"  {RED}@{p}{RESET}  {DIM}not found{RESET}")


def _render_content(content, max_len: int = 200) -> str:
    """Convert any message content shape to a readable preview string."""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            t = block.get("type", "")
            if t == "text":
                parts.append(block.get("text", ""))
            elif t == "tool_use":
                key = block.get("input", {})
                hint = key.get("command") or key.get("path") or ""
                parts.append(f"[tool: {block.get('name')}  {hint}]")
            elif t == "tool_result":
                c = block.get("content", "")
                parts.append(f"[result: {c[:80]}]")
        text = "\n".join(parts)
    else:
        text = str(content)

    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text


def print_history(messages: list) -> None:
    if not messages:
        print(f"{DIM}  (no history){RESET}\n")
        return

    width = 54
    print(f"\n{DIM}{'─' * 4} history {'─' * (width - 9)}{RESET}")

    for i, msg in enumerate(messages):
        role = msg.get("role", "?")
        label_color = CYAN if role == "user" else GREEN
        content_str = _render_content(msg.get("content", ""))

        print(f"\n{DIM}[{i}]{RESET} {label_color}{role}{RESET}")
        for line in content_str.splitlines():
            print(f"  {DIM}{line}{RESET}")

    from agent import estimate_tokens

    tokens = estimate_tokens(messages)
    footer = f"  {len(messages)} messages  ~{tokens:,} tokens  "
    print(f"\n{DIM}{'─' * 4}{footer}{'─' * max(0, width - len(footer))}{RESET}\n")
