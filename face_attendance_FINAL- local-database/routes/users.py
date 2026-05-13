"""
routes/users.py — User Management (Admin Only)
================================================
CRUD operations for admin/teacher/student accounts.
Includes pending approval queue for self-registered users.
"""

from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, jsonify)
from database import db
from models import User, Student, ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
from routes.auth import login_required, role_required

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
@role_required("admin")
def list_users():
    pending = User.query.filter_by(is_active=False).order_by(User.created_at.desc()).all()
    active  = User.query.filter_by(is_active=True).order_by(User.role, User.name).all()
    return render_template("users/list.html",
                           pending=pending, users=active,
                           active_page="users")


@users_bp.route("/create", methods=["GET", "POST"])
@role_required("admin")
def create_user():
    if request.method == "POST":
        username   = request.form.get("username", "").strip()
        password   = request.form.get("password", "").strip()
        name       = request.form.get("name",     "").strip()
        email      = request.form.get("email",    "").strip()
        role       = request.form.get("role",     "teacher").strip()
        department = request.form.get("department", "").strip()
        student_id = request.form.get("student_id", "").strip()

        if not all([username, password, name, role]):
            flash("Username, password, name and role are required.", "error")
            return _render_create_form()

        if len(password) < 4:
            flash("Password must be at least 4 characters.", "error")
            return _render_create_form()

        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' already exists.", "error")
            return _render_create_form()

        if role not in [ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT]:
            flash("Invalid role.", "error")
            return _render_create_form()

        try:
            user = User(
                username=username, name=name, email=email or None,
                role=role, department=department or None,
                student_id=int(student_id) if student_id else None,
                is_active=True,  # Admin-created users are active immediately
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"User '{name}' created as {role}!", "success")
            return redirect(url_for("users.list_users"))
        except Exception as e:
            db.session.rollback()
            flash(f"Creation failed: {str(e)}", "error")

    return _render_create_form()


def _render_create_form():
    departments = [r[0] for r in db.session.query(Student.department)
                   .filter_by(is_active=True).distinct().all()]
    students = Student.query.filter_by(is_active=True).order_by(Student.name).all()
    return render_template("users/create.html",
                           departments=sorted(departments),
                           students=students,
                           active_page="users")


# ── Approve Pending User ──────────────────────────────────────
@users_bp.route("/<int:user_id>/approve", methods=["POST"])
@role_required("admin")
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        user.is_active = True
        db.session.commit()
        flash(f"'{user.name}' approved as {user.role}!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Approval failed: {str(e)}", "error")
    return redirect(url_for("users.list_users"))


# ── Reject (Delete) Pending User ──────────────────────────────
@users_bp.route("/<int:user_id>/reject", methods=["POST"])
@role_required("admin")
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        name = user.name
        db.session.delete(user)
        db.session.commit()
        flash(f"'{name}' rejected and removed.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Rejection failed: {str(e)}", "error")
    return redirect(url_for("users.list_users"))


# ── Delete Active User ────────────────────────────────────────
@users_bp.route("/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == ROLE_ADMIN:
        admin_count = User.query.filter_by(role=ROLE_ADMIN, is_active=True).count()
        if admin_count <= 1:
            flash("Cannot delete the last admin!", "error")
            return redirect(url_for("users.list_users"))
    try:
        name = user.name
        db.session.delete(user)
        db.session.commit()
        flash(f"User '{name}' deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Delete failed: {str(e)}", "error")
    return redirect(url_for("users.list_users"))


# ── Toggle Active Status ──────────────────────────────────────
@users_bp.route("/<int:user_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        user.is_active = not user.is_active
        db.session.commit()
        status = "activated" if user.is_active else "deactivated"
        return jsonify({"success": True, "message": f"{user.name} {status}",
                        "is_active": user.is_active})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ── API: Pending Count (for sidebar badge) ────────────────────
@users_bp.route("/api/pending-count")
@role_required("admin")
def pending_count():
    count = User.query.filter_by(is_active=False).count()
    return jsonify({"count": count})
