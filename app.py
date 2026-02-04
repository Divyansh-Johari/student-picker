import sqlite3
import random
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
DB_NAME = "students.db"

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Enable WAL for concurrency
    cur.execute("PRAGMA journal_mode=WAL;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            is_selected INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS selection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            selected_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/add_student", methods=["POST"])
def add_student():
    name = request.json.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name required"}), 400

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO students (name) VALUES (?)",
            (name,)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Registered successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Name already registered"}), 400

@app.route("/pick_student")
def pick_student():
    conn = get_db()
    students = conn.execute(
        "SELECT id, name FROM students WHERE is_selected = 0"
    ).fetchall()

    if not students:
        conn.close()
        return jsonify({"message": "All students selected"})

    chosen = random.choice(students)

    conn.execute(
        "UPDATE students SET is_selected = 1 WHERE id = ?",
        (chosen["id"],)
    )
    conn.execute(
        "INSERT INTO selection_log (name) VALUES (?)",
        (chosen["name"],)
    )

    conn.commit()
    conn.close()

    return jsonify({"selected": chosen["name"]})

@app.route("/report")
def report():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, selected_at FROM selection_log ORDER BY selected_at"
    ).fetchall()
    conn.close()

    return jsonify([
        {"name": r["name"], "time": r["selected_at"]}
        for r in rows
    ])

@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    conn.execute("UPDATE students SET is_selected = 0")
    conn.execute("DELETE FROM selection_log")
    conn.commit()
    conn.close()
    return jsonify({"message": "Session reset"})
