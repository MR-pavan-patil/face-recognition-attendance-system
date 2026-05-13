# FaceAttend — Complete Project Guide
## BCA Final Year Project | Face Recognition Attendance System
### Day 1 to Day 7 — Full Documentation

---

## 📁 COMPLETE PROJECT STRUCTURE

```
face_attendance/
│
├── ─── PYTHON FILES (Root) ───────────────────────────────────
│
├── app.py                    ← Main Flask server (run this!)
├── config.py                 ← MySQL password & settings
├── database.py               ← SQLAlchemy setup
├── models.py                 ← DB tables: Student, Attendance
├── utils.py                  ← Helper functions
├── init_db.py                ← Run ONCE to create database
├── requirements.txt          ← All Python packages
│
├── encode_faces.py           ← Day 5: Generate face encodings
├── camera.py                 ← Day 6+7: Live recognition + attendance
├── attendance_manager.py     ← Day 7: Attendance DB logic
│
├── ─── ROUTES (Web Endpoints) ───────────────────────────────
│
├── routes/
│   ├── __init__.py
│   ├── students.py           ← Register, list, delete students
│   ├── capture.py            ← Webcam dataset capture
│   └── attendance.py         ← Today's attendance, history
│
├── ─── WEB PAGES (HTML Templates) ──────────────────────────
│
├── templates/
│   ├── base.html             ← Master layout (navbar + sidebar)
│   ├── dashboard.html        ← Home dashboard with stats
│   ├── coming_soon.html      ← Placeholder for future pages
│   ├── errors/
│   │   ├── 404.html
│   │   └── 500.html
│   ├── students/
│   │   ├── register.html     ← Student registration form
│   │   ├── list.html         ← Students table with search
│   │   ├── detail.html       ← Single student profile
│   │   └── capture.html      ← Webcam capture page
│   └── attendance/
│       ├── today.html        ← Today's attendance list
│       └── history.html      ← Past date records
│
├── ─── STATIC FILES (CSS/JS) ────────────────────────────────
│
├── static/
│   ├── css/
│   │   └── style.css         ← Complete dark premium theme
│   └── js/
│       ├── main.js           ← Clock, sidebar, toast messages
│       ├── dashboard.js      ← Counter animations
│       ├── register.js       ← Drag and drop photo upload
│       └── capture.js        ← Webcam capture logic
│
├── ─── DATA FOLDERS ─────────────────────────────────────────
│
├── uploads/students/         ← Registration photos
│   └── <ROLL_NUMBER>/
│       └── photo_uuid.jpg
│
├── dataset/                  ← Webcam captured face photos
│   └── <ROLL_NUMBER>/
│       └── uuid.jpg
│
├── screenshots/              ← Auto-created when you press S in camera
│
└── encodings.pickle          ← Auto-created by encode_faces.py
```

---

## ⚙️ ONE-TIME SETUP (Do this only once on a new machine)

### Step 1 — Install Python 3.11
Download from: https://python.org/downloads/
During install: CHECK "Add Python to PATH" ✅

Verify:
```cmd
python --version
```
Should show: Python 3.11.x

---

### Step 2 — Install MySQL
Download MySQL Installer from: https://dev.mysql.com/downloads/installer/
- Choose "Developer Default" (~400 MB)
- Set root password — write it down!
- Example: Admin@1234

Verify MySQL is working:
```cmd
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
```
Type your password. You should see: mysql>
Type `exit` to leave.

If you get "'mysql' is not recognized" error:
→ Search "Environment Variables" in Windows
→ System Variables → Path → Edit → New
→ Add: C:\Program Files\MySQL\MySQL Server 8.0\bin
→ Click OK and restart CMD

---

### Step 3 — Set Your Password in config.py

Open config.py and change this line:
```python
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "your_password_here")
```
To your actual MySQL password:
```python
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "Admin@1234")
```
The code handles special characters like @ # % automatically.

---

### Step 4 — Install Python Packages (Day 1-4 web app)

Open CMD inside your project folder:
```cmd
pip install flask flask-sqlalchemy pymysql cryptography
```

---

### Step 5 — Install Face Recognition Packages (Day 5-7)

Install IN THIS EXACT ORDER:
```cmd
pip install cmake
pip install dlib
pip install face-recognition
pip install opencv-python numpy Pillow
```

