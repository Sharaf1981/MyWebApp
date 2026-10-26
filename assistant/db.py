"""SQLite storage for tasks and notes."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("ASSISTANT_DB", os.path.join(os.path.dirname(__file__), "..", "assistant.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due_date TEXT,
    priority TEXT NOT NULL DEFAULT 'medium',
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

PRIORITIES = ("low", "medium", "high")


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


# --- Tasks ---

def list_tasks(status="all"):
    query = "SELECT * FROM tasks"
    if status == "open":
        query += " WHERE done = 0"
    elif status == "done":
        query += " WHERE done = 1"
    query += " ORDER BY done, due_date IS NULL, due_date, id"
    with connect() as conn:
        return _rows(conn.execute(query))


def add_task(title, due_date=None, priority="medium"):
    if priority not in PRIORITIES:
        priority = "medium"
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, due_date, priority) VALUES (?, ?, ?)",
            (title.strip(), due_date or None, priority),
        )
        return dict(conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone())


def set_task_done(task_id, done=True):
    with connect() as conn:
        cur = conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (1 if done else 0, task_id))
        return cur.rowcount > 0


def delete_task(task_id):
    with connect() as conn:
        return conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount > 0


# --- Notes ---

def list_notes(query=None):
    sql = "SELECT * FROM notes"
    params = ()
    if query:
        sql += " WHERE title LIKE ? OR content LIKE ?"
        params = (f"%{query}%", f"%{query}%")
    sql += " ORDER BY id DESC"
    with connect() as conn:
        return _rows(conn.execute(sql, params))


def add_note(title, content=""):
    with connect() as conn:
        cur = conn.execute("INSERT INTO notes (title, content) VALUES (?, ?)", (title.strip(), content))
        return dict(conn.execute("SELECT * FROM notes WHERE id = ?", (cur.lastrowid,)).fetchone())


def delete_note(note_id):
    with connect() as conn:
        return conn.execute("DELETE FROM notes WHERE id = ?", (note_id,)).rowcount > 0
