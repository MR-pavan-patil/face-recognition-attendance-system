"""
encode_faces.py — Face Encoding Generator (Final)
===================================================
Improvements:
- Multiple encodings per image (num_jitters=3) — more accurate
- Image preprocessing (contrast enhance)
- Progress display
- Works automatically via capture.py (no need to run manually)
"""

import os, pickle, cv2, numpy as np
from pathlib import Path
from config import Config

def encode_all():
    try:
        import face_recognition
    except ImportError:
        print("ERROR: pip install face-recognition")
        return

    dataset_dir   = Config.DATASET_FOLDER
    enc_file      = os.path.join(os.path.dirname(dataset_dir), "encodings.pickle")
    supported_ext = {".jpg", ".jpeg", ".png", ".webp"}

    if not os.path.exists(dataset_dir):
        print(f"Dataset folder not found: {dataset_dir}")
        return

    folders = [d for d in Path(dataset_dir).iterdir()
               if d.is_dir() and not d.name.startswith(".")]

    if not folders:
        print("No student folders found in dataset/")
        return

    known_encodings = []
    known_names     = []
    total_imgs      = 0
    failed          = 0

    print(f"\nEncoding {len(folders)} students...\n")

    for folder in sorted(folders):
        roll = folder.name
        imgs = [f for f in folder.iterdir()
                if f.suffix.lower() in supported_ext]

        student_encs = 0
        for img_path in imgs:
            try:
                bgr = cv2.imread(str(img_path))
                if bgr is None:
                    continue

                # Enhance contrast (same as recognition)
                lab   = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                l     = clahe.apply(l)
                bgr   = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
                rgb   = np.ascontiguousarray(
                            cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)

                locs = face_recognition.face_locations(rgb, model="hog")
                if not locs:
                    failed += 1
                    continue

                # num_jitters=3 — more accurate encoding
                encs = face_recognition.face_encodings(rgb, locs, num_jitters=3)
                if encs:
                    known_encodings.append(encs[0])
                    known_names.append(roll)
                    student_encs += 1
                    total_imgs   += 1

            except Exception as e:
                failed += 1
                continue

        status = "✓" if student_encs > 0 else "✗"
        print(f"  {status} {roll:<20} {student_encs} encodings")

    print(f"\nTotal: {total_imgs} encodings from {len(folders)} students")
    if failed:
        print(f"Skipped: {failed} images (no face detected)")

    if known_encodings:
        with open(enc_file, "wb") as f:
            pickle.dump({"encodings": known_encodings, "names": known_names}, f)
        print(f"\n✓ Saved: {enc_file}")
        print("Recognition is ready!\n")
    else:
        print("\n✗ No encodings created. Check dataset photos.\n")


if __name__ == "__main__":
    encode_all()
