"""
routes/capture.py — Dataset Capture + Smart Incremental Encoding
=================================================================
SMART ENCODE:
  - Sirf NAYE student ko encode karo (seconds mein!)
  - Baaki students ka data already pickle mein hai — chhedo mat
  - Agar reset karo toh sirf us student ka data hatao
  - encode_faces.py ki ab KABHI zaroorat nahi!
"""

import os, base64, uuid, pickle, threading
from flask import Blueprint, render_template, request, jsonify, current_app
from routes.auth import login_required
from database import db
from models import Student
from config import Config

capture_bp = Blueprint("capture", __name__, url_prefix="/capture")

ENC_FILE = os.path.join(os.path.dirname(Config.DATASET_FOLDER), "encodings.pickle")


# ── Pickle helpers ────────────────────────────────────────────
def _load_pickle():
    """Load existing encodings. Returns (encodings_list, names_list)."""
    if not os.path.exists(ENC_FILE):
        return [], []
    try:
        with open(ENC_FILE, "rb") as f:
            data = pickle.load(f)
        return list(data["encodings"]), list(data["names"])
    except Exception:
        return [], []


def _save_pickle(encodings, names):
    """Save encodings to pickle."""
    with open(ENC_FILE, "wb") as f:
        pickle.dump({"encodings": encodings, "names": names}, f)


def _remove_student_from_pickle(roll_number):
    """Remove one student's encodings from pickle (for reset/delete)."""
    encs, names = _load_pickle()
    if not names:
        return 0
    # Keep everyone except this roll
    pairs   = [(e, n) for e, n in zip(encs, names) if n != roll_number]
    removed = len(encs) - len(pairs)
    if pairs:
        new_encs, new_names = zip(*pairs)
        _save_pickle(list(new_encs), list(new_names))
    else:
        # No one left
        if os.path.exists(ENC_FILE):
            os.remove(ENC_FILE)
    print(f"  ✓ Removed {removed} encodings for {roll_number}")
    return removed


# ── SMART INCREMENTAL ENCODE ──────────────────────────────────
def encode_one_student(roll_number):
    """
    Sirf EK student ko encode karo aur existing pickle mein ADD karo.
    Baaki sab students ko chhodo — unhe dobara encode karne ki zaroorat nahi!

    Steps:
      1. Existing pickle load karo
      2. Is student ke purane encodings hata do (agar tha)
      3. Is student ke naye photos encode karo
      4. Back mein add karke save karo
    """
    try:
        import face_recognition
        import cv2
        import numpy as np

        dataset_dir   = Config.DATASET_FOLDER
        student_folder = os.path.join(dataset_dir, roll_number)
        supported_ext  = {".jpg", ".jpeg", ".png", ".webp"}

        if not os.path.exists(student_folder):
            print(f"  ✗ Folder not found: {student_folder}")
            return False

        # Step 1: Load existing pickle
        all_encs, all_names = _load_pickle()
        print(f"  → Existing pickle: {len(all_encs)} encodings total")

        # Step 2: Remove old encodings of THIS student only
        before = len(all_encs)
        pairs  = [(e, n) for e, n in zip(all_encs, all_names) if n != roll_number]
        if pairs:
            all_encs, all_names = map(list, zip(*pairs))
        else:
            all_encs, all_names = [], []
        removed = before - len(all_encs)
        if removed:
            print(f"  → Removed {removed} old encodings for {roll_number}")

        # Step 3: Encode only THIS student's photos
        imgs = [
            os.path.join(student_folder, f)
            for f in os.listdir(student_folder)
            if os.path.splitext(f)[1].lower() in supported_ext
        ]

        if not imgs:
            print(f"  ✗ No photos in {student_folder}")
            return False

        new_encs  = 0
        for img_path in imgs:
            try:
                bgr = cv2.imread(img_path)
                if bgr is None:
                    continue

                # Same CLAHE preprocessing as recognition
                lab   = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l     = clahe.apply(l)
                bgr   = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
                rgb   = np.ascontiguousarray(
                    cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8
                )

                locs = face_recognition.face_locations(rgb, model="hog")
                if not locs:
                    # Try upsample
                    locs = face_recognition.face_locations(
                        rgb, number_of_times_to_upsample=2, model="hog"
                    )
                if not locs:
                    continue

                encs = face_recognition.face_encodings(rgb, locs, num_jitters=3)
                if encs:
                    all_encs.append(encs[0])
                    all_names.append(roll_number)
                    new_encs += 1

            except Exception as e:
                print(f"  ✗ Error on {img_path}: {e}")
                continue

        if new_encs == 0:
            print(f"  ✗ No faces found in photos for {roll_number}")
            return False

        # Step 4: Save back — EVERYONE's data intact + new student added
        _save_pickle(all_encs, all_names)
        total_students = len(set(all_names))
        print(f"  ✓ {roll_number}: {new_encs} new encodings added")
        print(f"  ✓ Pickle now has {len(all_encs)} encodings from {total_students} students")
        return True

    except Exception as e:
        print(f"  ✗ Encode failed for {roll_number}: {e}")
        return False


