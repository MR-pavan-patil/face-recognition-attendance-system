"""
routes/reports.py — Reports Blueprint (Day 8)
===============================================
Routes:
  GET  /reports/                  → Summary report (weekly/monthly)
  GET  /reports/student/<id>      → Per-student attendance report
  GET  /reports/export/csv        → Download full CSV
  GET  /reports/export/student/<id>/csv → Per-student CSV
  GET  /reports/api/summary       → JSON summary data
"""

import csv
import io
from datetime import date, datetime, timedelta
from collections import defaultdict

from flask import (Blueprint, render_template, request,
                   jsonify, Response, make_response)
from database import db
from models   import Student, Attendance
from routes.auth import login_required

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def get_date_range(period="week"):
    """Return (start_date, end_date) for given period."""
    today = date.today()
    if period == "week":
        start = today - timedelta(days=today.weekday())   # Monday
        end   = start + timedelta(days=6)                 # Sunday
    elif period == "month":
        start = today.replace(day=1)
        # last day of month
        if today.month == 12:
            end = today.replace(day=31)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    elif period == "last30":
        start = today - timedelta(days=29)
        end   = today
    else:
        start = today
        end   = today
    return start, end


def get_working_days(start_date, end_date):
    """Count working days (Mon–Sat) between two dates inclusive."""
    count = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 6:   # 0=Mon … 5=Sat, 6=Sun
            count += 1
        current += timedelta(days=1)
    return max(count, 1)


