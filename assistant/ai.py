"""Claude-powered chat that can manage the user's tasks and notes through tools."""
import json
import threading
from datetime import date

import anthropic

from . import db

MODEL = "claude-opus-5-5"
MAX_TOOL_ROUNDS = 10

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "list_tasks",
        "description": "List the user's tasks. Use before completing or deleting a task to find its id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["all", "open", "done"], "description": "Filter by status (default: all)"},
            },
        },
    },
    {
        "name": "add_task",
        "description": "Create a new task or reminder for the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short description of the task"},
                "due_date": {"type": "string", "description": "Due date as YYYY-MM-DD, if the user gave one"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["title"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as done (or reopen it with done=false).",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "done": {"type": "boolean", "description": "Default true"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "delete_task",
        "description": "Permanently delete a task.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "list_notes",
        "description": "List the user's notes, optionally filtered by a search term.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Text to search for in title or content"}},
        },
    },
    {
        "name": "add_note",
        "description": "Save a note for the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "delete_note",
        "description": "Permanently delete a note.",
        "input_schema": {
            "type": "object",
            "properties": {"note_id": {"type": "integer"}},
            "required": ["note_id"],
        },
    },
]

SYSTEM_PROMPT = """You are a friendly personal assistant inside a small productivity app.
You can manage the user's tasks and notes with the tools provided, and you can also answer general questions, write, translate and summarize.

- Reply in the same language the user writes in (Arabic, including Egyptian dialect, or English).
- When the user asks to remember, add, finish or remove something, use the tools rather than only describing it.
- Look up ids with list_tasks / list_notes instead of guessing them.
- Keep replies short and clear. Confirm what you changed.
Today's date is {today}."""


class ToolInputError(ValueError):
    pass


def _require(inp, key, kind):
    value = inp.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) and kind is int:
        raise ToolInputError(f"'{key}' is required and must be {kind.__name__}")
    return value


def run_tool(name, inp):
    if name == "list_tasks":
        return db.list_tasks(inp.get("status", "all"))
    if name == "add_task":
        return db.add_task(_require(inp, "title", str), inp.get("due_date"), inp.get("priority", "medium"))
    if name == "complete_task":
        ok = db.set_task_done(_require(inp, "task_id", int), inp.get("done", True))
        return {"ok": ok}
    if name == "delete_task":
        return {"ok": db.delete_task(_require(inp, "task_id", int))}
    if name == "list_notes":
        return db.list_notes(inp.get("query"))
    if name == "add_note":
        return db.add_note(_require(inp, "title", str), inp.get("content", ""))
    if name == "delete_note":
        return {"ok": db.delete_note(_require(inp, "note_id", int))}
    raise ToolInputError(f"Unknown tool: {name}")


# In-memory conversation history, keyed by conversation id. Assistant content is
# stored exactly as returned so thinking blocks are replayed unchanged.
_conversations = {}
_lock = threading.Lock()


def reset(conversation_id):
    with _lock:
        _conversations.pop(conversation_id, None)


def chat(conversation_id, user_text):
    """Send a user message, run any tool calls, and return (reply_text, data_changed)."""
    with _lock:
        history = list(_conversations.get(conversation_id, []))

    # Work on a copy and only commit it once the turn finishes, so a failed or
    # refused turn leaves the stored history untouched.
    messages = history + [{"role": "user", "content": user_text}]
    changed = False

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM_PROMPT.format(today=date.today().isoformat()),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "refusal":
            return ("عذرًا، لا أستطيع المساعدة في هذا الطلب. / Sorry, I can't help with that request.", changed)

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                output = run_tool(block.name, block.input)
                if not block.name.startswith("list_"):
                    changed = True
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output, ensure_ascii=False)})
            except ToolInputError as e:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    else:
        # Tool-round limit hit while the last message is tool results; don't
        # commit a history that ends without an assistant reply.
        return ("توقفت بعد خطوات كثيرة. حاول مرة أخرى. / Stopped after too many steps, please try again.", changed)

    with _lock:
        _conversations[conversation_id] = messages

    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return (text or "✓", changed)
