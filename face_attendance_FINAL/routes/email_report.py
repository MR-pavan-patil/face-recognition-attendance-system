"""
routes/email_report.py — Email + PDF + Low Attendance Alerts
=============================================================
Features:
  1. PDF report generate karo (student-wise)
  2. Email pe daily/monthly attendance report bhejo
  3. Low attendance (< 75%) students ka alert
"""

import io, csv, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from datetime             import date, datetime, timedelta
from flask                import (Blueprint, render_template, request,
                                  jsonify, send_file, current_app)
from routes.auth          import login_required
from database             import db
from models               import Student, Attendance

email_bp = Blueprint("email_report", __name__, url_prefix="/email")




@email_bp.route("/")
@login_required
def email_alerts_page():
    """Email & Alerts page."""
    return render_template("reports/email_alerts.html", active_page="email")

# ─────────────────────────────────────────────────────────────
# HELPER: Get attendance stats for all students
# ─────────────────────────────────────────────────────────────
def get_all_student_stats(period_days=30):
    """Return list of dicts with attendance stats per student."""
    today = date.today()
    start = today - timedelta(days=period_days)

    students = Student.query.filter_by(is_active=True).order_by(Student.name).all()
    result   = []

    for s in students:
        records = Attendance.query.filter(
            Attendance.student_id == s.id,
            Attendance.date       >= start,
            Attendance.date       <= today,
            Attendance.status     == "Present",
        ).all()

        # Working days (Mon-Sat)
        working = sum(
            1 for i in range((today - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 6
        )
        days_present = len(records)
        pct          = round(days_present / working * 100, 1) if working > 0 else 0
        status       = "Good" if pct >= 75 else ("Low" if pct >= 50 else "Critical")

        result.append({
            "id"          : s.id,
            "name"        : s.name,
            "roll_number" : s.roll_number,
            "department"  : s.department,
            "year"        : s.year,
            "days_present": days_present,
            "working_days": working,
            "percentage"  : pct,
            "status"      : status,
        })

    return result


# ─────────────────────────────────────────────────────────────
# 1. PDF REPORT — Student-wise
# ─────────────────────────────────────────────────────────────
@email_bp.route("/pdf/student/<int:student_id>")
@login_required
def student_pdf(student_id):
    """Generate PDF report for one student."""
    student = Student.query.get_or_404(student_id)

    records = Attendance.query.filter_by(
        student_id=student_id, status="Present"
    ).order_by(Attendance.date.desc()).all()

    today        = date.today()
    days_present = len(records)

    # Working days since registration
    start   = student.registered_at.date() if student.registered_at else today
    working = sum(
        1 for i in range((today - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 6
    )
    pct    = round(days_present / working * 100, 1) if working > 0 else 0
    status = "Good" if pct >= 75 else ("Low" if pct >= 50 else "Critical")

    html = _build_student_pdf_html(student, records, days_present, working, pct, status, today)

    try:
        # Try weasyprint first
        from weasyprint import HTML as WPHTML
        pdf_bytes = WPHTML(string=html).write_pdf()
    except ImportError:
        # Fallback: return HTML as downloadable file
        buf = io.BytesIO(html.encode("utf-8"))
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"report_{student.roll_number}.html",
            mimetype="text/html",
        )

    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"report_{student.roll_number}_{today}.pdf",
        mimetype="application/pdf",
    )


@email_bp.route("/pdf/summary")
@login_required
def summary_pdf():
    """Generate PDF summary report for all students."""
    period = request.args.get("period", "30")
    days   = int(period) if period.isdigit() else 30
    stats  = get_all_student_stats(days)
    today  = date.today()

    html = _build_summary_pdf_html(stats, today, days)

    try:
        from weasyprint import HTML as WPHTML
        pdf_bytes = WPHTML(string=html).write_pdf()
        buf = io.BytesIO(pdf_bytes)
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"attendance_report_{today}.pdf",
                         mimetype="application/pdf")
    except ImportError:
        buf = io.BytesIO(html.encode("utf-8"))
        buf.seek(0)
        return send_file(buf, as_attachment=True,
                         download_name=f"attendance_report_{today}.html",
                         mimetype="text/html")


# ─────────────────────────────────────────────────────────────
# 2. LOW ATTENDANCE ALERT API
# ─────────────────────────────────────────────────────────────
@email_bp.route("/api/low-attendance")
@login_required
def api_low_attendance():
    """Return students with < 75% attendance."""
    threshold = current_app.config.get("LOW_ATTENDANCE_THRESHOLD", 75)
    stats     = get_all_student_stats(30)
    low       = [s for s in stats if s["percentage"] < threshold]
    low.sort(key=lambda x: x["percentage"])
    return jsonify({
        "threshold" : threshold,
        "total_low" : len(low),
        "students"  : low,
    })


# ─────────────────────────────────────────────────────────────
# 3. EMAIL REPORT
# ─────────────────────────────────────────────────────────────
@email_bp.route("/send", methods=["POST"])
@login_required
def send_report_email():
    """Send attendance report email."""
    data       = request.get_json()
    to_email   = data.get("to_email", "").strip()
    report_type = data.get("type", "daily")   # daily | monthly | low_attendance

    if not to_email or "@" not in to_email:
        return jsonify({"success": False, "error": "Valid email required"})

    cfg = current_app.config
    if cfg.get("MAIL_USERNAME") == "your_email@gmail.com":
        return jsonify({
            "success": False,
            "error"  : "Email not configured! Update MAIL_USERNAME and MAIL_PASSWORD in config.py"
        })

    try:
        today = date.today()

        if report_type == "daily":
            subject, body, csv_data = _build_daily_report(today)
        elif report_type == "monthly":
            subject, body, csv_data = _build_monthly_report(today)
        else:  # low_attendance
            subject, body, csv_data = _build_low_attendance_report(today)

        _send_email(cfg, to_email, subject, body, csv_data,
                    f"attendance_{report_type}_{today}.csv")

        return jsonify({"success": True,
                        "message": f"Report sent to {to_email} ✓"})

    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "success": False,
            "error"  : "Gmail authentication failed! Check App Password in config.py"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def _send_email(cfg, to_email, subject, body_html, csv_data, filename):
    """Send email with CSV attachment."""
    msg = MIMEMultipart("mixed")
    msg["From"]    = cfg["MAIL_FROM"]
    msg["To"]      = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html"))

    # Attach CSV
    if csv_data:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(csv_data.encode("utf-8"))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f'attachment; filename="{filename}"')
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as server:
        server.starttls(context=context)
        server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        server.sendmail(cfg["MAIL_FROM"], to_email, msg.as_string())


