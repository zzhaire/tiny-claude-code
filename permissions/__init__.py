from ui import YELLOW, DIM, RESET, RED, GREEN, _rl

# Tools that are read-only — never need a prompt
AUTO_APPROVED = {"read_file", "list_dir", "get_cwd"}

# Session whitelist: tool names approved with "always" (covers all calls of that tool)
_whitelist: set[str] = set()


def _key(args: dict) -> str:
    """Display hint: the main argument of a tool call."""
    return args.get("command") or args.get("path") or ""


def is_allowed(tool_name: str, args: dict) -> bool:
    """Return True if this tool call may proceed.

    Auto-approves read-only tools and whitelist hits.
    Everything else prompts the user once.
    """
    if tool_name in AUTO_APPROVED:
        return True

    if tool_name in _whitelist:
        key = _key(args)
        print(f"\n{GREEN}✓ {tool_name}{RESET}  {DIM}{key}  (always allowed){RESET}")
        return True

    key = _key(args)
    # Pass both lines to input() so readline tracks cursor on the prompt line.
    # \001...\002 marks invisible bytes so readline width calculation stays correct.
    info   = f"\n{YELLOW}⚠ {tool_name}{RESET}  {DIM}{key}{RESET}"
    prompt = f"  {_rl(DIM)}Allow? [y]es / [n]o / [a]lways: {_rl(RESET)}"

    try:
        answer = input(f"{info}\n{prompt}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if answer == "a":
        _whitelist.add(tool_name)   # whitelist the whole tool, not one specific call
        return True

    return answer in ("y", "yes")


def clear_whitelist() -> None:
    _whitelist.clear()
