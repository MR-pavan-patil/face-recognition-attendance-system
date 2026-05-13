"""
attendance_manager.py — Attendance Marking Logic
==================================================
Day 7: Handles all attendance database operations.

RESPONSIBILITIES:
  1. Fetch student from DB by roll_number
  2. Check if attendance already marked today
  3. Insert new attendance record if not marked
  4. Return clear status messages to camera.py

WHY SEPARATE FILE?
  Keeping this separate from camera.py means:
  - camera.py handles ONLY video/recognition
  - This file handles ONLY database operations
  - Easy to test independently
  - Easy to modify without touching camera code

HOW DUPLICATE PREVENTION WORKS:
  The attendance table has a UNIQUE constraint on
  (student_id, date). So even if we accidentally try
  to insert twice, the database will reject it.
  We also check manually BEFORE inserting to show
  the correct message on screen.
"""

import sys
from datetime import date, datetime


# ─────────────────────────────────────────────────────────────
#  STATUS CODES — returned to camera.py
# ─────────────────────────────────────────────────────────────
STATUS_MARKED        = "marked"          # ✓ Newly marked present
STATUS_ALREADY_DONE  = "already_marked"  # ↩ Already marked today
STATUS_UNKNOWN       = "unknown"         # ? Roll number not in DB
STATUS_ERROR         = "error"           # ✗ Database/network error


# ─────────────────────────────────────────────────────────────
#  DATABASE CONNECTION
#  Uses same config as the Flask app
# ─────────────────────────────────────────────────────────────
def get_db_connection():
    """
    Create a direct PyMySQL connection.
    We use a direct connection here (not SQLAlchemy)
    because camera.py runs outside the Flask app context.
    """
    try:
        import pymysql
        from urllib.parse import unquote

        # Load config values
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import Config

        # Decode password (in case it was URL-encoded)
        password = unquote(Config.MYSQL_PASSWORD)

        conn = pymysql.connect(
            host     = Config.MYSQL_HOST,
            port     = int(Config.MYSQL_PORT),
            user     = Config.MYSQL_USER,
            password = password,
            database = Config.MYSQL_DB,
            charset  = "utf8mb4",
            autocommit = False,
            cursorclass = pymysql.cursors.DictCursor,
            connect_timeout = 10,
        )
        return conn

    except ImportError:
        raise RuntimeError("PyMySQL not installed. Run: pip install pymysql")
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {str(e)}")


# ─────────────────────────────────────────────────────────────
#  FETCH STUDENT BY ROLL NUMBER
# ─────────────────────────────────────────────────────────────
def get_student_by_roll(conn, roll_number: str):
    """
    Fetch student record from DB using roll_number.
    Returns dict with student info, or None if not found.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, roll_number, department, year "
                "FROM students WHERE roll_number = %s AND is_active = 1",
                (roll_number,)
            )
            return cursor.fetchone()  # Returns dict or None
    except Exception as e:
        raise RuntimeError(f"Error fetching student: {str(e)}")


# ─────────────────────────────────────────────────────────────
#  CHECK IF ATTENDANCE ALREADY MARKED TODAY
# ─────────────────────────────────────────────────────────────
def is_already_marked(conn, student_id: int, today: date) -> bool:
    """
    WHY THIS CHECK IS IMPORTANT:
    ─────────────────────────────
    A student might walk past the camera multiple times.
    Without this check, we'd insert dozens of records per day.
    This ensures exactly ONE attendance record per student per day.

    We check in Python BEFORE inserting so we can show the
    correct message on screen. The DB also has a UNIQUE
    constraint as a final safety net.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM attendance "
                "WHERE student_id = %s AND date = %s",
                (student_id, today)
            )
            return cursor.fetchone() is not None
    except Exception as e:
        raise RuntimeError(f"Error checking attendance: {str(e)}")


