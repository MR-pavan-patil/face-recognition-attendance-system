"""
app.py — FaceAttend Main Application (Final)
"""
import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, jsonify, redirect, url_for, session
from config  import Config
from database import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(hours=8)

    os.makedirs(app.config["UPLOAD_FOLDER"],  exist_ok=True)
    os.makedirs(app.config["DATASET_FOLDER"], exist_ok=True)

    db.init_app(app)

    # ── Register all blueprints ───────────────────────────────
    from routes.auth        import auth_bp
    from routes.students    import students_bp
    from routes.capture     import capture_bp
    from routes.attendance  import attendance_bp
    from routes.reports     import reports_bp
    from routes.recognition  import recognition_bp
    from routes.email_report import email_bp
    from routes.settings    import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(capture_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(recognition_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(settings_bp)

    with app.app_context():
        db.create_all()
        print("  ✓ Database tables verified")

    register_routes(app)
    return app


def register_routes(app):
    from routes.auth import login_required

    @app.route("/")
    @app.route("/dashboard")
    @login_required
    def dashboard():
        from models   import Student, Attendance
        from database import db as _db

        today         = date.today()
        total         = Student.query.filter_by(is_active=True).count()
        present_today = Attendance.query.filter_by(date=today, status="Present").count()
        dataset_ready = Student.query.filter_by(dataset_ready=True).count()

        # Weekly chart — last 7 days
        weekly = []
        for i in range(6, -1, -1):
            d   = today - timedelta(days=i)
            cnt = Attendance.query.filter_by(date=d, status="Present").count()
            weekly.append({
                "day"    : d.strftime("%a"),
                "present": cnt,
                "absent" : max(total - cnt, 0),
            })

        # Recent 5 marked today
        recent = (
            _db.session.query(Attendance, Student)
            .join(Student, Attendance.student_id == Student.id)
            .filter(Attendance.date == today)
            .order_by(Attendance.time_in.desc())
            .limit(5).all()
        )

        stats = {
            "total_students"        : total,
            "present_today"         : present_today,
            "absent"          : max(total - present_today, 0),
            "attendance_percentage" : round(present_today / total * 100, 1) if total > 0 else 0,
            "today_date"            : today.strftime("%B %d, %Y"),
            "day_name"              : today.strftime("%A"),
            "dataset_ready"         : dataset_ready,
        }
        return render_template("dashboard.html",
                               stats=stats, weekly=weekly,
                               recent=recent, now=datetime.now(),
                               active_page="dashboard")

    @app.route("/recognition")
    @login_required
    def recognition():
        return redirect(url_for("recognition.index"))

    @app.route("/api/stats")
    @login_required
    def api_stats():
        from models import Student, Attendance
        total   = Student.query.filter_by(is_active=True).count()
        today   = date.today()
        present = Attendance.query.filter_by(date=today, status="Present").count()
        return jsonify({
            "total_students"        : total,
            "present_today"         : present,
            "absent"          : max(total - present, 0),
            "attendance_percentage" : round(present / total * 100, 1) if total > 0 else 0,
        })

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500


app = create_app()

if __name__ == "__main__":
    print("\n" + "="*52)
    print("  FaceAttend — Final System")
    print("  URL    : http://127.0.0.1:5000")
    print("  Login  : admin / admin123")
    print("="*52 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
