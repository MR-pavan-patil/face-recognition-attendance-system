"""
routes/auth.py — Admin Login System (Day 9)
============================================
Login: admin / admin123
Change password in this file (ADMIN_PASSWORD)
"""

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash)
from functools import wraps

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ── Change these to your own credentials ─────────────────────
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ── Login Required Decorator ──────────────────────────────────
def login_required(f):
    """
    Add @login_required above any route to protect it.
    If not logged in → redirect to login page.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please login to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Login Page ────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in → go to dashboard
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.permanent = True
            session["logged_in"]  = True
            session["admin_name"] = username
            flash(f"Welcome back, {username}! 👋", "success")
            return redirect(url_for("dashboard"))
        else:
            error = "Wrong username or password. Try: admin / admin123"

    return render_template("auth/login.html", error=error)


# ── Logout ────────────────────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
