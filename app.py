"""Personal assistant web app: tasks, notes and an AI chat that manages them."""
import anthropic
from flask import Flask, jsonify, render_template, request

from assistant import ai, db

app = Flask(__name__)
db.init_db()


def _json():
    return request.get_json(silent=True) or {}


@app.get("/")
def index():
    return render_template("index.html")


# --- Tasks ---

@app.get("/api/tasks")
def get_tasks():
    return jsonify(db.list_tasks(request.args.get("status", "all")))


@app.post("/api/tasks")
def create_task():
    data = _json()
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    return jsonify(db.add_task(title, data.get("due_date"), data.get("priority", "medium"))), 201


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    if not db.set_task_done(task_id, bool(_json().get("done", True))):
        return jsonify(error="not found"), 404
    return jsonify(ok=True)


@app.delete("/api/tasks/<int:task_id>")
def remove_task(task_id):
    if not db.delete_task(task_id):
        return jsonify(error="not found"), 404
    return jsonify(ok=True)


# --- Notes ---

@app.get("/api/notes")
def get_notes():
    return jsonify(db.list_notes(request.args.get("q")))


@app.post("/api/notes")
def create_note():
    data = _json()
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    return jsonify(db.add_note(title, data.get("content", ""))), 201


@app.delete("/api/notes/<int:note_id>")
def remove_note(note_id):
    if not db.delete_note(note_id):
        return jsonify(error="not found"), 404
    return jsonify(ok=True)


# --- Chat ---

@app.post("/api/chat")
def chat():
    data = _json()
    message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id") or "default"
    if not message:
        return jsonify(error="message is required"), 400
    try:
        reply, changed = ai.chat(conversation_id, message)
    except anthropic.AuthenticationError:
        return jsonify(error="auth"), 401
    except anthropic.RateLimitError:
        return jsonify(error="rate_limit"), 429
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        app.logger.exception("Claude API error")
        return jsonify(error="api", detail=str(e)), 502
    return jsonify(reply=reply, changed=changed)


@app.post("/api/chat/reset")
def chat_reset():
    ai.reset(_json().get("conversation_id") or "default")
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
