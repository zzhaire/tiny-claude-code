CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def print_banner(model: str, workdir: str):
    print(f"\n{BOLD}tiny-claude-code{RESET} v0.1")
    print(f">{DIM}model: {model}  \n  cwd: {workdir}{RESET}")
    print(f">{DIM}type your request, or /help for commands{RESET}\n")


def prompt_symbol() -> str:
    return f"{CYAN}>> {RESET}"


def print_error(msg: str):
    print(f"{RED}error:{RESET} {msg}")


def print_info(msg: str):
    print(f"{DIM}{msg}{RESET}")


def print_token_usage(input_tok: int, output_tok: int, total_in: int, total_out: int):
    turn = f"in {input_tok:,}  out {output_tok:,}"
    total = f"Σ in {total_in:,}  out {total_out:,}"
    print(f"{DIM}  {turn}  │  {total}{RESET}\n")