If dlib fails on Windows:
1. Go to: https://github.com/z-mahmud22/Dlib_Windows_Python3.x
2. Download the .whl file for your Python version
   Example for Python 3.11: dlib-19.24.2-cp311-cp311-win_amd64.whl
3. Run: pip install dlib-19.24.2-cp311-cp311-win_amd64.whl
4. Then: pip install face-recognition

Verify everything:
```cmd
python -c "import flask; print('Flask OK')"
python -c "import face_recognition; print('face_recognition OK')"
python -c "import cv2; print('OpenCV OK')"
```

---

### Step 6 — Create the Database (Run ONCE only!)

```cmd
python init_db.py
```

Expected output:
```
✓ Database 'face_attendance_db' created
✓ Tables created: students, student_images, attendance
✓ Done! Now run: python app.py
```

---

## ▶️ HOW TO RUN EVERY DAY

### Start the Web App:
```cmd
python app.py
```
Then open browser: http://127.0.0.1:5000

### Start Face Recognition (after encoding):
```cmd
python camera.py
```

To stop either: Press Ctrl + C in CMD

---

## 🗓️ DAY-BY-DAY COMPLETE GUIDE

---

### ✅ DAY 1 — Flask Setup + Dashboard

**What was built:**
- Flask project structure
- Dark professional dashboard with sidebar navigation
- 4 stat cards: Total Students, Present Today, Absent, Dataset Ready
- Live clock in top navbar
- Quick actions panel
- Responsive layout (works on mobile)

**Files created:**
app.py, config.py, database.py, models.py,
templates/base.html, templates/dashboard.html,
static/css/style.css, static/js/main.js, static/js/dashboard.js

---

### ✅ DAY 2 — MySQL Database + Student Registration

**What was built:**
- MySQL database connection with SQLAlchemy
- 3 database tables: students, student_images, attendance
- Student registration form with validation
- Multi-photo upload (drag & drop, up to 10 photos)
- Students list with search and pagination
- Delete student with confirmation

**Database tables:**
```
students        → id, name, roll_number, email, phone, department, year, section,
                  is_active, dataset_ready, registered_at
student_images  → id, student_id, filename, filepath, uploaded_at
attendance      → id, student_id, date, time_in, status, marked_by
```

**Files created:**
routes/students.py, templates/students/register.html,
templates/students/list.html, templates/students/detail.html,
static/js/register.js

---

### ✅ DAY 3 — Premium UI Polish

**What was improved:**
- Fonts: Poppins (headings) + Inter (body text)
- Card shadows and depth
- Table row hover effects with blue left border
- Badge improvements (Ready/Pending/Year badges)
- Button hover lift + glow animations
- Better search bar with focus glow
- Increased spacing for readability
- Fully responsive on all screen sizes

**Files updated:** static/css/style.css, templates/base.html

---

### ✅ DAY 4 — Webcam Dataset Capture

**What was built:**
- Camera access via browser getUserMedia API
- Live video feed with face position guide oval
- Manual capture button (or press Spacebar)
- Auto-capture mode (captures every 1.2 seconds)
- Photos saved to dataset/<roll_number>/ folder
- Progress counter: 0 to 30 photos
- "Mark Dataset Ready" → updates database
- Reset & Recapture option
- Green camera button in students list

**How to use:**
1. python app.py
2. Open http://127.0.0.1:5000/students/
3. Click green camera button for any student
4. Allow camera → click Auto toggle → wait for 30 photos
5. Click "Mark Dataset Ready"

**Files created:**
routes/capture.py, templates/students/capture.html, static/js/capture.js

---

### ✅ DAY 5 — Face Encoding Generator

**What was built:**
- Reads all photos from dataset/<roll_number>/ folders
- Detects faces using dlib (HOG model)
- Generates 128-dimensional face encodings
- Saves all encodings to encodings.pickle

**How encodings work (simple explanation):**
The face_recognition library measures 128 specific points on every face
(eye distance, nose width, jawline shape, etc.) and converts them into
a list of 128 numbers. Two photos of the same person produce similar
numbers. Two different people produce different numbers.
When recognizing someone: compare their live 128 numbers against stored
encodings. Closest match = recognized person.

**How to run:**
```cmd
python encode_faces.py
```
Re-run whenever you add new student photos!

**Files created:** encode_faces.py

---

