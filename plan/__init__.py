"""Planning and solving system: DAG-based task tracking with tree display."""

import io
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from dotenv import load_dotenv
load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

from anthropic import Anthropic
from config import MODEL

CYAN   = "\033[36m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

STATUS_ICON = {
    "pending": f"{DIM}○{RESET}",
    "running": f"{YELLOW}▶{RESET}",
    "done":    f"{GREEN}✓{RESET}",
    "failed":  f"{RED}✗{RESET}",
}

_PLAN_PROMPT = """\
You are a planning assistant. Break the given goal into concrete, atomic tasks.
Return ONLY valid JSON — no markdown fences, no explanation:

{
  "tasks": [
    {"id": "t1", "description": "...", "depends_on": []},
    {"id": "t2", "description": "...", "depends_on": ["t1"]},
    ...
  ]
}

Rules:
- ids must be short strings: t1, t2, t3 ...
- depends_on lists ids of tasks that must finish before this one starts
- 3-8 tasks is ideal; keep each task atomic (one focused coding step)
- The dependency graph must be a DAG (no cycles)
"""


@dataclass
class Task:
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"   # pending | running | done | failed
    error: str = ""


@dataclass
class Plan:
    goal: str
    tasks: list[Task]
    attempt: int = 1
    max_attempts: int = 4

    def get(self, task_id: str) -> "Task | None":
        return next((t for t in self.tasks if t.id == task_id), None)

    def ready(self) -> list["Task"]:
        done_ids = {t.id for t in self.tasks if t.status == "done"}
        return [
            t for t in self.tasks
            if t.status == "pending"
            and all(dep in done_ids for dep in t.depends_on)
        ]

    def is_complete(self) -> bool:
        return all(t.status == "done" for t in self.tasks)

    def has_failures(self) -> bool:
        return any(t.status == "failed" for t in self.tasks)

    def failed_tasks(self) -> list["Task"]:
        return [t for t in self.tasks if t.status == "failed"]

    def _progress(self) -> str:
        done = sum(1 for t in self.tasks if t.status == "done")
        return f"{done}/{len(self.tasks)} done"


def _client() -> Anthropic:
    return Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))


def _parse_tasks(text: str) -> list[Task]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(m.group()) if m else {}
    return [
        Task(
            id=t["id"],
            description=t["description"],
            depends_on=t.get("depends_on", []),
        )
        for t in data.get("tasks", [])
    ]


def _ask_model(user_content: str) -> str:
    """Call the model with the plan prompt embedded in the user message.

    Uses streaming (same transport as the agent) to stay compatible with proxies
    that reject non-streaming or system-parameter requests.
    Returns the text response, or "" on error.
    """
    message = f"{_PLAN_PROMPT}\n\n{user_content}"
    try:
        with _client().messages.stream(
            model=MODEL,
            messages=[{"role": "user", "content": message}],
            max_tokens=1500,
        ) as stream:
            return stream.get_final_message().content[0].text
    except Exception as e:
        print(f"{RED}[plan API error: {e}]{RESET}")
        return ""


def create_plan(goal: str) -> "Plan | None":
    text = _ask_model(f"Goal: {goal}")
    if not text:
        return None
    return Plan(goal=goal, tasks=_parse_tasks(text))


def replan(old: "Plan", failure_context: str) -> "Plan | None":
    failed_desc = "\n".join(
        f"  - {t.description}: {t.error}" for t in old.failed_tasks()
    )
    user_content = (
        f"Original goal: {old.goal}\n\n"
        f"Attempt {old.attempt} failed.\n"
        f"Failed tasks:\n{failed_desc}\n\n"
        f"Failure details: {failure_context}\n\n"
        "Create a completely new plan to achieve the original goal, "
        "avoiding the above failures."
    )
    text = _ask_model(user_content)
    if not text:
        return None
    return Plan(
        goal=old.goal,
        tasks=_parse_tasks(text),
        attempt=old.attempt + 1,
        max_attempts=old.max_attempts,
    )


