import os
import random
import psycopg2
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ---------------- DATABASE ----------------
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            is_selected BOOLEAN DEFAULT FALSE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS selection_log (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
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
    data = request.get_json()
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO students (name) VALUES (%s)", (name,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Registered successfully"})
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "Name already registered"}), 400
    except Exception:
        return jsonify({"error": "Server error"}), 500

@app.route("/pick_student", methods=["GET"])
def pick_student():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM students WHERE is_selected = FALSE")
    students = cur.fetchall()

    if not students:
        return jsonify({"message": "All students already selected"})

    chosen = random.choice(students)

    cur.execute(
        "UPDATE students SET is_selected = TRUE WHERE id = %s",
        (chosen[0],)
    )
    cur.execute(
        "INSERT INTO selection_log (name) VALUES (%s)",
        (chosen[1],)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"selected": chosen[1]})

@app.route("/report", methods=["GET"])
def report():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, selected_at
        FROM selection_log
        ORDER BY selected_at
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {"name": r[0], "time": r[1].strftime("%Y-%m-%d %H:%M:%S")}
        for r in rows
    ])

@app.route("/reset", methods=["POST"])
def reset():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE students SET is_selected = FALSE")
    cur.execute("DELETE FROM selection_log")

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Session reset successfully"})

# ---------------- ENTRY ----------------
if __name__ == "__main__":
    app.run()