### ✅ DAY 6 — Live Face Recognition

**What was built:**
- Opens webcam using OpenCV
- Detects faces in real-time (every 2nd frame for speed)
- Matches detected faces against encodings.pickle
- Shows student name + confidence percentage
- Green corner brackets = known person
- Red corner brackets = unknown person
- FPS counter, live clock in HUD
- Press S to save screenshot
- Press P to pause/resume
- Press Q to quit

**Performance tuning (in camera.py):**
```python
SCALE_FACTOR    = 0.5   # reduce to 0.25 if slow
PROCESS_EVERY_N = 2     # increase to 4 if slow
TOLERANCE       = 0.50  # lower = stricter matching
```

**How to run:**
```cmd
python camera.py
```

**Files updated:** camera.py

---

### ✅ DAY 7 — Attendance Marking Logic (TODAY)

**What was built:**

attendance_manager.py:
- Connects directly to MySQL (no Flask context needed)
- Fetches student by roll_number
- Checks if already marked today (per student per day)
- Inserts new attendance record if not marked
- Returns status: marked / already_marked / unknown / error

camera.py (updated):
- After recognizing face with confidence >= 60%
- Waits 5-second cooldown before re-checking same person
- Calls mark_attendance(roll_number)
- Shows notification on screen:
  - Green: "Marked: [Name] | [Roll] | [Time]"
  - Orange: "Already marked today"
  - Red: DB error message
- "Marked Today: X" counter in HUD

routes/attendance.py (new web page):
- /attendance/ — today's attendance table
- /attendance/history — pick any past date
- /attendance/api/today — JSON data for dashboard

**Duplicate prevention (3 layers):**
1. 5-second cooldown in camera memory
2. SELECT check in Python before INSERT
3. UNIQUE constraint in MySQL as final safety net

**How attendance is validated once per day:**
Every attendance record stores student_id + date.
The combination is UNIQUE in the database.
Before inserting, we run:
SELECT id FROM attendance WHERE student_id = ? AND date = TODAY
If a row exists → skip insert → show "Already Marked Today"

**How to test:**
```cmd
python attendance_manager.py
```
Edit test_roll to any student roll number.
Run twice to see duplicate prevention in action.

**Files created:**
attendance_manager.py, routes/attendance.py,
templates/attendance/today.html, templates/attendance/history.html

**Files updated:** camera.py, app.py, templates/base.html

---

## 🌐 ALL PAGES AND URLS

| Page | URL | Day Added |
|------|-----|-----------|
| Dashboard | http://127.0.0.1:5000/ | Day 1 |
| Register Student | http://127.0.0.1:5000/students/register | Day 2 |
| All Students | http://127.0.0.1:5000/students/ | Day 2 |
| Student Profile | http://127.0.0.1:5000/students/<id> | Day 2 |
| Capture Photos | http://127.0.0.1:5000/capture/<id> | Day 4 |
| Today's Attendance | http://127.0.0.1:5000/attendance/ | Day 7 |
| Attendance History | http://127.0.0.1:5000/attendance/history | Day 7 |
| API — Stats | http://127.0.0.1:5000/api/stats | Day 1 |
| API — Today's Records | http://127.0.0.1:5000/attendance/api/today | Day 7 |

---

## 🔧 COMPLETE ERROR REFERENCE

### MySQL Errors:
```
Error: 'mysql' is not recognized
Fix:   Add MySQL bin folder to Windows PATH (see Step 2 above)

Error: Can't connect to MySQL server on '1234@localhost'
Fix:   Special character in password. config.py uses quote_plus() — check it's there.

Error: Access denied for user 'root'@'localhost'
Fix:   Wrong password in config.py

Error: Unknown database 'face_attendance_db'
Fix:   Run: python init_db.py
```

### Python Package Errors:
```
Error: No module named 'flask'
Fix:   pip install flask flask-sqlalchemy pymysql cryptography

Error: No module named 'face_recognition'
Fix:   pip install cmake, then pip install dlib, then pip install face-recognition

Error: No module named 'cv2'
Fix:   pip install opencv-python

Error: dlib installation failed / error: Microsoft Visual C++ required
Fix:   Download pre-built dlib wheel from:
       https://github.com/z-mahmud22/Dlib_Windows_Python3.x
```

