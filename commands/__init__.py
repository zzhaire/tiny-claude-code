from ui import print_info, print_history, GREEN, CYAN, BOLD, DIM, RESET

COMMANDS = {
    "/help":         "Show this help message",
    "/history":      "Show current context window",
    "/clear":        "Clear conversation history",
    "/compact":      "Summarise history and compress context",
    "/skills":       "List available skills",
    "/skill <name>": "Activate a skill (or /skill off to deactivate)",
    "/plan <goal>":  "Generate a plan for a goal (no args = show current plan)",
    "/solve":        "Execute the current plan",
    "/exit":         "Exit tiny-claude-code",
}


def handle_command(cmd: str, history: list, state: dict) -> bool:
    """Dispatch a slash command. Returns True if handled, False if unknown."""
    parts = cmd.strip().split()
    name = parts[0].lower()

    if name == "/help":
        print(f"\n{BOLD}Commands:{RESET}")
        for c, desc in COMMANDS.items():
            print(f"  {GREEN}{c:<20}{RESET} {desc}")
        active = state.get("active_skill")
        if active:
            print(f"\n{DIM}  active skill: {active}{RESET}")
        print()
        return True

    if name == "/history":
        print_history(history)
        return True

    if name == "/clear":
        history.clear()
        print_info("conversation cleared\n")
        return True

    if name == "/compact":
        if not history:
            print_info("nothing to compact\n")
        else:
            from agent import auto_compact
            print_info("compacting context...")
            history[:] = auto_compact(history)
        return True

    if name == "/skills":
        from context import list_skills
        skills = list_skills()
        if not skills:
            print_info("no skills found in skills/\n")
        else:
            print(f"\n{BOLD}Available skills:{RESET}")
            active = state.get("active_skill")
            for s in skills:
                marker = f" {CYAN}●{RESET}" if s["name"] == active else "  "
                print(f"{marker} {GREEN}{s['name']:<12}{RESET} {DIM}{s['description']}{RESET}")
            print()
        return True

    if name == "/skill":
        if len(parts) < 2:
            print_info("usage: /skill <name> | /skill off\n")
            return True
        arg = parts[1].lower()
        if arg == "off":
            state["active_skill"] = None
            print_info("skill deactivated\n")
        else:
            from context import load_skill
            skill = load_skill(arg)
            if skill is None:
                print_info(f"skill '{arg}' not found — use /skills to list available skills\n")
            else:
                state["active_skill"] = arg
                print_info(f"skill '{arg}' activated: {skill['description']}\n")
        return True

    if name == "/plan":
        from plan import create_plan, display_plan
        goal = " ".join(parts[1:]).strip()
        if not goal:
            current = state.get("plan")
            if current is None:
                print_info("no active plan — use /plan <goal> to create one\n")
            else:
                display_plan(current)
        else:
            print_info(f"generating plan for: {goal}\n")
            p = create_plan(goal)
            if p is None:
                print_info("failed to generate plan (API error)\n")
            else:
                state["plan"] = p
                display_plan(p)
        return True

    if name == "/solve":
        from plan import execute_plan, display_plan
        current = state.get("plan")
        if current is None:
            print_info("no active plan — use /plan <goal> to create one first\n")
        else:
            state["plan"] = execute_plan(current, history)
        return True

    if name in ("/exit", "/quit"):
        raise SystemExit(0)

    return False
