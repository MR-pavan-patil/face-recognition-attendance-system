"""
test_face.py — Quick face detection test
Run: python test_face.py
"""

import os
import face_recognition
from PIL import Image

DATASET_DIR = "dataset"

print("\n" + "="*50)
print("  Face Detection Test")
print("="*50)

# Find all student folders
folders = [
    d for d in os.listdir(DATASET_DIR)
    if os.path.isdir(os.path.join(DATASET_DIR, d))
    and not d.startswith(".")
]

if not folders:
    print("\n✗ No folders found in dataset/")
    print("  Expected: dataset/<roll_number>/photo.jpg")
    exit()

print(f"\n  Found folders: {folders}")

for folder in folders[:2]:  # test first 2 students
    folder_path = os.path.join(DATASET_DIR, folder)
    images = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    print(f"\n  Student: {folder}")
    print(f"  Photos found: {len(images)}")

    if not images:
        print("  ✗ No images found in this folder!")
        continue

    # Test first 3 images
    for img_name in images[:3]:
        img_path = os.path.join(folder_path, img_name)
        
        try:
            # Check image opens
            pil_img = Image.open(img_path)
            print(f"\n  Testing: {img_name}")
            print(f"  Size: {pil_img.size} | Mode: {pil_img.mode}")

            # Try face detection
            image = face_recognition.load_image_file(img_path)
            locations = face_recognition.face_locations(image, model="hog")

            if locations:
                print(f"  ✓ FACE DETECTED! Location: {locations[0]}")
            else:
                print(f"  ✗ No face detected")
                print(f"  Tip: Face must be clearly visible, well-lit, front-facing")

        except Exception as e:
            print(f"  ✗ Error: {e}")

print("\n" + "="*50)
print("  If all show 'No face detected':")
print("  1. Photos may be too dark or blurry")
print("  2. Face may be too small in frame")
print("  3. Try capturing new photos in good light")
print("="*50 + "\n")
