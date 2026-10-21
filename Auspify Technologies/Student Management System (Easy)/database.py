"""Database layer for the Student Management System (SQLite)."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")


class StudentDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    def create_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL UNIQUE,
                name    TEXT NOT NULL,
                email   TEXT,
                phone   TEXT,
                course  TEXT,
                age     INTEGER
            )
            """
        )
        self.conn.commit()

    # ---------- CREATE ----------
    def add_student(self, roll_no, name, email, phone, course, age):
        try:
            self.conn.execute(
                "INSERT INTO students (roll_no, name, email, phone, course, age) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (roll_no, name, email, phone, course, age),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Roll number '{roll_no}' already exists.")

    # ---------- READ ----------
    def get_all(self):
        return self.conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()

    def search(self, keyword):
        like = f"%{keyword}%"
        return self.conn.execute(
            "SELECT * FROM students WHERE roll_no LIKE ? OR name LIKE ? "
            "OR course LIKE ? OR email LIKE ? ORDER BY roll_no",
            (like, like, like, like),
        ).fetchall()

    # ---------- UPDATE ----------
    def update_student(self, student_id, roll_no, name, email, phone, course, age):
        try:
            self.conn.execute(
                "UPDATE students SET roll_no=?, name=?, email=?, phone=?, "
                "course=?, age=? WHERE id=?",
                (roll_no, name, email, phone, course, age, student_id),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Roll number '{roll_no}' already exists.")

    # ---------- DELETE ----------
    def delete_student(self, student_id):
        self.conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
