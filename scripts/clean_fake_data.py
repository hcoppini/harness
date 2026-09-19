import sqlite3
from pathlib import Path

def clean_db(db_path=None):
    if db_path is None:
        db_path = Path(__file__).resolve().parent.parent / "data" / "harness.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM school_exams WHERE scope LIKE '%Kłaczkow%' OR title LIKE '%Powstanie Styczniowe%' OR title LIKE '%Kinematyka%' OR title LIKE '%Algorytmy Wyszukiwania%' OR title LIKE '%Trygonometria%'")
    print(f"Deleted {cur.rowcount} fake exams.")
    cur.execute("DELETE FROM homework_items WHERE source = 'vulcan' AND (title LIKE '%plecakowy%' OR notes LIKE '%arkusza CKE%')")
    print(f"Deleted {cur.rowcount} fake homework.")
    conn.commit()
    print("Remaining exams in DB:")
    for r in cur.execute("SELECT id, subject, title, exam_date FROM school_exams").fetchall():
        print("  ", r)
    print("Remaining homework in DB:")
    for r in cur.execute("SELECT id, subject, title, due_date FROM homework_items").fetchall():
        print("  ", r)
    conn.close()

if __name__ == "__main__":
    clean_db()
