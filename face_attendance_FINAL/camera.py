"""
camera.py — Live Face Recognition + Attendance Marking
========================================================
Day 7 Update: Integrated attendance_manager.py
  - Recognized face -> mark attendance in MySQL
  - Shows "Attendance Marked" or "Already Marked Today"
  - Notification bar on screen
  - No duplicate entries

CONTROLS:
  Q / ESC  -> Quit
  S        -> Save screenshot
  P        -> Pause / Resume
"""

import cv2
import pickle
import os
import sys
import time
import numpy as np
from datetime import datetime
from collections import defaultdict

# CONFIG
ENCODINGS_FILE      = "encodings.pickle"
TOLERANCE           = 0.50
SCALE_FACTOR        = 0.5
PROCESS_EVERY_N     = 2
DISPLAY_WIDTH       = 1280
DISPLAY_HEIGHT      = 720
CAMERA_INDEX        = 0
SCREENSHOTS_FOLDER  = "screenshots"
RECOGNITION_COOLDOWN = 5   # seconds between re-checking same person

# Colors BGR
COLOR_KNOWN    = (50, 220, 100)
COLOR_UNKNOWN  = (50, 100, 255)
COLOR_BOX_BG   = (15, 20, 35)
COLOR_WHITE    = (240, 240, 240)
COLOR_MUTED    = (120, 140, 160)
COLOR_ACCENT   = (255, 148, 82)
COLOR_OVERLAY  = (8, 12, 20)
COLOR_SUCCESS  = (50, 220, 100)
COLOR_WARNING  = (50, 180, 255)
COLOR_ERROR    = (50, 80, 220)


def check_imports():
    try:
        import face_recognition
        return face_recognition
    except ImportError:
        print("\nface_recognition not installed!")
        print("Run: pip install cmake dlib face-recognition")
        sys.exit(1)


def load_attendance_manager():
    try:
        from attendance_manager import mark_attendance, STATUS_MARKED, STATUS_ALREADY_DONE
        return mark_attendance, STATUS_MARKED, STATUS_ALREADY_DONE
    except Exception as e:
        print(f"\n  WARNING: Attendance manager failed: {e}")
        print("  Recognition works but attendance won't be saved.")
        return None, None, None


def load_encodings():
    if not os.path.exists(ENCODINGS_FILE):
        print(f"\nERROR: '{ENCODINGS_FILE}' not found!")
        print("Run: python encode_faces.py  first")
        sys.exit(1)
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    from collections import Counter
    counts = Counter(data["names"])
    print(f"  Loaded {len(data['encodings'])} encodings for {len(counts)} student(s)")
    for name, count in sorted(counts.items()):
        print(f"    -> {name}: {count} photos")
    return data["encodings"], data["names"]


def recognize_faces(frame, known_encodings, known_names, face_recognition):
    results = []
    small   = cv2.resize(frame, (0, 0), fx=SCALE_FACTOR, fy=SCALE_FACTOR)
    rgb     = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    locations = face_recognition.face_locations(rgb, model="hog")
    if not locations:
        return results
    encodings = face_recognition.face_encodings(rgb, locations)
    scale = 1 / SCALE_FACTOR
    for (top, right, bottom, left), enc in zip(locations, encodings):
        top    = int(top * scale)
        right  = int(right * scale)
        bottom = int(bottom * scale)
        left   = int(left * scale)
        name = "Unknown"
        confidence = 0.0
        color = COLOR_UNKNOWN
        if known_encodings:
            distances = face_recognition.face_distance(known_encodings, enc)
            best_idx  = int(np.argmin(distances))
            best_dist = distances[best_idx]
            if best_dist < TOLERANCE:
                name       = known_names[best_idx]
                confidence = max(0, round((1 - best_dist / TOLERANCE) * 100, 1))
                color      = COLOR_KNOWN
        results.append((top, right, bottom, left, name, confidence, color))
    return results


