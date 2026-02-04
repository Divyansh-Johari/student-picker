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

    # Enable WAL mode for better concurrency
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

# ---- Student Registration ----
@app.route("/add_student", methods=["POST"])
def add_student():
    name = request.json.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400

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

# ---- Pick Random Student ----
@app.route("/pick_student")
def pick_student():
    conn = get_db()
    students = conn.execute(
        "SELECT id, name FROM students WHERE is_selected = 0"
    ).fetchall()

    if not students:
        conn.close()
        return jsonify({"message": "All students have been selected"})

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

# ---- Live Student List (Admin) ----
@app.route("/students")
def students():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, is_selected FROM students ORDER BY name"
    ).fetchall()
    conn.close()

    return jsonify([
        {
            "name": row["name"],
            "is_selected": bool(row["is_selected"])
        }
        for row in rows
    ])

# ---- Selection Report ----
@app.route("/report")
def report():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, selected_at FROM selection_log ORDER BY selected_at"
    ).fetchall()
    conn.close()

    return jsonify([
        {
            "name": row["name"],
            "time": row["selected_at"]
        }
        for row in rows
    ])

# ---- Reset Session ----
@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    conn.execute("DELETE FROM students")
    conn.execute("DELETE FROM selection_log")
    conn.commit()
    conn.close()

    return jsonify({"message": "New session started"})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
