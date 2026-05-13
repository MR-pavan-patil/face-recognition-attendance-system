"""
models.py — Database Models
=============================
Tables:
  1. users          — admin, teacher, student login accounts
  2. students       — registered student info
  3. student_images — uploaded photo paths
  4. attendance     — daily attendance records
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database import db


# ── Role Constants ────────────────────────────────────────────
ROLE_ADMIN   = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"


class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username   = db.Column(db.String(50),  nullable=False, unique=True)
    password   = db.Column(db.String(255), nullable=False)   # werkzeug hash
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), nullable=True)
    role       = db.Column(db.String(20),  nullable=False, default=ROLE_TEACHER)
    department = db.Column(db.String(80),  nullable=True)    # Teacher dept scope
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw):
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_teacher(self):
        return self.role == ROLE_TEACHER

    @property
    def is_student(self):
        return self.role == ROLE_STUDENT

    def to_dict(self):
        return {
            "id"        : self.id,
            "username"  : self.username,
            "name"      : self.name,
            "email"     : self.email or "",
            "role"      : self.role,
            "department": self.department or "",
            "is_active" : self.is_active,
            "created_at": self.created_at.strftime("%d %b %Y") if self.created_at else "",
        }

    def __repr__(self):
        return f"<User {self.username} role={self.role}>"


class Student(db.Model):
    __tablename__ = "students"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name        = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20),  nullable=False, unique=True)
    email       = db.Column(db.String(120), nullable=False, unique=True)
    phone       = db.Column(db.String(15),  nullable=True)
    department  = db.Column(db.String(80),  nullable=False)
    year        = db.Column(db.String(10),  nullable=False)
    section     = db.Column(db.String(5),   nullable=True)

    is_active     = db.Column(db.Boolean, default=True)
    dataset_ready = db.Column(db.Boolean, default=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images             = db.relationship("StudentImage", backref="student", lazy=True, cascade="all, delete-orphan")
    attendance_records = db.relationship("Attendance",   backref="student", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.roll_number} — {self.name}>"

    def to_dict(self):
        return {
            "id"           : self.id,
            "name"         : self.name,
            "roll_number"  : self.roll_number,
            "email"        : self.email,
            "phone"        : self.phone or "",
            "department"   : self.department,
            "year"         : self.year,
            "section"      : self.section or "",
            "is_active"    : self.is_active,
            "dataset_ready": self.dataset_ready,
            "photo_count"  : len(self.images),
            "registered_at": self.registered_at.strftime("%d %b %Y, %I:%M %p"),
        }


class StudentImage(db.Model):
    __tablename__ = "student_images"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    filename    = db.Column(db.String(200), nullable=False)
    filepath    = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StudentImage student_id={self.student_id} file={self.filename}>"


class Attendance(db.Model):
    __tablename__ = "attendance"

    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    date       = db.Column(db.Date,    nullable=False, default=datetime.utcnow().date)
    time_in    = db.Column(db.Time,    nullable=True)
    status     = db.Column(db.String(10), nullable=False, default="Present")
    marked_by  = db.Column(db.String(20), default="System")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("student_id", "date", name="unique_attendance_per_day"),
    )

    def __repr__(self):
        return f"<Attendance student_id={self.student_id} date={self.date} status={self.status}>"

    def to_dict(self):
        return {
            "id"        : self.id,
            "student_id": self.student_id,
            "date"      : str(self.date),
            "time_in"   : str(self.time_in) if self.time_in else "--",
            "status"    : self.status,
            "marked_by" : self.marked_by,
        }
