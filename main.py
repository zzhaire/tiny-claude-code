#!/usr/bin/env python3
"""tiny-claude-code — a minimal Claude Code clone."""

import argparse
import os

try:
    import readline
    readline.parse_and_bind("set bind-tty-special-chars off")
except ImportError:
    pass


def run_repl(model: str, workdir: str):
    from ui import print_banner, prompt_symbol, print_error, print_token_usage, print_loaded_files
    from commands import handle_command
    from agent import agent_loop
    from context import resolve_at_refs

    print_banner(model, workdir)
    history = []
    state = {"active_skill": None, "plan": None}
    total_in = total_out = 0

    while True:
        try:
            user_input = input(prompt_symbol())
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.startswith("/"):
            try:
                if not handle_command(user_input, history, state):
                    print_error(f"unknown command: {user_input}\n")
            except SystemExit:
                print("bye")
                break
            continue

        user_input, loaded = resolve_at_refs(user_input)
        if loaded:
            print_loaded_files(loaded)

        # Prepend active skill prompt so the model follows the skill's instructions
        active_skill = state.get("active_skill")
        if active_skill:
            from context import load_skill
            skill = load_skill(active_skill)
            if skill and skill.get("prompt"):
                user_input = f"[Skill: {active_skill}]\n{skill['prompt']}\n\n---\n\n{user_input}"

        history.append({"role": "user", "content": user_input})
        response, usage = agent_loop(history)
        if response:
            print(response)

        if usage:
            total_in += usage["input_tokens"]
            total_out += usage["output_tokens"]
            print_token_usage(usage["input_tokens"], usage["output_tokens"], total_in, total_out)
        else:
            print()


def main():
    parser = argparse.ArgumentParser(
        prog="tiny-claude-code",
        description="A minimal Claude Code clone",
    )
    parser.add_argument("--model", help="Override model ID")
    parser.add_argument("--dir", help="Set working directory", default=".")
    args = parser.parse_args()

    # Apply overrides before any imports read env/cwd
    if args.dir != ".":
        os.chdir(args.dir)
    if args.model:
        os.environ["MODEL_ID"] = args.model

    from config import MODEL, WORKDIR
    run_repl(MODEL, str(WORKDIR))


if __name__ == "__main__":
    main()
