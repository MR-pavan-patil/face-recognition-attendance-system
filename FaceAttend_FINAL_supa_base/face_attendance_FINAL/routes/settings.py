"""
routes/settings.py — App Settings Page
"""
import os, re
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from routes.auth import login_required
from config import Config

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")


def _update_config(key, value):
    """Update a single key in config.py."""
    with open(CONFIG_PATH, "r") as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(key + " ") or stripped.startswith(key + "="):
            indent = len(line) - len(line.lstrip())
            new_lines.append(" " * indent + f'{key} = "{value}"\n')
        else:
            new_lines.append(line)
    with open(CONFIG_PATH, "w") as f:
        f.writelines(new_lines)


@settings_bp.route("/")
@login_required
def index():
    return render_template("settings/index.html",
                           config=Config, active_page="settings")


@settings_bp.route("/api/save", methods=["POST"])
@login_required
def save_settings():
    data = request.get_json()
    try:
        allowed = {
            "COLLEGE", "APP_NAME", "APP_VERSION",
            "LOW_ATTENDANCE_THRESHOLD",
            "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_FROM",
            "ADMIN_USERNAME", "ADMIN_PASSWORD",
        }
        for key, value in data.items():
            if key in allowed:
                _update_config(key, str(value).strip())
        return jsonify({"success": True,
                        "message": "Settings saved! Restart app to apply."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