def _build_daily_report(today):
    """Today's attendance report."""
    records = (
        db.session.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .filter(Attendance.date == today, Attendance.status == "Present")
        .order_by(Student.name)
        .all()
    )
    total   = Student.query.filter_by(is_active=True).count()
    present = len(records)
    pct     = round(present / total * 100, 1) if total > 0 else 0

    subject = f"FaceAttend — Daily Report {today.strftime('%d %b %Y')}"
    body    = _email_template(
        title   = f"Daily Attendance — {today.strftime('%A, %d %B %Y')}",
        summary = f"Present: <b>{present}</b> / {total} students ({pct}%)",
        rows    = [(a.time_in.strftime('%I:%M %p') if a.time_in else '--',
                    s.name, s.roll_number, s.department, s.year)
                   for a, s in records],
        headers = ["Time", "Name", "Roll No", "Dept", "Year"],
    )
    # CSV
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["#", "Name", "Roll Number", "Department", "Year", "Time In"])
    for i, (a, s) in enumerate(records, 1):
        w.writerow([i, s.name, s.roll_number, s.department, s.year,
                    a.time_in.strftime('%I:%M %p') if a.time_in else '--'])
    return subject, body, buf.getvalue()


def _build_monthly_report(today):
    """Last 30 days summary report."""
    stats   = get_all_student_stats(30)
    subject = f"FaceAttend — Monthly Report {today.strftime('%B %Y')}"
    body    = _email_template(
        title   = f"Monthly Attendance — {today.strftime('%B %Y')}",
        summary = f"Period: Last 30 Days &nbsp;|&nbsp; {len(stats)} students",
        rows    = [(s["name"], s["roll_number"], s["department"],
                    f"{s['days_present']}/{s['working_days']}",
                    f"{s['percentage']}%", s["status"])
                   for s in stats],
        headers = ["Name", "Roll No", "Dept", "Present/Total", "%", "Status"],
    )
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["#","Name","Roll No","Department","Year","Present","Working Days","%","Status"])
    for i, s in enumerate(stats, 1):
        w.writerow([i, s["name"], s["roll_number"], s["department"], s["year"],
                    s["days_present"], s["working_days"], s["percentage"], s["status"]])
    return subject, body, buf.getvalue()


