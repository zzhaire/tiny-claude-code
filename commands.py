from ui import print_info, GREEN, BOLD, RESET

COMMANDS = {
    "/help":  "Show this help message",
    "/clear": "Clear conversation history",
    "/exit":  "Exit tiny-claude-code",
}


def handle_command(cmd: str, history: list) -> bool:
    """Dispatch a slash command. Returns True if handled, False if unknown."""
    name = cmd.strip().split()[0].lower()

    if name == "/help":
        print(f"\n{BOLD}Commands:{RESET}")
        for c, desc in COMMANDS.items():
            print(f"  {GREEN}{c:<10}{RESET} {desc}")
        print()
        return True

    if name == "/clear":
        history.clear()
        print_info("conversation cleared\n")
        return True

    if name in ("/exit", "/quit"):
        raise SystemExit(0)

    return False
