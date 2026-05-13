"""
models.py — Database Models
=============================
Tables:
  1. students       — registered student info
  2. student_images — uploaded photo paths
  3. attendance     — daily attendance records (used Day 6+)
"""

from datetime import datetime
from database import db


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
