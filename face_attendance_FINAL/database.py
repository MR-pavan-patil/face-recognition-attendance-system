"""
database.py — SQLAlchemy Instance
===================================
Single db object used across the entire project.
Prevents circular imports between app.py and models.py
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