def display_plan(plan: Plan) -> None:
    attempt_info = f"{DIM}[attempt {plan.attempt}/{plan.max_attempts}]{RESET}"
    progress = f"{DIM}{plan._progress()}{RESET}"
    print(f"\n{BOLD}Plan:{RESET} {CYAN}{plan.goal}{RESET}  {attempt_info}  {progress}")

    # Build children map: which tasks depend on each task (reverse edges)
    children: dict[str, list[str]] = {t.id: [] for t in plan.tasks}
    for t in plan.tasks:
        for dep in t.depends_on:
            if dep in children:
                children[dep].append(t.id)

    roots = [t for t in plan.tasks if not t.depends_on]
    visited: set[str] = set()

    def _draw(tid: str, prefix: str, is_last: bool) -> None:
        task = plan.get(tid)
        if task is None:
            return
        connector = "└─" if is_last else "├─"
        icon = STATUS_ICON.get(task.status, "○")

        if tid in visited:
            label = f"{DIM}{task.description}  (↑ already shown){RESET}"
            print(f"{DIM}{prefix}{connector}{RESET} {icon} {DIM}{tid}{RESET}  {label}")
            return

        label = task.description
        if task.status == "failed" and task.error:
            label += f"  {RED}{DIM}{task.error[:60]}{RESET}"

        print(f"{DIM}{prefix}{connector}{RESET} {icon} {DIM}{tid}{RESET}  {label}")
        visited.add(tid)

        kids = children.get(tid, [])
        child_prefix = prefix + ("   " if is_last else "│  ")
        for i, kid in enumerate(kids):
            _draw(kid, child_prefix, i == len(kids) - 1)

    print(f"{DIM}│{RESET}")
    for i, root in enumerate(roots):
        _draw(root.id, "", i == len(roots) - 1)
    print()


# ── Thread-local stdout capture ───────────────────────────────────────────────

_tls = threading.local()


class _PerThreadCapture:
    """Replaces sys.stdout so each thread's writes go to its own StringIO.

    The main thread (no buffer installed) still writes to the real stdout.
    """

    def __init__(self, real):
        self._real = real

    def _target(self):
        buf = getattr(_tls, "buf", None)
        return buf if buf is not None else self._real

    def write(self, s: str) -> int:
        return self._target().write(s)

    def flush(self) -> None:
        self._target().flush()

    @staticmethod
    def start() -> None:
        _tls.buf = io.StringIO()

    @staticmethod
    def collect() -> str:
        text = getattr(_tls, "buf", io.StringIO()).getvalue()
        _tls.buf = None
        return text


# ── Subagent runner ───────────────────────────────────────────────────────────

def _run_task(task: Task, history_snapshot: list) -> tuple[Task, str, str]:
    """Run one task in an isolated agent session.

    Returns (task, last_assistant_text, captured_stdout).
    Modifies task.status in place.
    """
    from agent import agent_loop

    _PerThreadCapture.start()
    try:
        local_history = list(history_snapshot)
        local_history.append({
            "role": "user",
            "content": (
                f"[Task {task.id}] {task.description}\n"
                "Complete this task fully. When done, briefly confirm what was accomplished."
            ),
        })
        _, usage = agent_loop(local_history)

        if usage and usage.get("input_tokens", 0) > 0:
            task.status = "done"
            last_reply = next(
                (m["content"] for m in reversed(local_history) if m["role"] == "assistant"),
                "(no output)",
            )
        else:
            task.status = "failed"
            task.error = "agent returned no response"
            last_reply = task.error
    except Exception as e:
        task.status = "failed"
        task.error = str(e)[:120]
        last_reply = task.error
    finally:
        captured = _PerThreadCapture.collect()

    return task, last_reply, captured


# ── Batch summary ─────────────────────────────────────────────────────────────