def trigger_encode(roll_number):
    """Sirf ek student ko background mein encode karo."""
    t = threading.Thread(
        target=encode_one_student,
        args=(roll_number,),
        daemon=True
    )
    t.start()


# ── Routes ────────────────────────────────────────────────────
@capture_bp.route("/<int:student_id>")
@login_required
def capture_page(student_id):
    student = Student.query.get_or_404(student_id)
    dataset_folder = os.path.join(Config.DATASET_FOLDER, student.roll_number)
    existing_count = 0
    if os.path.exists(dataset_folder):
        existing_count = len([
            f for f in os.listdir(dataset_folder)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ])
    return render_template("students/capture.html",
                           student=student,
                           existing_count=existing_count,
                           active_page="students")


@capture_bp.route("/save", methods=["POST"])
@login_required
def save_photo():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data"}), 400

    student_id   = data.get("student_id")
    image_base64 = data.get("image")
    if not student_id or not image_base64:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    student = Student.query.get(student_id)
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404

    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        img_bytes   = base64.b64decode(image_base64)
        save_folder = os.path.join(Config.DATASET_FOLDER, student.roll_number)
        os.makedirs(save_folder, exist_ok=True)

        filename  = f"{uuid.uuid4().hex}.jpg"
        save_path = os.path.join(save_folder, filename)
        with open(save_path, "wb") as f:
            f.write(img_bytes)

        total = len([x for x in os.listdir(save_folder)
                     if x.lower().endswith((".jpg", ".jpeg", ".png"))])
        return jsonify({"success": True, "total": total, "filename": filename})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@capture_bp.route("/<int:student_id>/done", methods=["POST"])
@login_required
def mark_done(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        student.dataset_ready = True
        db.session.commit()

        # ✅ SIRF IS STUDENT KO ENCODE KARO — baaki sab safe hain!
        trigger_encode(student.roll_number)

        return jsonify({
            "success": True,
            "message": (
                f"Photos saved for {student.name}! "
                f"Encoding sirf inhi ke liye ho raha hai — "
                f"20-30 seconds mein recognition ready!"
            )
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@capture_bp.route("/<int:student_id>/reset", methods=["POST"])
@login_required
def reset_dataset(student_id):
    import shutil
    student = Student.query.get_or_404(student_id)
    dataset_folder = os.path.join(Config.DATASET_FOLDER, student.roll_number)
    try:
        # Delete photos
        if os.path.exists(dataset_folder):
            shutil.rmtree(dataset_folder)
        os.makedirs(dataset_folder, exist_ok=True)
        student.dataset_ready = False
        db.session.commit()

        # ✅ Sirf is student ki encodings hatao pickle se
        _remove_student_from_pickle(student.roll_number)

        return jsonify({
            "success": True,
            "message": f"{student.name} ka data reset ho gaya. Baaki students safe hain."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@capture_bp.route("/api/encode_status")
@login_required
def encode_status():
    """Check encoding status — kitne students encoded hain."""
    if not os.path.exists(ENC_FILE):
        return jsonify({"ready": False, "students": 0, "encodings": 0})
    try:
        encs, names = _load_pickle()
        from collections import Counter
        return jsonify({
            "ready"    : len(encs) > 0,
            "students" : len(Counter(names)),
            "encodings": len(encs),
        })
    except Exception:
        return jsonify({"ready": False, "students": 0, "encodings": 0})
