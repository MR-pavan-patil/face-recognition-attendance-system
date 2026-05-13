"""
routes/analytics.py — Advanced Analytics Dashboard
====================================================
Interactive charts: trends, heatmap, dept comparison,
monthly averages, status distribution, top/bottom students.
"""

from datetime import date, datetime, timedelta
from collections import defaultdict

from flask import Blueprint, render_template, request, jsonify, g
from database import db
from models import Student, Attendance, ROLE_ADMIN, ROLE_TEACHER, ROLE_STUDENT
from routes.auth import login_required

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


def _dept_filter(query_model=None):
    """Return dept filter based on role. Admin=None, Teacher=own dept."""
    role = g.user.role if hasattr(g, 'user') and g.user else "admin"
    if role == ROLE_TEACHER and g.user.department:
        return g.user.department
    return None


def _filtered_students(dept=None):
    """Get students optionally filtered by department."""
    q = Student.query.filter_by(is_active=True)
    if dept:
        q = q.filter_by(department=dept)
    return q


# ── Main Analytics Page ───────────────────────────────────────
@analytics_bp.route("/")
@login_required
def index():
    dept = _dept_filter()
    students = _filtered_students(dept).all()
    total = len(students)

    today = date.today()
    present_today = Attendance.query.filter_by(date=today, status="Present")
    if dept:
        present_today = present_today.join(Student).filter(Student.department == dept)
    present_count = present_today.count()

    # 30-day stats
    start_30 = today - timedelta(days=29)
    att_30 = Attendance.query.filter(
        Attendance.date >= start_30, Attendance.date <= today, Attendance.status == "Present"
    )
    if dept:
        att_30 = att_30.join(Student).filter(Student.department == dept)
    att_30_list = att_30.all()

    # Per-student 30-day
    present_lookup = defaultdict(int)
    for a in att_30_list:
        present_lookup[a.student_id] += 1

    working_30 = sum(1 for i in range(30) if (start_30 + timedelta(days=i)).weekday() < 6)
    good = low = critical = 0
    for s in students:
        pct = round(present_lookup[s.id] / working_30 * 100, 1) if working_30 > 0 else 0
        if pct >= 75: good += 1
        elif pct >= 50: low += 1
        else: critical += 1

    avg_pct = round(sum(present_lookup[s.id] for s in students) / (total * working_30) * 100, 1) if total > 0 and working_30 > 0 else 0

    all_depts = [r[0] for r in db.session.query(Student.department)
                 .filter_by(is_active=True).distinct().all()]

    return render_template(
        "analytics/index.html",
        active_page="analytics",
        total_students=total,
        present_today=present_count,
        avg_pct=avg_pct,
        good_count=good,
        low_count=low,
        critical_count=critical,
        all_depts=sorted(all_depts),
        user_dept=dept,
    )


# ── API: Attendance Trend (30 days) ──────────────────────────
@analytics_bp.route("/api/trends")
@login_required
def api_trends():
    dept = request.args.get("dept") or _dept_filter()
    days = int(request.args.get("days", 30))
    today = date.today()
    start = today - timedelta(days=days - 1)

    total = _filtered_students(dept).count()
    att = Attendance.query.filter(
        Attendance.date >= start, Attendance.date <= today, Attendance.status == "Present"
    )
    if dept and dept != "all":
        att = att.join(Student).filter(Student.department == dept)
    records = att.all()

    by_date = defaultdict(int)
    for r in records:
        by_date[r.date] += 1

    data = []
    for i in range(days):
        d = start + timedelta(days=i)
        cnt = by_date.get(d, 0)
        data.append({
            "date": d.strftime("%d %b"),
            "date_full": d.isoformat(),
            "present": cnt,
            "absent": max(total - cnt, 0),
            "pct": round(cnt / total * 100, 1) if total > 0 else 0,
        })
    return jsonify({"total": total, "data": data})


# ── API: Department Comparison ────────────────────────────────
@analytics_bp.route("/api/department")
@login_required
def api_department():
    today = date.today()
    start = today - timedelta(days=29)
    working = sum(1 for i in range(30) if (start + timedelta(days=i)).weekday() < 6)

    students = Student.query.filter_by(is_active=True).all()
    att_records = Attendance.query.filter(
        Attendance.date >= start, Attendance.date <= today, Attendance.status == "Present"
    ).all()

    present_lookup = defaultdict(set)
    for a in att_records:
        present_lookup[a.student_id].add(a.date)

    dept_data = defaultdict(lambda: {"total": 0, "present_sum": 0})
    for s in students:
        dept_data[s.department]["total"] += 1
        dept_data[s.department]["present_sum"] += len(present_lookup[s.id])

    result = []
    for dept_name, vals in sorted(dept_data.items()):
        max_possible = vals["total"] * working
        pct = round(vals["present_sum"] / max_possible * 100, 1) if max_possible > 0 else 0
        result.append({
            "department": dept_name,
            "students": vals["total"],
            "pct": pct,
        })
    result.sort(key=lambda x: x["pct"], reverse=True)
    return jsonify(result)


