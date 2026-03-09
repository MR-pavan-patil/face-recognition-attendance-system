"""
routes/students.py — Student Management (Final)
"""
import os, uuid, shutil
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file, abort
from database import db
from models import Student, StudentImage
from routes.auth import login_required

students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.route("/")
@login_required
def list_students():
    page   = request.args.get("page",   1,  type=int)
    search = request.args.get("search", "").strip()
    dept   = request.args.get("dept",   "all")

    query = Student.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(
                Student.name.ilike(f"%{search}%"),
                Student.roll_number.ilike(f"%{search}%"),
                Student.email.ilike(f"%{search}%"),
            )
        )
    if dept != "all":
        query = query.filter_by(department=dept)

    students  = query.order_by(Student.registered_at.desc()).paginate(
                    page=page, per_page=10, error_out=False)
    all_depts = [r[0] for r in db.session.query(Student.department)
                 .filter_by(is_active=True).distinct().all()]

    return render_template("students/list.html",
                           students=students, search=search,
                           selected_dept=dept, all_depts=sorted(all_depts),
                           active_page="students")


@students_bp.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "POST":
        name        = request.form.get("name",        "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        email       = request.form.get("email",       "").strip()
        phone       = request.form.get("phone",       "").strip()
        department  = request.form.get("department",  "").strip()
        year        = request.form.get("year",        "").strip()
        section     = request.form.get("section",     "").strip()

        if not all([name, roll_number, email, department, year]):
            flash("All required fields must be filled.", "error")
            return render_template("students/register.html", active_page="students")

        # ── Duplicate check — ONLY active students ────────────
        # Agar pehle delete kiya tha (is_active=False) toh reactivate karo
        old_roll  = Student.query.filter_by(roll_number=roll_number).first()
        old_email = Student.query.filter_by(email=email).first()

        if old_roll and old_roll.is_active:
            flash(f"Roll number '{roll_number}' already registered.", "error")
            return render_template("students/register.html", active_page="students")

        if old_email and old_email.is_active:
            flash(f"Email '{email}' already registered.", "error")
            return render_template("students/register.html", active_page="students")

        # ── Agar deleted student ka same roll number hai → reactivate ──
        if old_roll and not old_roll.is_active:
            try:
                old_roll.name        = name
                old_roll.email       = email
                old_roll.phone       = phone or None
                old_roll.department  = department
                old_roll.year        = year
                old_roll.section     = section or None
                old_roll.is_active   = True
                old_roll.dataset_ready = False
                db.session.commit()
                flash(f"Student '{name}' re-registered successfully!", "success")
                return redirect(url_for("students.list_students"))
            except Exception as e:
                db.session.rollback()
                flash(f"Re-registration failed: {str(e)}", "error")
                return render_template("students/register.html", active_page="students")

        # ── Fresh registration ─────────────────────────────────
        try:
            student = Student(
                name=name, roll_number=roll_number, email=email,
                phone=phone or None, department=department,
                year=year, section=section or None,
            )
            db.session.add(student)
            db.session.flush()

            photos = request.files.getlist("photos")
            folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(student.id))
            os.makedirs(folder, exist_ok=True)

            for photo in photos:
                if photo and photo.filename:
                    ext      = photo.filename.rsplit(".", 1)[-1].lower()
                    filename = f"{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(folder, filename)
                    photo.save(filepath)
                    db.session.add(StudentImage(
                        student_id=student.id,
                        filename=filename,
                        filepath=filepath,
                    ))

            db.session.commit()
            flash(f"Student '{name}' registered successfully!", "success")
            return redirect(url_for("students.list_students"))

        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "error")

    return render_template("students/register.html", active_page="students")


@students_bp.route("/<int:student_id>")
@login_required
def view_student(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template("students/detail.html",
                           student=student, active_page="students")


@students_bp.route("/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    """
    Hard delete — student aur uska dataset bhi hata do.
    Phir dobara same roll se register karein toh koi problem nahi.
    """
    from config import Config
    student = Student.query.get_or_404(student_id)
    name    = student.name
    roll    = student.roll_number

    try:
        # Delete dataset folder
        dataset_folder = os.path.join(Config.DATASET_FOLDER, roll)
        if os.path.exists(dataset_folder):
            shutil.rmtree(dataset_folder)

        # Hard delete from DB
        db.session.delete(student)
        db.session.commit()

        flash(f"Student '{name}' permanently deleted.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Delete failed: {str(e)}", "error")

    return redirect(url_for("students.list_students"))


@students_bp.route("/api/all")
@login_required
def api_all_students():
    students = Student.query.filter_by(is_active=True).order_by(Student.name).all()
    return jsonify([s.to_dict() for s in students])

@students_bp.route("/photo/<int:image_id>")
@login_required
def serve_photo(image_id):
    """Serve student uploaded photo securely."""
    from models import StudentImage
    img = StudentImage.query.get_or_404(image_id)
    if not os.path.exists(img.filepath):
        abort(404)
    return send_file(img.filepath, mimetype="image/jpeg")


@students_bp.route("/dataset-photo/<roll>/<filename>")
@login_required  
def serve_dataset_photo(roll, filename):
    """Serve student dataset photo."""
    from config import Config
    import re
    # Security: only allow safe filenames
    if not re.match(r'^[\w\-]+\.(jpg|jpeg|png|webp)$', filename, re.IGNORECASE):
        abort(404)
    filepath = os.path.join(Config.DATASET_FOLDER, roll, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_file(filepath, mimetype="image/jpeg")

