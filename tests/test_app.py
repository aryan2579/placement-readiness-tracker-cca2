
import os
import tempfile

import pytest
import app as app_module


@pytest.fixture()
def client(monkeypatch):
    # Create a temporary database for each test.
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setattr(app_module, "DB_PATH", db_path)

    app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test",
    )

    app_module.init_db()

    try:
        with app_module.app.test_client() as test_client:
            yield test_client
    finally:
        # The test client may preserve a request context.
        # Close the connection while an app context is active.
        with app_module.app.app_context():
            app_module.close_db()

        # Remove the temporary database and SQLite sidecar files.
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = db_path + suffix
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except PermissionError:
                    # Report a cleanup problem instead of hiding it.
                    pytest.fail(
                        f"Could not remove temporary database: {path}"
                    )


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert (
        b"Placement" in response.data
        or b"Student" in response.data
    )


def test_duplicate_roll_number_is_rejected(client):
    student = {
        "roll_no": "CS001",
        "name": "Aryan",
        "department": "CSE",
        "cgpa": "8.5",
        "skills": "Python",
        "status": "Preparing",
    }

    first_response = client.post("/students", data=student)
    second_response = client.post("/students", data=student)

    assert first_response.status_code == 302
    assert second_response.status_code == 302

    with app_module.app.app_context():
        conn = app_module.get_db()

        rows = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM students
            WHERE roll_no = ?
            """,
            ("CS001",),
        ).fetchone()

        assert rows["total"] == 1


def test_csv_export(client):
    client.post(
        "/students",
        data={
            "roll_no": "CS002",
            "name": "Test Student",
            "department": "CSE",
            "cgpa": "8.0",
            "skills": "Python, Git",
            "status": "Preparing",
        },
    )

    response = client.get("/export.csv")

    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert b"Roll No" in response.data
    assert b"CS002" in response.data
