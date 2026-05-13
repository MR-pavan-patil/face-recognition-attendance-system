"""
init_db.py — One-time Database Setup
======================================
Run ONCE after setting up MySQL:
  python init_db.py
"""

import sys

def init_database():
    print("\n" + "═" * 55)
    print("  FaceAttend — Database Initialization")
    print("═" * 55)

    from config import Config
    if "your_password_here" in Config.MYSQL_PASSWORD:
        print("\n⚠️  ERROR: MySQL password not set!")
        print("    Open config.py → change MYSQL_PASSWORD")
        sys.exit(1)

    try:
        import pymysql
        conn = pymysql.connect(
            host=Config.MYSQL_HOST, port=int(Config.MYSQL_PORT),
            user=Config.MYSQL_USER, password=Config.MYSQL_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        conn.commit()
        conn.close()
        print(f"\n✓ Database '{Config.MYSQL_DB}' created / verified")
    except Exception as e:
        print(f"\n✗ MySQL connection failed: {e}")
        print("\nCheck: MySQL running? Password correct in config.py?")
        sys.exit(1)

    try:
        from app import app
        from database import db
        with app.app_context():
            db.create_all()
            print("✓ Tables created: students, student_images, attendance")
    except Exception as e:
        print(f"\n✗ Table creation failed: {e}")
        sys.exit(1)

    print("\n" + "─" * 55)
    print("  ✓ Done! Now run:  python app.py")
    print("  ✓ Open:  http://127.0.0.1:5000")
    print("─" * 55 + "\n")


if __name__ == "__main__":
    init_database()
