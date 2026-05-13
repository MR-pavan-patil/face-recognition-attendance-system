"""
routes/auth.py — Role-Based Auth System with Self-Registration
================================================================
- Login with hashed passwords
- Self-registration (pending admin approval)
- Roles: admin | teacher | student
"""

from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash, g)
from functools import wraps
from database import db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Get Current User ──────────────────────────────────────────
def get_current_user():
    """Fetch logged-in user from session. Returns User object or None."""
    if "user_id" not in session:
        return None
    from models import User
    return User.query.get(session["user_id"])


# ── Login Required Decorator ──────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please login to access this page.", "warning")
            return redirect(url_for("auth.login"))
        g.user = get_current_user()
        if not g.user:
            session.clear()
            flash("Session expired. Please login again.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Role Required Decorator ──────────────────────────────────
def role_required(*roles):
    """Restrict route to specific roles. Usage: @role_required('admin', 'teacher')"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("logged_in"):
                flash("Please login to access this page.", "warning")
                return redirect(url_for("auth.login"))
            g.user = get_current_user()
            if not g.user:
                session.clear()
                return redirect(url_for("auth.login"))
            if g.user.role not in roles:
                flash("You don't have permission to access this page.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Login Page ────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    # Determine which tab is active (login or register)
    mode = request.args.get("mode", "login")

    error = None
    reg_error = None
    reg_success = None

    if request.method == "POST":
        form_type = request.form.get("form_type", "login")

        if form_type == "login":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            from models import User
            user = User.query.filter_by(username=username).first()

            if not user:
                error = "Account not found. Please sign up first."
                mode = "login"
            elif not user.is_active:
                error = "Your account is pending admin approval. Please wait."
                mode = "login"
            elif not user.check_password(password):
                error = "Wrong password. Please try again."
                mode = "login"
            else:
                session.permanent = True
                session["logged_in"]  = True
                session["user_id"]    = user.id
                session["user_role"]  = user.role
                session["user_name"]  = user.name
                session["user_dept"]  = user.department or ""
                flash(f"Welcome back, {user.name}!", "success")
                if user.is_student:
                    return redirect(url_for("student_dashboard.my_dashboard"))
                return redirect(url_for("dashboard"))

        elif form_type == "register":
            name       = request.form.get("reg_name",       "").strip()
            username   = request.form.get("reg_username",   "").strip()
            email      = request.form.get("reg_email",      "").strip()
            password   = request.form.get("reg_password",   "").strip()
            confirm    = request.form.get("reg_confirm",    "").strip()
            role       = request.form.get("reg_role",       "student").strip()
            department = request.form.get("reg_department", "").strip()

            mode = "register"

            # Validations
            if not all([name, username, password, confirm]):
                reg_error = "All required fields must be filled."
            elif len(username) < 3:
                reg_error = "Username must be at least 3 characters."
            elif len(password) < 4:
                reg_error = "Password must be at least 4 characters."
            elif password != confirm:
                reg_error = "Passwords do not match."
            elif role not in ["teacher", "student"]:
                reg_error = "Invalid role selected."
            else:
                from models import User, ROLE_TEACHER, ROLE_STUDENT
                if User.query.filter_by(username=username).first():
                    reg_error = f"Username '{username}' is already taken."
                elif email and User.query.filter_by(email=email).first():
                    reg_error = "This email is already registered."
                else:
                    try:
                        new_user = User(
                            username=username,
                            name=name,
                            email=email or None,
                            role=role,
                            department=department or None,
                            is_active=False,  # Pending approval!
                        )
                        new_user.set_password(password)
                        db.session.add(new_user)
                        db.session.commit()
                        reg_success = "Account created! Waiting for admin approval."
                        mode = "login"
                    except Exception as e:
                        db.session.rollback()
                        reg_error = f"Registration failed: {str(e)}"

    # Get departments for dropdown
    from models import Student
    departments = [r[0] for r in db.session.query(Student.department)
                   .filter_by(is_active=True).distinct().all()]

    # Count pending users for badge
    from models import User
    pending_count = User.query.filter_by(is_active=False).count()

    return render_template("auth/login.html",
                           error=error,
                           reg_error=reg_error,
                           reg_success=reg_success,
                           mode=mode,
                           departments=sorted(departments),
                           pending_count=pending_count)


# ── Logout ────────────────────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