def _summarize_batch(results: list[tuple[Task, str]], goal: str) -> str:
    """Ask the model for a 2-3 sentence summary of what a parallel batch accomplished."""
    parts = [
        f"[{'done' if t.status == 'done' else 'FAILED'}] {t.id}: {t.description}\n{reply[:400]}"
        for t, reply in results
    ]
    prompt = (
        f"Goal: {goal}\n\n"
        "The following tasks just completed in parallel:\n\n"
        + "\n\n".join(parts)
        + "\n\nWrite a concise 2-3 sentence summary of what was accomplished."
    )
    text = _ask_model(prompt)
    if text:
        return text
    # Fallback: plain list
    return "\n".join(
        f"- {t.id} ({'done' if t.status == 'done' else 'FAILED'}): {t.description}"
        for t, _ in results
    )


# ── Execution ─────────────────────────────────────────────────────────────────

def execute_plan(plan: Plan, history: list) -> Plan:
    """Execute plan tasks in parallel batches determined by the DAG.

    Each batch = all currently-ready tasks (no pending dependencies).
    Subagents run in threads with isolated history copies so the main
    history stays clean. Only a brief summary per batch is appended.
    """
    real_stdout = sys.stdout
    capture = _PerThreadCapture(real_stdout)
    sys.stdout = capture

    try:
        plan = _execute_loop(plan, history)
    finally:
        sys.stdout = real_stdout

    return plan


def _execute_loop(plan: Plan, history: list) -> Plan:
    from agent import agent_loop  # noqa: F401 (imported for type checking)

    while True:
        if plan.is_complete():
            print(f"{GREEN}✓ Plan complete!{RESET}\n")
            break

        ready = plan.ready()

        if not ready:
            if plan.has_failures():
                if plan.attempt >= plan.max_attempts:
                    failed = ", ".join(t.id for t in plan.failed_tasks())
                    print(f"{RED}✗ Max attempts ({plan.max_attempts}) reached. "
                          f"Failed: {failed}{RESET}\n")
                    break
                failure_ctx = "\n".join(
                    f"{t.id}: {t.description} — {t.error}"
                    for t in plan.failed_tasks()
                )
                print(f"{YELLOW}⚠ Replanning "
                      f"(attempt {plan.attempt + 1}/{plan.max_attempts})...{RESET}\n")
                new_plan = replan(plan, failure_ctx)
                if new_plan is None:
                    print(f"{RED}✗ Replanning failed (API error). Stopping.{RESET}\n")
                    break
                plan = new_plan
                display_plan(plan)
                continue
            break

        # Mark batch as running and announce
        for task in ready:
            task.status = "running"
        display_plan(plan)

        if len(ready) == 1:
            print(f"{YELLOW}▶ {ready[0].id}:{RESET} {ready[0].description}\n")
        else:
            ids = "  ".join(
                f"{YELLOW}{t.id}{RESET}" for t in ready
            )
            print(f"{YELLOW}▶ Running in parallel:{RESET} {ids}\n")

        # Snapshot history for subagents — they work on isolated copies
        history_snapshot = list(history)

        # Execute batch in parallel threads
        batch_results: list[tuple[Task, str]] = []
        with ThreadPoolExecutor(max_workers=len(ready)) as pool:
            futures = {pool.submit(_run_task, t, history_snapshot): t for t in ready}
            for fut in as_completed(futures):
                task, last_reply, captured = fut.result()
                # Print each subagent's captured output sequentially (no interleaving)
                if captured.strip():
                    print(f"{DIM}── {task.id} ──────────────────────────{RESET}")
                    print(captured.rstrip())
                    print(f"{DIM}────────────────────────────────────{RESET}\n")
                batch_results.append((task, last_reply))

        # Generate summary and append ONE message to main history
        summary = _summarize_batch(batch_results, plan.goal)
        history.append({"role": "assistant", "content": f"[Batch summary]\n{summary}"})
        print(f"\n{DIM}Batch summary:{RESET} {summary}\n")

        display_plan(plan)

    return plan
