
import csv
import io
import os
import sqlite3
from pathlib import Path

from flask import (
    Flask,
    Response,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    str(BASE_DIR / "students.db")
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-me")

STATUSES = [
    "Not Started",
    "Preparing",
    "Interviewing",
    "Placed",
]


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db():
    """Create one database connection per Flask app context."""
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Close the database connection when the app context ends."""
    conn = g.pop("db", None)

    if conn is not None:
        conn.close()



def init_db():
    """Create the students table and always close the connection."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                cgpa REAL NOT NULL CHECK(cgpa >= 0 AND cgpa <= 10),
                skills TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Not Started',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def eligible(cgpa):
    """Return True if the student's CGPA is at least 7.0."""
    return float(cgpa) >= 7.0


@app.before_request
def ensure_database():
    """Ensure the database and required table exist."""
    init_db()


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    try:
        conn = get_db()
        conn.execute("SELECT 1").fetchone()

        return jsonify(
            status="healthy",
            service="placement-readiness-tracker"
        ), 200

    except sqlite3.Error:
        return jsonify(status="unhealthy"), 500


# --------------------------------------------------
# HOME PAGE AND STUDENT DASHBOARD
# --------------------------------------------------

@app.get("/")
def index():
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = """
        SELECT *
        FROM students
        WHERE (
            name LIKE ?
            OR roll_no LIKE ?
            OR department LIKE ?
        )
    """

    params = [f"%{search}%"] * 3

    if status_filter in STATUSES:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY name COLLATE NOCASE"

    conn = get_db()

    students = conn.execute(query, params).fetchall()

    all_students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    stats = {
        "total": len(all_students),
        "eligible": sum(
            1 for student in all_students
            if eligible(student["cgpa"])
        ),
        "interviewing": sum(
            1 for student in all_students
            if student["status"] == "Interviewing"
        ),
        "placed": sum(
            1 for student in all_students
            if student["status"] == "Placed"
        ),
    }

    return render_template(
        "index.html",
        students=students,
        stats=stats,
        q=search,
        status_filter=status_filter,
        statuses=STATUSES,
        eligible=eligible,
    )


# --------------------------------------------------
# ADD STUDENT
# --------------------------------------------------

@app.post("/students")
def add_student():
    roll_no = request.form.get(
        "roll_no", ""
    ).strip().upper()

    name = request.form.get(
        "name", ""
    ).strip()

    department = request.form.get(
        "department", ""
    ).strip()

    skills = request.form.get(
        "skills", ""
    ).strip()

    status = request.form.get(
        "status", "Not Started"
    )

    try:
        cgpa = float(request.form.get("cgpa", ""))

    except (ValueError, TypeError):
        flash("Enter a valid CGPA.", "error")
        return redirect(url_for("index"))

    if (
        not all([roll_no, name, department])
        or not 0 <= cgpa <= 10
        or status not in STATUSES
    ):
        flash(
            "Please complete all required fields and "
            "use a CGPA between 0 and 10.",
            "error",
        )
        return redirect(url_for("index"))

    try:
        conn = get_db()

        conn.execute(
            """
            INSERT INTO students
                (roll_no, name, department, cgpa, skills, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                roll_no,
                name,
                department,
                cgpa,
                skills,
                status,
            ),
        )

        conn.commit()

        flash(
            f"Student {name} added successfully.",
            "success",
        )

    except sqlite3.IntegrityError:
        flash(
            "That roll number already exists. "
            "Use a unique roll number.",
            "error",
        )

    except sqlite3.Error:
        app.logger.exception("Unable to add student")
        flash(
            "A database error occurred while adding the student.",
            "error",
        )

    return redirect(url_for("index"))


# --------------------------------------------------
# UPDATE PLACEMENT STATUS
# --------------------------------------------------

@app.post("/students/<int:student_id>/update")
def update_student(student_id):
    status = request.form.get("status", "")

    if status not in STATUSES:
        flash("Choose a valid placement status.", "error")

    else:
        conn = get_db()

        result = conn.execute(
            """
            UPDATE students
            SET status = ?
            WHERE id = ?
            """,
            (status, student_id),
        )

        conn.commit()

        if result.rowcount:
            flash("Placement status updated.", "success")
        else:
            flash("Student not found.", "error")

    return redirect(url_for("index"))


# --------------------------------------------------
# DELETE STUDENT
# --------------------------------------------------

@app.post("/students/<int:student_id>/delete")
def delete_student(student_id):
    conn = get_db()

    result = conn.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,),
    )

    conn.commit()

    if result.rowcount:
        flash("Student deleted.", "success")
    else:
        flash("Student not found.", "error")

    return redirect(url_for("index"))


# --------------------------------------------------
# EXPORT STUDENTS TO CSV
# --------------------------------------------------

@app.get("/export.csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Roll No",
        "Name",
        "Department",
        "CGPA",
        "Eligible (CGPA >= 7.0)",
        "Skills",
        "Placement Status",
    ])

    conn = get_db()

    students = conn.execute(
        """
        SELECT *
        FROM students
        ORDER BY name COLLATE NOCASE
        """
    )

    for student in students:
        writer.writerow([
            student["roll_no"],
            student["name"],
            student["department"],
            student["cgpa"],
            "Yes" if eligible(student["cgpa"]) else "No",
            student["skills"],
            student["status"],
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=placement_students.csv"
        },
    )


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