def _build_low_attendance_report(today):
    """Students below 75% attendance."""
    threshold = 75
    stats     = [s for s in get_all_student_stats(30) if s["percentage"] < threshold]
    stats.sort(key=lambda x: x["percentage"])
    subject   = f"⚠️ FaceAttend — Low Attendance Alert {today.strftime('%d %b %Y')}"
    body      = _email_template(
        title   = f"⚠️ Low Attendance Alert — {len(stats)} Students Below {threshold}%",
        summary = f"Students with attendance below <b>{threshold}%</b> in last 30 days",
        rows    = [(s["name"], s["roll_number"], s["department"],
                    f"{s['percentage']}%", s["status"])
                   for s in stats],
        headers = ["Name", "Roll No", "Dept", "%", "Status"],
        alert   = True,
    )
    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["#","Name","Roll No","Department","%","Status"])
    for i, s in enumerate(stats, 1):
        w.writerow([i, s["name"], s["roll_number"], s["department"],
                    s["percentage"], s["status"]])
    return subject, body, buf.getvalue()


def _email_template(title, summary, rows, headers, alert=False):
    color = "#ef4444" if alert else "#5294ff"
    rows_html = "".join(
        "<tr>" + "".join(f"<td style='padding:10px 14px;border-bottom:1px solid #1e293b;"
                         f"color:#94a3c0;font-size:13px'>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    header_html = "".join(
        f"<th style='padding:10px 14px;text-align:left;color:#5294ff;"
        f"font-size:11px;text-transform:uppercase;letter-spacing:.8px'>{h}</th>"
        for h in headers
    )
    return f"""<!DOCTYPE html><html><body style='background:#080c14;margin:0;padding:20px;
font-family:Inter,sans-serif'>
<div style='max-width:700px;margin:0 auto;background:#0f1621;border-radius:16px;
     border:1px solid #1e293b;overflow:hidden'>
  <div style='background:linear-gradient(135deg,#0d1421,#1a2436);padding:28px 32px;
       border-bottom:1px solid #1e293b'>
    <div style='font-size:22px;font-weight:800;color:#edf2ff;font-family:Poppins,sans-serif'>
      FaceAttend
    </div>
    <div style='font-size:18px;font-weight:700;color:{color};margin-top:8px'>{title}</div>
    <div style='color:#94a3c0;font-size:13px;margin-top:6px'>{summary}</div>
  </div>
  <div style='padding:24px 32px'>
    <table style='width:100%;border-collapse:collapse'>
      <thead><tr style='background:#131920'>{header_html}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    {'<p style="color:#ef4444;font-size:13px;margin-top:20px;padding:14px;background:rgba(239,68,68,0.1);border-radius:8px;border:1px solid rgba(239,68,68,0.2)">⚠️ Action required: Please contact students with low attendance.</p>' if alert else ''}
  </div>
  <div style='padding:18px 32px;border-top:1px solid #1e293b;color:#4e6080;font-size:12px'>
    Sent by FaceAttend — BCA Final Year Project &nbsp;|&nbsp; {datetime.now().strftime('%d %b %Y %I:%M %p')}
  </div>
</div></body></html>"""


# ─────────────────────────────────────────────────────────────
# PDF HTML BUILDERS
# ─────────────────────────────────────────────────────────────
def _build_student_pdf_html(student, records, days_present, working, pct, status, today):
    color = "#22c55e" if pct >= 75 else ("#f59e0b" if pct >= 50 else "#ef4444")
    rows  = "".join(
        f"<tr><td>{i}</td><td>{r.date.strftime('%d %b %Y')}</td>"
        f"<td>{r.date.strftime('%A')}</td>"
        f"<td>{r.time_in.strftime('%I:%M %p') if r.time_in else '--'}</td>"
        f"<td style='color:#22c55e;font-weight:600'>Present</td></tr>"
        for i, r in enumerate(records, 1)
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<style>
  body{{font-family:Arial,sans-serif;background:#fff;color:#1e293b;margin:0;padding:32px}}
  h1{{color:#1e40af;font-size:24px;margin-bottom:4px}}
  .subtitle{{color:#64748b;font-size:14px;margin-bottom:24px}}
  .info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}}
  .info-box{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px}}
  .info-label{{font-size:11px;text-transform:uppercase;color:#94a3b8;letter-spacing:.8px}}
  .info-value{{font-size:18px;font-weight:700;color:#1e293b;margin-top:4px}}
  .stat-pct{{font-size:32px;font-weight:800;color:{color}}}
  table{{width:100%;border-collapse:collapse;margin-top:16px}}
  th{{background:#1e40af;color:#fff;padding:10px 14px;text-align:left;font-size:12px}}
  td{{padding:9px 14px;border-bottom:1px solid #e2e8f0;font-size:13px}}
  tr:nth-child(even){{background:#f8fafc}}
  .footer{{margin-top:32px;color:#94a3b8;font-size:11px;text-align:center}}
</style></head>
<body>
  <h1>Student Attendance Report</h1>
  <div class="subtitle">Generated: {today.strftime('%d %B %Y')} &nbsp;|&nbsp; FaceAttend BCA Project</div>

  <div class="info-grid">
    <div class="info-box">
      <div class="info-label">Student Name</div>
      <div class="info-value">{student.name}</div>
      <div style="color:#64748b;font-size:13px;margin-top:4px">
        {student.roll_number} &nbsp;|&nbsp; {student.department} &nbsp;|&nbsp; {student.year}
      </div>
    </div>
    <div class="info-box" style="text-align:center">
      <div class="info-label">Attendance</div>
      <div class="stat-pct">{pct}%</div>
      <div style="color:#64748b;font-size:13px">{days_present} present / {working} working days</div>
      <div style="color:{color};font-weight:700;font-size:14px;margin-top:4px">{status}</div>
    </div>
  </div>

  <table>
    <thead><tr><th>#</th><th>Date</th><th>Day</th><th>Time In</th><th>Status</th></tr></thead>
    <tbody>{rows if rows else '<tr><td colspan="5" style="text-align:center;color:#94a3b8">No records found</td></tr>'}</tbody>
  </table>
  <div class="footer">FaceAttend — BCA Final Year Project &nbsp;|&nbsp; {today.strftime('%Y')}</div>
</body></html>"""


def _build_summary_pdf_html(stats, today, days):
    rows = "".join(
        f"<tr><td>{i}</td><td>{s['name']}</td><td>{s['roll_number']}</td>"
        f"<td>{s['department']}</td><td>{s['days_present']}/{s['working_days']}</td>"
        f"<td style='font-weight:700;color:{'#22c55e' if s['percentage']>=75 else ('#f59e0b' if s['percentage']>=50 else '#ef4444')}'>"
        f"{s['percentage']}%</td>"
        f"<td style='color:{'#22c55e' if s['status']=='Good' else ('#f59e0b' if s['status']=='Low' else '#ef4444')}'>"
        f"{s['status']}</td></tr>"
        for i, s in enumerate(stats, 1)
    )
    low_count  = sum(1 for s in stats if s["percentage"] < 75)
    good_count = sum(1 for s in stats if s["percentage"] >= 75)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<style>
  body{{font-family:Arial,sans-serif;margin:0;padding:32px;color:#1e293b}}
  h1{{color:#1e40af;font-size:22px}}
  .stats{{display:flex;gap:16px;margin:20px 0}}
  .stat{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
         padding:14px 20px;flex:1;text-align:center}}
  .stat-v{{font-size:24px;font-weight:800}}
  .stat-l{{font-size:11px;color:#94a3b8;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse}}
  th{{background:#1e40af;color:#fff;padding:9px 12px;text-align:left;font-size:12px}}
  td{{padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px}}
  tr:nth-child(even){{background:#f8fafc}}
</style></head>
<body>
  <h1>Attendance Summary Report</h1>
  <p style="color:#64748b">Last {days} days &nbsp;|&nbsp; Generated: {today.strftime('%d %B %Y')}</p>
  <div class="stats">
    <div class="stat"><div class="stat-v">{len(stats)}</div><div class="stat-l">Total Students</div></div>
    <div class="stat"><div class="stat-v" style="color:#22c55e">{good_count}</div><div class="stat-l">Above 75%</div></div>
    <div class="stat"><div class="stat-v" style="color:#ef4444">{low_count}</div><div class="stat-l">Below 75%</div></div>
  </div>
  <table>
    <thead><tr><th>#</th><th>Name</th><th>Roll No</th><th>Dept</th><th>Present/Total</th><th>%</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="color:#94a3b8;font-size:11px;text-align:center;margin-top:24px">FaceAttend — BCA Final Year Project</p>
</body></html>"""
