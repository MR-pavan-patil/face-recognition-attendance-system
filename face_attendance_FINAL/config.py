"""
config.py — Central Configuration
===================================
All project settings in one place.
⚠️  Edit MYSQL_PASSWORD to your MySQL password before running!
"""

import os
from urllib.parse import quote_plus

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "face-attend-secret-key-2024-bca")

    # ── MySQL ────────────────────────────────────────────────
    # ⚠️  Change "your_password_here" to your actual MySQL password
    MYSQL_USER     = os.environ.get("MYSQL_USER",     "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "Admin@1234")  # Change this to your MySQL password
    MYSQL_HOST     = os.environ.get("MYSQL_HOST",     "localhost")
    MYSQL_PORT     = os.environ.get("MYSQL_PORT",     "3306")
    MYSQL_DB       = os.environ.get("MYSQL_DB",       "face_attendance_db")

    # quote_plus handles special characters like @ # % in passwords
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{quote_plus(MYSQL_PASSWORD)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── File Upload ──────────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, "uploads", "students")
    DATASET_FOLDER     = os.path.join(BASE_DIR, "dataset")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # ── Pagination ───────────────────────────────────────────
    STUDENTS_PER_PAGE = 10

    # ── App Info ─────────────────────────────────────────────
    APP_NAME    = "FaceAttend"
    APP_VERSION = "Day 9 — Final"
    COLLEGE     = "Your College Name"

    # ── Admin Login ──────────────────────────────────────────────
    # ⚠️  Change these before demo!
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # ── Email Settings (Gmail) ───────────────────────────────
    # ⚠️  Steps:
    # 1. Gmail → Settings → Security → 2-Step Verification ON
    # 2. Gmail → App Passwords → Create → Copy 16-char password
    # 3. Paste below (not your real Gmail password!)
    MAIL_SERVER   = "smtp.gmail.com"
    MAIL_PORT     = 587
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "patilwebsite@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "djslnfinporpeurr")
    MAIL_FROM     = os.environ.get("MAIL_USERNAME", "patilwebsite@gmail.com")

    # Low attendance threshold
    LOW_ATTENDANCE_THRESHOLD = 75   # % se kam → alert