def draw_face(frame, top, right, bottom, left, name, confidence, color, att_status=""):
    corner_len = min(28, (bottom - top) // 4)
    th = 2
    # Corner brackets
    cv2.line(frame, (left,  top),    (left + corner_len, top),    color, th)
    cv2.line(frame, (left,  top),    (left,  top + corner_len),   color, th)
    cv2.line(frame, (right, top),    (right - corner_len, top),   color, th)
    cv2.line(frame, (right, top),    (right, top + corner_len),   color, th)
    cv2.line(frame, (left,  bottom), (left + corner_len, bottom), color, th)
    cv2.line(frame, (left,  bottom), (left,  bottom - corner_len),color, th)
    cv2.line(frame, (right, bottom), (right - corner_len, bottom),color, th)
    cv2.line(frame, (right, bottom), (right, bottom - corner_len),color, th)
    for pt in [(left,top),(right,top),(left,bottom),(right,bottom)]:
        cv2.circle(frame, pt, 3, color, -1)

    font = cv2.FONT_HERSHEY_DUPLEX
    if name != "Unknown":
        l1 = name
        l2 = f"{confidence:.0f}% match"
        if att_status == "marked":
            l3 = "Attendance Marked"
            l3_color = COLOR_SUCCESS
        elif att_status == "already_marked":
            l3 = "Already Marked Today"
            l3_color = COLOR_WARNING
        else:
            l3 = ""
            l3_color = COLOR_MUTED
    else:
        l1, l2, l3, l3_color = "Unknown", "Not in database", "", COLOR_MUTED

    (w1, h1), _ = cv2.getTextSize(l1, font, 0.6,  1)
    (w2, h2), _ = cv2.getTextSize(l2, font, 0.45, 1)
    (w3, h3), _ = cv2.getTextSize(l3, font, 0.42, 1) if l3 else ((0, 0), None)
    box_w = max(w1, w2, w3) + 20
    box_h = h1 + h2 + (h3 + 6 if l3 else 0) + 20
    hf, wf = frame.shape[:2]

    lx1 = left;  ly1 = bottom + 6
    lx2 = left + box_w; ly2 = ly1 + box_h
    if ly2 > hf:
        ly1 = top - box_h - 6; ly2 = top - 6

    overlay = frame.copy()
    cv2.rectangle(overlay, (lx1, ly1), (lx2, ly2), COLOR_BOX_BG, -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.rectangle(frame, (lx1, ly1), (lx1 + 3, ly2), color, -1)
    cv2.rectangle(frame, (lx1, ly1), (lx2, ly2), color, 1)

    y = ly1 + h1 + 6
    cv2.putText(frame, l1, (lx1 + 12, y), font, 0.6,  COLOR_WHITE, 1, cv2.LINE_AA)
    y += h2 + 5
    cv2.putText(frame, l2, (lx1 + 12, y), font, 0.45, COLOR_MUTED, 1, cv2.LINE_AA)
    if l3:
        y += h3 + 5
        cv2.putText(frame, l3, (lx1 + 12, y), font, 0.42, l3_color, 1, cv2.LINE_AA)
    return frame


class NotificationManager:
    DISPLAY_SECONDS = 4
    MAX_VISIBLE     = 4
    def __init__(self):
        self.notifications = []
    def add(self, text, color):
        self.notifications.append({
            "text": text, "color": color, "created_at": time.time()
        })
        self.notifications = self.notifications[-self.MAX_VISIBLE:]
    def draw(self, frame):
        now = time.time()
        self.notifications = [
            n for n in self.notifications
            if now - n["created_at"] < self.DISPLAY_SECONDS
        ]
        h, w = frame.shape[:2]
        y_start = h - 90
        font = cv2.FONT_HERSHEY_DUPLEX
        for i, notif in enumerate(reversed(self.notifications)):
            text  = notif["text"]
            color = notif["color"]
            (tw, th), _ = cv2.getTextSize(text, font, 0.55, 1)
            nx1 = 14;  ny1 = y_start - i * (th + 22) - th - 8
            nx2 = nx1 + tw + 28; ny2 = ny1 + th + 12
            if ny1 < 60:
                break
            overlay = frame.copy()
            cv2.rectangle(overlay, (nx1, ny1), (nx2, ny2), COLOR_BOX_BG, -1)
            cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
            cv2.rectangle(frame, (nx1, ny1), (nx1+3, ny2), color, -1)
            cv2.rectangle(frame, (nx1, ny1), (nx2,  ny2),  color, 1)
            cv2.putText(frame, text, (nx1+14, ny1+th+3), font, 0.55, COLOR_WHITE, 1, cv2.LINE_AA)
        return frame


def draw_hud(frame, fps, face_count, known_count, marked_today, paused):
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_DUPLEX
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), COLOR_OVERLAY, -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    cv2.putText(frame, "FaceAttend",               (14,  34), font, 0.75, COLOR_ACCENT,  1, cv2.LINE_AA)
    cv2.line(frame, (132,10),(132,42),(40,50,70),1)
    fps_col = COLOR_SUCCESS if fps >= 20 else COLOR_ERROR
    cv2.putText(frame, f"FPS: {fps:.0f}",           (148, 34), font, 0.52, fps_col,      1, cv2.LINE_AA)
    cv2.putText(frame, f"Faces: {face_count}",      (240, 34), font, 0.52, COLOR_WHITE,  1, cv2.LINE_AA)
    cv2.putText(frame, f"Known: {known_count}",     (345, 34), font, 0.52, COLOR_SUCCESS,1, cv2.LINE_AA)
    cv2.putText(frame, f"Marked Today: {marked_today}", (460, 34), font, 0.52, COLOR_WARNING, 1, cv2.LINE_AA)
    ts = datetime.now().strftime("%d %b  %I:%M:%S %p")
    (tw, _),_ = cv2.getTextSize(ts, font, 0.5, 1)
    cv2.putText(frame, ts, (w - tw - 14, 34), font, 0.5, COLOR_MUTED, 1, cv2.LINE_AA)

    if paused:
        cv2.putText(frame, "PAUSED", (w//2 - 55, h//2), font, 1.4, COLOR_ACCENT, 2, cv2.LINE_AA)

    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h-36), (w, h), COLOR_OVERLAY, -1)
    cv2.addWeighted(overlay2, 0.78, frame, 0.22, 0, frame)
    cv2.putText(frame, "  Q: Quit    S: Screenshot    P: Pause",
                (10, h-10), font, 0.42, COLOR_MUTED, 1, cv2.LINE_AA)
    cv2.putText(frame, "Day 8: Reports & Analytics coming next",
                (w-370, h-10), font, 0.38, (60,80,100), 1, cv2.LINE_AA)
    return frame


def run(known_encodings, known_names, face_recognition,
        mark_attendance_fn, STATUS_MARKED, STATUS_ALREADY_DONE):

    print(f"\n  Opening camera {CAMERA_INDEX}...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"  ERROR: Could not open camera {CAMERA_INDEX}")
        print("  Try CAMERA_INDEX = 1 in camera.py")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  DISPLAY_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DISPLAY_HEIGHT)
    print("  Camera opened successfully")
    print("  Attendance marking: ACTIVE" if mark_attendance_fn else
          "  WARNING: Attendance marking DISABLED")
    print("  Q=quit  S=screenshot  P=pause\n")

    cv2.namedWindow("FaceAttend - Day 7", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("FaceAttend - Day 7", DISPLAY_WIDTH, DISPLAY_HEIGHT)

    notifications = NotificationManager()
    os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

    fps_counter  = 0
    fps_start    = time.time()
    fps          = 0.0
    frame_count  = 0
    face_results = []
    paused       = False
    student_cache = {}
    last_tried    = defaultdict(float)
    marked_today  = 0
    marked_set    = set()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)

            if frame_count % PROCESS_EVERY_N == 0:
                face_results = recognize_faces(
                    frame, known_encodings, known_names, face_recognition
                )

                if mark_attendance_fn:
                    now_t = time.time()
                    for (_, _, _, _, name, conf, _) in face_results:
                        if name == "Unknown" or conf < 60:
                            continue
                        if now_t - last_tried[name] < RECOGNITION_COOLDOWN:
                            continue
                        last_tried[name] = now_t

                        result = mark_attendance_fn(name)
                        status = result["status"]
                        student_cache[name] = {"att_status": status, "result": result}

                        if status == STATUS_MARKED:
                            sname = result["student"]["name"] if result["student"] else name
                            t = result["time"] or ""
                            notifications.add(f"Marked: {sname}  |  {name}  |  {t}", COLOR_SUCCESS)
                            if name not in marked_set:
                                marked_set.add(name)
                                marked_today += 1
                            print(f"  MARKED: {sname} ({name}) at {t}")
                        elif status == STATUS_ALREADY_DONE:
                            sname = result["student"]["name"] if result["student"] else name
                            notifications.add(f"Already marked: {sname}", COLOR_WARNING)
                        elif status == "error":
                            notifications.add(f"DB Error: {result['message'][:40]}", COLOR_ERROR)

            frame_count += 1

        known_this = 0
        for (top, right, bottom, left, name, conf, color) in face_results:
            cache = student_cache.get(name, {})
            att_st = cache.get("att_status", "")
            frame = draw_face(frame, top, right, bottom, left, name, conf, color, att_st)
            if name != "Unknown":
                known_this += 1

        fps_counter += 1
        elapsed = time.time() - fps_start
        if elapsed >= 0.5:
            fps = fps_counter / elapsed
            fps_counter = 0
            fps_start = time.time()

        frame = draw_hud(frame, fps, len(face_results), known_this, marked_today, paused)
        frame = notifications.draw(frame)
        cv2.imshow("FaceAttend - Day 7", frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break
        elif key in (ord('s'), ord('S')):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(SCREENSHOTS_FOLDER, f"screenshot_{ts}.jpg")
            cv2.imwrite(path, frame)
            print(f"  Screenshot saved: {path}")
        elif key in (ord('p'), ord('P')):
            paused = not paused
            print(f"  {'PAUSED' if paused else 'RESUMED'}")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n  Session ended. Marked {marked_today} student(s) this session.")


if __name__ == "__main__":
    print("\n" + "="*56)
    print("  FaceAttend - Live Recognition + Attendance (Day 7)")
    print("="*56)

    face_recognition = check_imports()
    print("  Libraries loaded")

    mark_fn, S_MARKED, S_ALREADY = load_attendance_manager()

    print(f"\n  Loading encodings...")
    known_encodings, known_names = load_encodings()

    run(known_encodings, known_names, face_recognition,
        mark_fn, S_MARKED, S_ALREADY)
