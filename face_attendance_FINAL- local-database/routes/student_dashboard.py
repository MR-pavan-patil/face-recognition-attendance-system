"""
routes/student_dashboard.py — Student Self-Service Portal
==========================================================
Students can only see their own attendance data.
"""

from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, jsonify, g
from database import db
from models import Student, Attendance, ROLE_STUDENT
from routes.auth import login_required, role_required

student_dashboard_bp = Blueprint("student_dashboard", __name__, url_prefix="/my")


@student_dashboard_bp.route("/dashboard")
@role_required("student")
def my_dashboard():
    student = Student.query.get(g.user.student_id) if g.user.student_id else None
    if not student:
        return render_template("student/dashboard.html",
                               student=None, active_page="my_dashboard")

    today = date.today()
    start_30 = today - timedelta(days=29)

    # 30-day stats
    records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= start_30, Attendance.date <= today,
        Attendance.status == "Present"
    ).order_by(Attendance.date.desc()).all()

    working = sum(1 for i in range(30) if (start_30 + timedelta(days=i)).weekday() < 6)
    days_present = len(records)
    pct = round(days_present / working * 100, 1) if working > 0 else 0
    status = "Good" if pct >= 75 else ("Low" if pct >= 50 else "Critical")

    # Today's status
    today_att = Attendance.query.filter_by(
        student_id=student.id, date=today
    ).first()

    # Calendar data (last 30 days)
    present_dates = {r.date for r in records}
    calendar_data = []
    for i in range(30):
        d = start_30 + timedelta(days=i)
        calendar_data.append({
            "date": d.strftime("%d"),
            "date_full": d.isoformat(),
            "day": d.strftime("%a"),
            "present": d in present_dates,
            "sunday": d.weekday() == 6,
            "today": d == today,
        })

    # Streak calculation
    streak = 0
    check_date = today
    while check_date >= start_30:
        if check_date.weekday() == 6:
            check_date -= timedelta(days=1)
            continue
        if check_date in present_dates:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    # Recent 5 records
    recent = records[:5]

    return render_template("student/dashboard.html",
                           student=student, active_page="my_dashboard",
                           pct=pct, days_present=days_present,
                           working_days=working, status=status,
                           today_marked=today_att is not None,
                           today_time=today_att.time_in.strftime("%I:%M %p") if today_att and today_att.time_in else None,
                           calendar=calendar_data, streak=streak,
                           recent=recent)


@student_dashboard_bp.route("/api/trend")
@role_required("student")
def api_my_trend():
    student = Student.query.get(g.user.student_id) if g.user.student_id else None
    if not student:
        return jsonify({"data": []})

    today = date.today()
    start = today - timedelta(days=29)
    records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.date >= start, Attendance.date <= today,
        Attendance.status == "Present"
    ).all()

    present_dates = {r.date for r in records}
    data = []
    for i in range(30):
        d = start + timedelta(days=i)
        data.append({
            "date": d.strftime("%d %b"),
            "present": 1 if d in present_dates else 0,
        })
    return jsonify({"data": data})
