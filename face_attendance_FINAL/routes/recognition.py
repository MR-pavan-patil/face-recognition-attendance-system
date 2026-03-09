"""
routes/recognition.py — Web Face Recognition (Final Fixed)
"""
import os, base64, pickle
import numpy as np
from datetime import date, datetime
from flask import Blueprint, render_template, request, jsonify
from routes.auth import login_required

recognition_bp = Blueprint("recognition", __name__, url_prefix="/recognition")

ENCODINGS_FILE = "encodings.pickle"
TOLERANCE      = 0.68   # More lenient for mobile camera
MIN_CONF       = 25     # Low threshold — mobile angle varies a lot

_enc_cache   = None
_names_cache = None


def load_encodings(force=False):
    global _enc_cache, _names_cache
    if _enc_cache is not None and not force:
        return _enc_cache, _names_cache
    if not os.path.exists(ENCODINGS_FILE):
        return None, None
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
        _enc_cache   = data["encodings"]
        _names_cache = data["names"]
        return _enc_cache, _names_cache
    except Exception:
        return None, None


def decode_frame(b64):
    """Decode base64 → clean RGB numpy array"""
    try:
        import cv2
        if "," in b64:
            b64 = b64.split(",")[1]
        arr = np.frombuffer(base64.b64decode(b64), np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        # Enhance contrast slightly for better detection
        lab   = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l     = clahe.apply(l)
        bgr   = cv2.cvtColor(cv2.merge([l, a, b_ch]), cv2.COLOR_LAB2BGR)
        rgb   = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)
        return rgb
    except Exception:
        return None


# ── Main Page ─────────────────────────────────────────────────
@recognition_bp.route("/")
@login_required
def index():
    enc, names = load_encodings()
    from collections import Counter
    from models import Attendance
    today = date.today()
    return render_template(
        "recognition/index.html",
        active_page     = "recognition",
        encodings_ready = enc is not None and len(enc) > 0,
        known_count     = len(Counter(names)) if names else 0,
        marked_today    = Attendance.query.filter_by(date=today).count(),
    )


# ── API: Recognize ────────────────────────────────────────────
@recognition_bp.route("/api/recognize", methods=["POST"])
@login_required
def api_recognize():
    try:
        import face_recognition, cv2
    except ImportError:
        return jsonify({"status": "error", "message": "face_recognition not installed"}), 500

    data = request.get_json()
    if not data or "frame" not in data:
        return jsonify({"status": "error", "message": "No frame"}), 400

    rgb = decode_frame(data["frame"])
    if rgb is None:
        return jsonify({"status": "error", "message": "Cannot decode image"})

    enc, names = load_encodings()
    if enc is None:
        return jsonify({"status": "no_encodings",
                        "message": "Encodings not ready. Capture photos first!"})

    try:
        h, w = rgb.shape[:2]
        # Resize for speed if too large
        if w > 640:
            scale = 640 / w
            small = cv2.resize(rgb, (640, int(h * scale)))
            small = np.ascontiguousarray(small, dtype=np.uint8)
        else:
            small = rgb

        locs = face_recognition.face_locations(small, model="hog")
        if not locs:
            locs = face_recognition.face_locations(
                small, number_of_times_to_upsample=2, model="hog"
            )
        if not locs:
            return jsonify({"status": "no_face",
                            "message": "No face detected — move closer & face the camera"})

        encodings = face_recognition.face_encodings(small, locs,
                                                     num_jitters=2)  # More accurate
        if not encodings:
            return jsonify({"status": "no_face", "message": "Could not encode face"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    face_enc  = encodings[0]
    distances = face_recognition.face_distance(enc, face_enc)
    best_idx  = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    if best_dist >= TOLERANCE:
        return jsonify({"status": "unknown",
                        "message": f"Face not recognized (dist={best_dist:.2f})",
                        "confidence": 0})

    roll       = names[best_idx]
    confidence = round((1 - best_dist / TOLERANCE) * 100, 1)

    if confidence < MIN_CONF:
        return jsonify({
            "status"    : "low_confidence",
            "message"   : f"Low confidence {confidence}% — move closer",
            "confidence": confidence,
        })

    # Mark attendance
    try:
        from models   import Student, Attendance
        from database import db

        today   = date.today()
        student = Student.query.filter_by(roll_number=roll, is_active=True).first()
        if not student:
            return jsonify({"status": "unknown", "message": "Student not in DB"})

        existing = Attendance.query.filter_by(
            student_id=student.id, date=today).first()
        if existing:
            return jsonify({
                "status"     : "already_marked",
                "name"       : student.name,
                "roll_number": roll,
                "confidence" : confidence,
                "message"    : f"{student.name} already marked today",
                "department" : student.department,
            })

        record = Attendance(
            student_id = student.id,
            date       = today,
            time_in    = datetime.now().time(),
            status     = "Present",
            marked_by  = "WebRecognition",
        )
        db.session.add(record)
        db.session.commit()

        return jsonify({
            "status"     : "marked",
            "name"       : student.name,
            "roll_number": roll,
            "confidence" : confidence,
            "message"    : f"✓ {student.name} marked present!",
            "time"       : datetime.now().strftime("%I:%M %p"),
            "department" : student.department,
        })

    except Exception as e:
        try:
            from database import db
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"status": "error", "message": str(e)})


# ── API: Reload encodings ─────────────────────────────────────
@recognition_bp.route("/api/reload", methods=["POST"])
@login_required
def api_reload():
    enc, names = load_encodings(force=True)
    from collections import Counter
    count = len(Counter(names)) if names else 0
    return jsonify({"success": enc is not None,
                    "students": count,
                    "encodings": len(enc) if enc else 0})


# ── Manual Attendance ─────────────────────────────────────────
@recognition_bp.route("/manual")
@login_required
def manual():
    from models import Student
    students = Student.query.filter_by(is_active=True).order_by(Student.name).all()
    return render_template("recognition/manual.html",
                           students=students, active_page="recognition")


@recognition_bp.route("/api/manual_mark", methods=["POST"])
@login_required
def api_manual_mark():
    from models import Student, Attendance
    from database import db
    data = request.get_json()
    student_id = data.get("student_id") if data else None
    if not student_id:
        return jsonify({"success": False, "error": "student_id required"}), 400
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404
    today    = date.today()
    existing = Attendance.query.filter_by(
        student_id=student_id, date=today).first()
    if existing:
        return jsonify({"success": False, "status": "already_marked",
                        "message": f"{student.name} already marked today"})
    try:
        record = Attendance(
            student_id=student_id,
            date=today,
            time_in=datetime.now().time(),
            status="Present",
            marked_by="Manual",
        )
        db.session.add(record)
        db.session.commit()
        return jsonify({"success": True,
                        "message": f"✓ {student.name} marked present",
                        "time": datetime.now().strftime("%I:%M %p")})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