def get_all_dates_in_range(start_date, end_date):
    """Return list of all dates from start to end inclusive."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


# ─────────────────────────────────────────────────────────────
#  MAIN REPORTS PAGE
# ─────────────────────────────────────────────────────────────
@reports_bp.route("/") 
@login_required
def summary():
    period = request.args.get("period", "week")
    dept   = request.args.get("dept",   "all")

    start_date, end_date = get_date_range(period)
    working_days         = get_working_days(start_date, end_date)
    all_dates            = get_all_dates_in_range(start_date, end_date)

    # All active students (filter by dept if needed)
    student_query = Student.query.filter_by(is_active=True)
    if dept != "all":
        student_query = student_query.filter_by(department=dept)
    students = student_query.order_by(Student.name).all()

    # All attendance in range
    att_records = (
        Attendance.query
        .filter(Attendance.date >= start_date,
                Attendance.date <= end_date)
        .all()
    )

    # Build lookup: {student_id: set of dates present}
    present_lookup = defaultdict(set)
    for att in att_records:
        present_lookup[att.student_id].add(att.date)

    # Per-student stats
    student_stats = []
    total_pct_sum = 0
    for stu in students:
        days_present = len(present_lookup[stu.id])
        pct          = round((days_present / working_days) * 100, 1)
        total_pct_sum += pct
        student_stats.append({
            "id"          : stu.id,
            "name"        : stu.name,
            "roll_number" : stu.roll_number,
            "department"  : stu.department,
            "year"        : stu.year,
            "days_present": days_present,
            "working_days": working_days,
            "percentage"  : pct,
            "status"      : "Good" if pct >= 75 else ("Low" if pct >= 50 else "Critical"),
        })

    # Sort by percentage descending
    student_stats.sort(key=lambda x: x["percentage"], reverse=True)

    # Overall summary
    total_students  = len(students)
    avg_attendance  = round(total_pct_sum / total_students, 1) if total_students > 0 else 0
    good_count      = sum(1 for s in student_stats if s["status"] == "Good")
    low_count       = sum(1 for s in student_stats if s["status"] == "Low")
    critical_count  = sum(1 for s in student_stats if s["status"] == "Critical")

    # Daily attendance count for chart
    daily_counts = []
    for d in all_dates:
        count = sum(1 for att in att_records if att.date == d)
        daily_counts.append({
            "date"    : d.strftime("%d %b"),
            "present" : count,
            "absent"  : total_students - count,
        })

    # Department-wise stats
    dept_stats = defaultdict(lambda: {"total": 0, "present_days": 0})
    for stu in students:
        dept_stats[stu.department]["total"] += 1
        dept_stats[stu.department]["present_days"] += len(present_lookup[stu.id])

    dept_summary = []
    for dept_name, vals in sorted(dept_stats.items()):
        max_days = vals["total"] * working_days
        pct      = round((vals["present_days"] / max_days * 100), 1) if max_days > 0 else 0
        dept_summary.append({"dept": dept_name, "pct": pct, "total": vals["total"]})

    # All departments for filter dropdown
    all_depts = [r[0] for r in db.session.query(Student.department).distinct().all()]

    return render_template(
        "reports/summary.html",
        active_page    = "reports",
        period         = period,
        selected_dept  = dept,
        all_depts      = sorted(all_depts),
        start_date     = start_date,
        end_date       = end_date,
        working_days   = working_days,
        student_stats  = student_stats,
        total_students = total_students,
        avg_attendance = avg_attendance,
        good_count     = good_count,
        low_count      = low_count,
        critical_count = critical_count,
        daily_counts   = daily_counts,
        dept_summary   = dept_summary,
    )


# ─────────────────────────────────────────────────────────────
#  PER-STUDENT REPORT
# ─────────────────────────────────────────────────────────────
@reports_bp.route("/student/<int:student_id>")
def student_report(student_id):
    student = Student.query.get_or_404(student_id)
    period  = request.args.get("period", "month")

    start_date, end_date = get_date_range(period)
    working_days         = get_working_days(start_date, end_date)

    records = (
        Attendance.query
        .filter_by(student_id=student_id)
        .filter(Attendance.date >= start_date,
                Attendance.date <= end_date)
        .order_by(Attendance.date.desc())
        .all()
    )

    days_present = len(records)
    pct          = round((days_present / working_days) * 100, 1)

    # Calendar data: all dates in range with present/absent
    all_dates   = get_all_dates_in_range(start_date, end_date)
    present_set = {r.date for r in records}
    calendar    = []
    for d in all_dates:
        calendar.append({
            "date"   : d,
            "present": d in present_set,
            "sunday" : d.weekday() == 6,
        })

    # All-time stats
    all_records   = Attendance.query.filter_by(student_id=student_id).all()
    total_present = len(all_records)
    first_date    = min((r.date for r in all_records), default=date.today())

    return render_template(
        "reports/student_report.html",
        active_page   = "reports",
        student       = student,
        period        = period,
        start_date    = start_date,
        end_date      = end_date,
        working_days  = working_days,
        days_present  = days_present,
        percentage    = pct,
        records       = records,
        calendar      = calendar,
        total_present = total_present,
        first_date    = first_date,
    )


# ─────────────────────────────────────────────────────────────
#  CSV EXPORT — FULL
# ─────────────────────────────────────────────────────────────
@reports_bp.route("/export/csv")
def export_csv():
    """Download full attendance as CSV."""
    period = request.args.get("period", "month")
    dept   = request.args.get("dept",   "all")

    start_date, end_date = get_date_range(period)
    working_days         = get_working_days(start_date, end_date)

    student_query = Student.query.filter_by(is_active=True)
    if dept != "all":
        student_query = student_query.filter_by(department=dept)
    students = student_query.order_by(Student.department, Student.name).all()

    att_records = (
        Attendance.query
        .filter(Attendance.date >= start_date,
                Attendance.date <= end_date)
        .all()
    )

    present_lookup = defaultdict(set)
    for att in att_records:
        present_lookup[att.student_id].add(att.date)

    # Get all dates for header
    all_dates = get_all_dates_in_range(start_date, end_date)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ["#", "Name", "Roll Number", "Department", "Year",
              "Days Present", f"Working Days ({working_days})", "Attendance %", "Status"]
    for d in all_dates:
        header.append(d.strftime("%d-%b"))
    writer.writerow(header)

    # Data rows
    for i, stu in enumerate(students, 1):
        days_present = len(present_lookup[stu.id])
        pct          = round((days_present / working_days) * 100, 1)
        status       = "Good" if pct >= 75 else ("Low" if pct >= 50 else "Critical")

        row = [i, stu.name, stu.roll_number, stu.department,
               stu.year, days_present, working_days, f"{pct}%", status]

        for d in all_dates:
            row.append("P" if d in present_lookup[stu.id] else "A")

        writer.writerow(row)

    # Footer row
    if students:
        total_p = sum(len(present_lookup[s.id]) for s in students)
        max_p   = len(students) * working_days
        overall = round(total_p / max_p * 100, 1) if max_p > 0 else 0
        writer.writerow([])
        writer.writerow(["", "OVERALL AVERAGE", "", "", "",
                         total_p, max_p, f"{overall}%", ""])

    output.seek(0)
    filename = f"attendance_{start_date}_{end_date}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─────────────────────────────────────────────────────────────
#  CSV EXPORT — PER STUDENT
# ─────────────────────────────────────────────────────────────
@reports_bp.route("/export/student/<int:student_id>/csv")
def export_student_csv(student_id):
    """Download individual student attendance as CSV."""
    student    = Student.query.get_or_404(student_id)
    period     = request.args.get("period", "month")
    start_date, end_date = get_date_range(period)
    working_days = get_working_days(start_date, end_date)

    records = (
        Attendance.query
        .filter_by(student_id=student_id)
        .filter(Attendance.date >= start_date,
                Attendance.date <= end_date)
        .order_by(Attendance.date)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["FaceAttend — Student Attendance Report"])
    writer.writerow(["Name",        student.name])
    writer.writerow(["Roll Number", student.roll_number])
    writer.writerow(["Department",  student.department])
    writer.writerow(["Period",      f"{start_date} to {end_date}"])
    writer.writerow([])
    writer.writerow(["Date", "Day", "Status", "Time In", "Marked By"])

    present_dates = {r.date for r in records}
    all_dates     = get_all_dates_in_range(start_date, end_date)
    att_lookup    = {r.date: r for r in records}

    for d in all_dates:
        if d.weekday() == 6:
            status = "Sunday"
            time_in = "--"
            by      = "--"
        elif d in present_dates:
            r       = att_lookup[d]
            status  = "Present"
            time_in = r.time_in.strftime("%I:%M %p") if r.time_in else "--"
            by      = r.marked_by
        else:
            status  = "Absent"
            time_in = "--"
            by      = "--"

        writer.writerow([
            d.strftime("%d %B %Y"),
            d.strftime("%A"),
            status, time_in, by
        ])

    writer.writerow([])
    writer.writerow(["Days Present",   len(records)])
    writer.writerow(["Working Days",   working_days])
    writer.writerow(["Attendance %",
                     f"{round(len(records)/working_days*100,1)}%"])

    output.seek(0)
    filename = f"{student.roll_number}_attendance_{start_date}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─────────────────────────────────────────────────────────────
#  JSON API — for dashboard chart
# ─────────────────────────────────────────────────────────────
@reports_bp.route("/api/summary")
def api_summary():
    period = request.args.get("period", "week")
    start_date, end_date = get_date_range(period)
    total   = Student.query.filter_by(is_active=True).count()
    records = (
        Attendance.query
        .filter(Attendance.date >= start_date,
                Attendance.date <= end_date)
        .all()
    )
    all_dates = get_all_dates_in_range(start_date, end_date)
    daily = []
    for d in all_dates:
        count = sum(1 for r in records if r.date == d)
        daily.append({
            "date"   : d.strftime("%d %b"),
            "present": count,
            "absent" : max(total - count, 0),
        })
    return jsonify({"period": period, "total": total, "daily": daily})

@reports_bp.route("/api/student/<int:student_id>")
@login_required
def api_student_stats(student_id):
    """Quick stats for student detail page."""
    from models import Student, Attendance
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False})

    records = Attendance.query.filter_by(
        student_id=student_id, status="Present"
    ).order_by(Attendance.date.desc()).all()

    days_present = len(records)
    last_seen    = records[0].date.strftime("%d %b %Y") if records else None

    # Working days since registration
    from datetime import date
    start = student.registered_at.date() if student.registered_at else date.today()
    total_days = (date.today() - start).days + 1
    working    = sum(1 for i in range(total_days)
                     if (start + __import__('datetime').timedelta(days=i)).weekday() < 6)
    pct = round(days_present / working * 100, 1) if working > 0 else 0

    return jsonify({
        "success"     : True,
        "days_present": days_present,
        "working_days": working,
        "percentage"  : pct,
        "last_seen"   : last_seen,
    })

