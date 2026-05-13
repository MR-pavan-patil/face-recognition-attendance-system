"""
routes/attendance.py — Attendance (Final Clean)
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from database import db
from models import Student, Attendance
from datetime import date, datetime, timedelta
from routes.auth import login_required

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendance")


@attendance_bp.route("/")
@login_required
def today_attendance():
    today  = date.today()
    page   = request.args.get("page",   1, type=int)
    search = request.args.get("search", "").strip()

    query = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .filter(Attendance.date == today)
        .order_by(Attendance.time_in.desc())
    )
    if search:
        query = query.filter(db.or_(
            Student.name.ilike(f"%{search}%"),
            Student.roll_number.ilike(f"%{search}%"),
        ))
    records = query.paginate(page=page, per_page=20, error_out=False)

    total   = Student.query.filter_by(is_active=True).count()
    present = Attendance.query.filter_by(date=today, status="Present").count()

    stats = {
        "date"      : today.strftime("%d %B %Y"),
        "day_name"  : today.strftime("%A"),
        "total"     : total,
        "present"   : present,
        "absent"    : max(total - present, 0),
        "percentage": round(present / total * 100, 1) if total > 0 else 0,
    }
    return render_template("attendance/today.html",
                           records=records, stats=stats,
                           search=search, today=today,
                           active_page="attendance")


@attendance_bp.route("/history")
@login_required
def history():
    date_str = request.args.get("date", "")
    try:
        selected = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        selected = date.today()

    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .filter(Attendance.date == selected)
        .order_by(Attendance.time_in)
        .all()
    )
    total   = Student.query.filter_by(is_active=True).count()
    present = len(records)
    return render_template("attendance/history.html",
                           records=records, selected_date=selected,
                           total=total, present=present,
                           absent=max(total - present, 0),
                           percentage=round(present / total * 100, 1) if total else 0,
                           active_page="attendance")


@attendance_bp.route("/absent")
@login_required
def absent_list():
    date_str = request.args.get("date", "")
    try:
        sel = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        sel = date.today()

    all_students    = Student.query.filter_by(is_active=True).all()
    present_ids     = {a.student_id for a in
                       Attendance.query.filter_by(date=sel, status="Present").all()}
    absent_students = sorted([s for s in all_students if s.id not in present_ids],
                             key=lambda s: s.name)

    total   = len(all_students)
    present = len(present_ids)
    absent  = len(absent_students)

    return render_template("attendance/absent.html",
                           absent_students=absent_students,
                           selected_date=sel, today=date.today(),
                           total=total, present=present, absent=absent,
                           percentage=round(present / total * 100, 1) if total else 0,
                           active_page="absent")


@attendance_bp.route("/api/mark", methods=["POST"])
@login_required
def api_mark():
    data       = request.get_json()
    student_id = data.get("student_id") if data else None
    mark_date  = data.get("date")

    if not student_id:
        return jsonify({"success": False, "error": "student_id required"}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404

    try:
        att_date = datetime.strptime(mark_date, "%Y-%m-%d").date() if mark_date else date.today()
    except ValueError:
        att_date = date.today()

    existing = Attendance.query.filter_by(student_id=student_id, date=att_date).first()
    if existing:
        return jsonify({"success": False, "status": "already_marked",
                        "message": f"{student.name} already marked"})
    try:
        record = Attendance(student_id=student_id, date=att_date,
                            time_in=datetime.now().time(),
                            status="Present", marked_by="Manual")
        db.session.add(record)
        db.session.commit()
        return jsonify({"success": True, "status": "marked",
                        "message": f"✓ {student.name} marked present",
                        "time": datetime.now().strftime("%I:%M %p")})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route("/api/undo", methods=["POST"])
@login_required
def api_undo():
    data          = request.get_json()
    attendance_id = data.get("attendance_id") if data else None
    student_id    = data.get("student_id")
    undo_date     = data.get("date")

    try:
        if attendance_id:
            record = Attendance.query.get(attendance_id)
        elif student_id and undo_date:
            att_date = datetime.strptime(undo_date, "%Y-%m-%d").date()
            record   = Attendance.query.filter_by(
                student_id=student_id, date=att_date).first()
        else:
            return jsonify({"success": False, "error": "attendance_id or student_id+date required"}), 400

        if not record:
            return jsonify({"success": False, "error": "Record not found"})

        student = Student.query.get(record.student_id)
        db.session.delete(record)
        db.session.commit()
        return jsonify({"success": True,
                        "message": f"✓ Removed for {student.name if student else 'student'}"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route("/api/today")
@login_required
def api_today():
    today   = date.today()
    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .filter(Attendance.date == today)
        .order_by(Attendance.time_in.desc())
        .all()
    )
    total = Student.query.filter_by(is_active=True).count()
    data  = [{"id": att.id, "name": stu.name, "roll_number": stu.roll_number,
               "department": stu.department,
               "time_in": str(att.time_in) if att.time_in else "--",
               "status": att.status, "marked_by": att.marked_by}
             for att, stu in records]
    return jsonify({"total": total, "present": len(data), "records": data})
