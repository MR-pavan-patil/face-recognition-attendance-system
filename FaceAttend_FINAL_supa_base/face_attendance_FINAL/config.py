"""
config.py — Central Configuration
===================================
All project settings in one place.
"""

import os
from urllib.parse import quote_plus

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "face-attend-secret-key-2024-bca")

    # ── Supabase PostgreSQL ──────────────────────────────────
    SUPABASE_HOST     = "db.yoxpejspivehlcvzudbr.supabase.co"
    SUPABASE_PORT     = "5432"
    SUPABASE_DB       = "postgres"
    SUPABASE_USER     = "postgres"
    SUPABASE_PASSWORD = "@M-AF8Y@6d@AaHg"

    # ✅ quote_plus handles @ # % special chars in password
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{SUPABASE_USER}:{quote_plus(SUPABASE_PASSWORD)}"
        f"@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle" : 300,
        "connect_args" : {"sslmode": "require"},
    }

    # ── File Upload ──────────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, "uploads", "students")
    DATASET_FOLDER     = os.path.join(BASE_DIR, "dataset")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # ── Pagination ───────────────────────────────────────────
    STUDENTS_PER_PAGE = 10

    # ── App Info ─────────────────────────────────────────────
    APP_NAME    = "FaceAttend"
    APP_VERSION = "v1.0.0"
    COLLEGE     = "Satyam College of Science & Commerce, Bidar"

    # ── Admin Login ──────────────────────────────────────────
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # ── Email Settings (Gmail) ───────────────────────────────
    MAIL_SERVER   = "smtp.gmail.com"
    MAIL_PORT     = 587
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "your_email@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "your_app_password_here")
    MAIL_FROM     = os.environ.get("MAIL_USERNAME", "your_email@gmail.com")

    # Low attendance threshold
    LOW_ATTENDANCE_THRESHOLD = 75
