"""
init_db.py — One-time Database Setup (Supabase)
=================================================
Run ONCE after setting your Supabase details in config.py:
  python init_db.py
"""
import sys

def init_database():
    print("\n" + "═" * 55)
    print("  FaceAttend — Supabase Database Initialization")
    print("═" * 55)

    from config import Config

    if "YOUR_PASSWORD_HERE" in Config.SUPABASE_PASSWORD or "YOUR_PROJECT_REF" in Config.SUPABASE_HOST:
        print("\n⚠️  ERROR: Supabase details not set in config.py!")
        print("\n  Open config.py and fill in:")
        print("  SUPABASE_HOST     = 'db.xxxxxx.supabase.co'")
        print("  SUPABASE_PASSWORD = 'your_actual_password'")
        print("\n  (Supabase → Project Settings → Database → Connection parameters)")
        sys.exit(1)

    print(f"\n  Connecting to: {Config.SUPABASE_HOST}")

    try:
        from app import app
        from database import db
        with app.app_context():
            db.create_all()
            print("\n✓ Tables created: students, student_images, attendance")
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nCheck:")
        print("  • SUPABASE_HOST correct in config.py?")
        print("  • SUPABASE_PASSWORD correct?")
        print("  • Internet connection working?")
        sys.exit(1)

    print("\n" + "─" * 55)
    print("  ✓ Done! Now run:  python app.py")
    print("  ✓ Open:  http://127.0.0.1:5000")
    print("─" * 55 + "\n")

if __name__ == "__main__":
    init_database()