# ── API: Weekly Heatmap ───────────────────────────────────────
@analytics_bp.route("/api/heatmap")
@login_required
def api_heatmap():
    dept = request.args.get("dept") or _dept_filter()
    today = date.today()
    start = today - timedelta(days=59)  # Last 2 months

    att = Attendance.query.filter(
        Attendance.date >= start, Attendance.date <= today, Attendance.status == "Present"
    )
    if dept and dept != "all":
        att = att.join(Student).filter(Student.department == dept)
    records = att.all()

    total = _filtered_students(dept).count()
    # Group by day-of-week and hour
    heatmap = defaultdict(lambda: defaultdict(int))
    day_counts = defaultdict(lambda: defaultdict(int))

    for r in records:
        dow = r.date.weekday()  # 0=Mon, 6=Sun
        hour_slot = "morning"
        if r.time_in:
            h = r.time_in.hour if hasattr(r.time_in, 'hour') else 9
            if h < 9:
                hour_slot = "early"
            elif h < 11:
                hour_slot = "morning"
            elif h < 14:
                hour_slot = "afternoon"
            else:
                hour_slot = "late"
        else:
            hour_slot = "morning"
        heatmap[dow][hour_slot] += 1
        day_counts[dow]["total"] += 1

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    slots = ["early", "morning", "afternoon", "late"]
    result = []
    for di, day_name in enumerate(days):
        for slot in slots:
            count = heatmap[di][slot]
            result.append({
                "day": day_name,
                "slot": slot,
                "count": count,
                "intensity": min(count / max(total, 1), 1.0),
            })

    return jsonify(result)


# ── API: Monthly Averages ─────────────────────────────────────
@analytics_bp.route("/api/monthly-avg")
@login_required
def api_monthly_avg():
    dept = request.args.get("dept") or _dept_filter()
    today = date.today()

    result = []
    for i in range(6):  # Last 6 months
        if today.month - i > 0:
            m = today.month - i
            y = today.year
        else:
            m = today.month - i + 12
            y = today.year - 1

        month_start = date(y, m, 1)
        if m == 12:
            month_end = date(y, 12, 31)
        else:
            month_end = date(y, m + 1, 1) - timedelta(days=1)

        if month_end > today:
            month_end = today

        working = sum(1 for d_i in range((month_end - month_start).days + 1)
                      if (month_start + timedelta(days=d_i)).weekday() < 6)
        total = _filtered_students(dept).count()

        att = Attendance.query.filter(
            Attendance.date >= month_start, Attendance.date <= month_end,
            Attendance.status == "Present"
        )
        if dept and dept != "all":
            att = att.join(Student).filter(Student.department == dept)
        present_count = att.count()

        max_possible = total * working
        pct = round(present_count / max_possible * 100, 1) if max_possible > 0 else 0
        result.append({
            "month": month_start.strftime("%b %Y"),
            "month_short": month_start.strftime("%b"),
            "pct": pct,
            "present": present_count,
            "working": working,
        })

    result.reverse()
    return jsonify(result)


# ── API: Top / Bottom Students ────────────────────────────────
@analytics_bp.route("/api/top-students")
@login_required
def api_top_students():
    dept = request.args.get("dept") or _dept_filter()
    today = date.today()
    start = today - timedelta(days=29)
    working = sum(1 for i in range(30) if (start + timedelta(days=i)).weekday() < 6)

    students = _filtered_students(dept).all()
    att_records = Attendance.query.filter(
        Attendance.date >= start, Attendance.date <= today, Attendance.status == "Present"
    ).all()

    present_lookup = defaultdict(int)
    for a in att_records:
        present_lookup[a.student_id] += 1

    stats = []
    for s in students:
        pct = round(present_lookup[s.id] / working * 100, 1) if working > 0 else 0
        stats.append({
            "id": s.id, "name": s.name, "roll_number": s.roll_number,
            "department": s.department, "pct": pct,
            "days_present": present_lookup[s.id],
        })

    stats.sort(key=lambda x: x["pct"], reverse=True)
    return jsonify({
        "top": stats[:5],
        "bottom": list(reversed(stats[-5:])) if len(stats) >= 5 else list(reversed(stats)),
        "working_days": working,
    })


# ── API: Status Distribution ─────────────────────────────────
@analytics_bp.route("/api/status-distribution")
@login_required
def api_status_distribution():
    dept = request.args.get("dept") or _dept_filter()
    today = date.today()
    start = today - timedelta(days=29)
    working = sum(1 for i in range(30) if (start + timedelta(days=i)).weekday() < 6)

    students = _filtered_students(dept).all()
    att_records = Attendance.query.filter(
        Attendance.date >= start, Attendance.date <= today, Attendance.status == "Present"
    ).all()

    present_lookup = defaultdict(int)
    for a in att_records:
        present_lookup[a.student_id] += 1

    good = low = critical = 0
    for s in students:
        pct = round(present_lookup[s.id] / working * 100, 1) if working > 0 else 0
        if pct >= 75: good += 1
        elif pct >= 50: low += 1
        else: critical += 1

    return jsonify({"good": good, "low": low, "critical": critical})


# ── API: On-Time Distribution ─────────────────────────────────
@analytics_bp.route("/api/time-distribution")
@login_required
def api_time_distribution():
    dept = request.args.get("dept") or _dept_filter()
    today = date.today()
    start = today - timedelta(days=29)

    att = Attendance.query.filter(
        Attendance.date >= start, Attendance.date <= today, Attendance.status == "Present"
    )
    if dept and dept != "all":
        att = att.join(Student).filter(Student.department == dept)
    records = att.all()

    buckets = {"Before 9 AM": 0, "9-10 AM": 0, "10-11 AM": 0,
               "11 AM-12 PM": 0, "After 12 PM": 0}
    for r in records:
        if not r.time_in:
            buckets["9-10 AM"] += 1
            continue
        h = r.time_in.hour if hasattr(r.time_in, 'hour') else 9
        if h < 9: buckets["Before 9 AM"] += 1
        elif h < 10: buckets["9-10 AM"] += 1
        elif h < 11: buckets["10-11 AM"] += 1
        elif h < 12: buckets["11 AM-12 PM"] += 1
        else: buckets["After 12 PM"] += 1

    return jsonify([{"label": k, "count": v} for k, v in buckets.items()])
