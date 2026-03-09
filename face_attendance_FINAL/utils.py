"""
utils.py — Helper / Utility Functions
"""

import os
import uuid
from datetime import date
from config import Config


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename: str) -> str:
    ext = original_filename.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def ensure_student_upload_folder(roll_number: str) -> str:
    folder = os.path.join(Config.UPLOAD_FOLDER, roll_number)
    os.makedirs(folder, exist_ok=True)
    return folder


def ensure_dataset_folder(roll_number: str) -> str:
    folder = os.path.join(Config.DATASET_FOLDER, roll_number)
    os.makedirs(folder, exist_ok=True)
    return folder


def today_str() -> str:
    return date.today().strftime("%d %b %Y")


def today_iso() -> str:
    return date.today().isoformat()


MSG_SUCCESS = "success"
MSG_ERROR   = "error"
MSG_WARNING = "warning"
MSG_INFO    = "info"