# ─────────────────────────────────────────────────────────────
#  INSERT ATTENDANCE RECORD
# ─────────────────────────────────────────────────────────────
def insert_attendance(conn, student_id: int, today: date, now: datetime) -> bool:
    """
    Insert a new attendance record.
    Returns True on success, False on failure.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO attendance (student_id, date, time_in, status, marked_by) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    student_id,
                    today,
                    now.strftime("%H:%M:%S"),
                    "Present",
                    "FaceRecognition",
                )
            )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error inserting attendance: {str(e)}")


# ─────────────────────────────────────────────────────────────
#  MAIN FUNCTION — called from camera.py
# ─────────────────────────────────────────────────────────────
def mark_attendance(roll_number: str) -> dict:
    """
    Master function called by camera.py when a face is recognized.

    Args:
        roll_number: The recognized student's roll number

    Returns a dict:
    {
        "status"  : "marked" | "already_marked" | "unknown" | "error",
        "message" : "Human readable message for display",
        "student" : { name, roll_number, department } or None,
        "time"    : "HH:MM AM/PM" or None,
    }

    FLOW:
    ─────
    1. Connect to MySQL
    2. Find student by roll_number
    3. If not found → return STATUS_UNKNOWN
    4. Check if already marked today
    5. If yes  → return STATUS_ALREADY_DONE
    6. If no   → insert record → return STATUS_MARKED
    7. Close connection
    """
    conn = None
    today = date.today()
    now   = datetime.now()

    try:
        # Step 1 — Connect
        conn = get_db_connection()

        # Step 2 — Find student
        student = get_student_by_roll(conn, roll_number)
        if not student:
            return {
                "status" : STATUS_UNKNOWN,
                "message": f"Roll '{roll_number}' not found in database",
                "student": None,
                "time"   : None,
            }

        student_id = student["id"]
        name       = student["name"]

        # Step 3 — Check duplicate
        if is_already_marked(conn, student_id, today):
            return {
                "status" : STATUS_ALREADY_DONE,
                "message": f"Already marked today",
                "student": student,
                "time"   : now.strftime("%I:%M %p"),
            }

        # Step 4 — Insert attendance
        insert_attendance(conn, student_id, today, now)

        return {
            "status" : STATUS_MARKED,
            "message": f"Attendance marked at {now.strftime('%I:%M %p')}",
            "student": student,
            "time"   : now.strftime("%I:%M %p"),
        }

    except RuntimeError as e:
        return {
            "status" : STATUS_ERROR,
            "message": str(e),
            "student": None,
            "time"   : None,
        }

    except Exception as e:
        return {
            "status" : STATUS_ERROR,
            "message": f"Unexpected error: {str(e)[:60]}",
            "student": None,
            "time"   : None,
        }

    finally:
        if conn:
            conn.close()


# ─────────────────────────────────────────────────────────────
#  GET TODAY'S ATTENDANCE — used by Flask dashboard
# ─────────────────────────────────────────────────────────────
def get_todays_attendance() -> list:
    """
    Returns list of all students marked present today.
    Used by the Flask web dashboard.
    """
    conn = None
    try:
        conn = get_db_connection()
        today = date.today()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
                    s.name,
                    s.roll_number,
                    s.department,
                    s.year,
                    a.time_in,
                    a.status,
                    a.marked_by
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.date = %s
                ORDER BY a.time_in DESC
                """,
                (today,)
            )
            return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching today's attendance: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


# ─────────────────────────────────────────────────────────────
#  QUICK TEST — run this file directly to test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "═" * 50)
    print("  Attendance Manager — Quick Test")
    print("═" * 50)

    # HOW TO TEST:
    # Replace "BCA2024001" with an actual roll number from your DB
    test_roll = "BCA2024001"

    print(f"\n  Testing with roll number: {test_roll}")
    result = mark_attendance(test_roll)

    print(f"\n  Status  : {result['status']}")
    print(f"  Message : {result['message']}")
    if result["student"]:
        print(f"  Student : {result['student']['name']}")
    if result["time"]:
        print(f"  Time    : {result['time']}")

    print("\n  Run again to test duplicate prevention:")
    print(f"  python attendance_manager.py")
    print("═" * 50 + "\n")