### Camera Errors:
```
Error: Could not open camera 0
Fix:   Close Zoom/Teams/any app using camera
       Try CAMERA_INDEX = 1 in camera.py

Error: Camera permission denied in browser
Fix:   Click the camera icon in browser address bar → Allow

Error: encodings.pickle not found
Fix:   Run: python encode_faces.py
```

### Recognition Errors:
```
Problem: Always shows "Unknown"
Fix 1:  More training photos — minimum 20-30 per student
Fix 2:  Better lighting — face must be clearly visible
Fix 3:  Increase TOLERANCE = 0.55 in camera.py
Fix 4:  Re-run python encode_faces.py after adding photos

Problem: Wrong person recognized
Fix 1:  Lower TOLERANCE = 0.45 in camera.py (stricter matching)
Fix 2:  More varied training photos

Problem: Very low FPS (below 10)
Fix:    SCALE_FACTOR = 0.25 in camera.py
        PROCESS_EVERY_N = 4 in camera.py
```

### Attendance Errors:
```
Problem: Attendance not being marked
Fix 1:  Confidence >= 60% required — check lighting
Fix 2:  Wait 5 seconds (RECOGNITION_COOLDOWN) between checks
Fix 3:  Test directly: python attendance_manager.py
Fix 4:  Make sure roll_number in dataset/ matches students table

Problem: Duplicate attendance records
Fix:    UniqueConstraint prevents this at DB level
        This error should not occur — if it does, report a bug
```

---

## 🗺️ FULL 10-DAY ROADMAP

| Day | Topic | Status |
|-----|-------|--------|
| Day 1  | Flask Setup + Dashboard UI | ✅ Complete |
| Day 2  | MySQL DB + Student Registration | ✅ Complete |
| Day 3  | Premium UI Polish | ✅ Complete |
| Day 4  | Webcam Dataset Capture | ✅ Complete |
| Day 5  | Face Encoding Generator | ✅ Complete |
| Day 6  | Live Face Recognition | ✅ Complete |
| Day 7  | Attendance Marking Logic | ✅ Complete |
| Day 8  | Reports + PDF/Excel Export | 🔜 Next |
| Day 9  | Admin Login System | 🔜 |
| Day 10 | Final Testing + Deployment | 🔜 |

---

## 🗓️ DAY 8 PREVIEW — Reports & Analytics

**What we will build:**
1. Attendance summary table (weekly / monthly)
2. Per-student report: X days present out of Y working days
3. Department-wise attendance percentage
4. PDF export of any report (using reportlab)
5. Excel export (using openpyxl)
6. Simple bar chart on dashboard (weekly trend)

**New packages needed:**
```cmd
pip install reportlab openpyxl
```

**New files:**
- routes/reports.py
- templates/reports/summary.html
- templates/reports/student_report.html

---

## 💡 TIPS FOR VIVA / PROJECT DEMO

1. Run camera.py in a well-lit room
2. Register yourself as a student first with 30 photos
3. Use Auto-capture mode for dataset collection
4. Show the live "Attendance Marked" notification on screen
5. Show the attendance table at /attendance/ updating in real-time
6. Show duplicate prevention by standing in front of camera again
7. Show history page at /attendance/history with past records
8. Explain the 3-layer duplicate prevention system
9. Mention the database UNIQUE constraint in your presentation
10. The dataset/ folder with student photos is your training data

---

## 📦 PYTHON PACKAGES SUMMARY

| Package | Version | Used For | Day |
|---------|---------|----------|-----|
| flask | 3.0.3 | Web framework | Day 1 |
| flask-sqlalchemy | 3.1.1 | Database ORM | Day 2 |
| pymysql | 1.1.1 | MySQL connector | Day 2 |
| cryptography | 42.0.8 | PyMySQL requirement | Day 2 |
| opencv-python | 4.9.0.80 | Webcam + video | Day 6 |
| numpy | 1.26.4 | Array math | Day 5 |
| Pillow | 10.4.0 | Image loading | Day 5 |
| face-recognition | 1.3.0 | Face detection + encoding | Day 5 |
| dlib | 19.24.x | Face recognition backend | Day 5 |
| cmake | latest | dlib build requirement | Day 5 |

---

*Project: FaceAttend — BCA Final Year Project*
*Built with: Flask + MySQL + OpenCV + face_recognition*
*Progress: Day 7 of 10 complete*
