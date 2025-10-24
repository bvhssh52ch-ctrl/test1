from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import os
from pathlib import Path

# ---------------------------
# Basic configuration
# ---------------------------
DB_PATH = "attendance.db"  # SQLite file on disk
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "secret-admin")  # change in production

app = Flask(__name__)  # Flask application instance

# ---------------------------
# Database helpers (SQLite)
# ---------------------------
def get_conn():
    """Return a SQLite connection with dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they do not exist (idempotent)."""
    conn = get_conn()
    cur = conn.cursor()

    # Employees table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee','manager','admin')),
            created_at TEXT NOT NULL
        )
        """
    )

    # Time entries table (clock/break events)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('CLOCK_IN','CLOCK_OUT','BREAK_START','BREAK_END')),
            ts TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
        """
    )

    conn.commit()
    conn.close()

def now_iso() -> str:
    """Return current UTC-ish ISO timestamp (YYYY-MM-DDTHH:MM:SSZ)."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def require_admin(req) -> bool:
    """Simple header-based admin check (for demo only)."""
    return req.headers.get("X-ADMIN-TOKEN") == ADMIN_TOKEN
# ---------------------------
# Public endpoints (employees)
# ---------------------------

@app.post("/register")
def register_employee():
    """Register a new employee (name + role)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    role = (data.get("role") or "employee").strip().lower()

    if not name or role not in ("employee", "manager", "admin"):
        return jsonify(error="Bad payload: name required, role in {employee, manager, admin}"), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO employees (name, role, created_at) VALUES (?,?,?)",
        (name, role, now_iso()),
    )
    emp_id = cur.lastrowid
    conn.commit()
    conn.close()

    return jsonify(id=emp_id, name=name, role=role), 201


@app.post("/clock-in")
def clock_in():
    """Record a clock-in event."""
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        return jsonify(error="employee_id required"), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM employees WHERE id=?", (employee_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify(error="Employee not found"), 404

    cur.execute(
        "INSERT INTO time_entries (employee_id, event_type, ts) VALUES (?,?,?)",
        (employee_id, "CLOCK_IN", now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify(message="Clock-in recorded"), 201


@app.post("/clock-out")
def clock_out():
    """Record a clock-out event."""
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        return jsonify(error="employee_id required"), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM employees WHERE id=?", (employee_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify(error="Employee not found"), 404

    cur.execute(
        "INSERT INTO time_entries (employee_id, event_type, ts) VALUES (?,?,?)",
        (employee_id, "CLOCK_OUT", now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify(message="Clock-out recorded"), 201


@app.post("/break-start")
def break_start():
    """Record the start of a break."""
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        return jsonify(error="employee_id required"), 400
 
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM employees WHERE id=?", (employee_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify(error="Employee not found"), 404

    cur.execute(
        "INSERT INTO time_entries (employee_id, event_type, ts) VALUES (?,?,?)",
        (employee_id, "BREAK_START", now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify(message="Break started"), 201


@app.post("/break-end")
def break_end():
    """Record the end of a break."""
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        return jsonify(error="employee_id required"), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM employees WHERE id=?", (employee_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify(error="Employee not found"), 404

    cur.execute(
        "INSERT INTO time_entries (employee_id, event_type, ts) VALUES (?,?,?)",
        (employee_id, "BREAK_END", now_iso()),
    )
    conn.commit()
    conn.close()
    return jsonify(message="Break ended"), 201
# ---------------------------
# Admin endpoints (read-only)
# ---------------------------

@app.get("/employees")
def list_employees():
    """List all employees (admin-only)."""
    if not require_admin(request):
        return jsonify(error="Admin token required"), 403

    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, name, role, created_at FROM employees ORDER BY id"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200


@app.get("/entries")
def list_entries():
    """List time entries with optional filters (admin-only)."""
    if not require_admin(request):
        return jsonify(error="Admin token required"), 403

    employee_id = request.args.get("employee_id")
    date = request.args.get("date")  # YYYY-MM-DD

    sql = "SELECT id, employee_id, event_type, ts FROM time_entries WHERE 1=1"
    params = []
    if employee_id:
        sql += " AND employee_id=?"
        params.append(employee_id)
    if date:
        sql += " AND ts LIKE ?"
        params.append(f"{date}%")

    sql += " ORDER BY ts DESC"

    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute(sql, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200
# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    # Ensure DB and tables exist
    if not Path(DB_PATH).exists():
        init_db()
    else:
        # Safe to call again in case schema is missing
        init_db()

    app.run(debug=True)

