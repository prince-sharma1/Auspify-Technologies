"""Database layer for the Online Examination System (SQLite)."""
import csv
import os
import sqlite3
from datetime import datetime, timedelta

from auth import AuthMixin, AuthError

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exam.db")
TS_FMT = "%Y-%m-%d %H:%M:%S"
GRACE_SECONDS = 60          # extra time allowed for the final submit after the timer ends
DEFAULT_ADMIN = ("admin", "Administrator", "Admin@123")


class ExamDB(AuthMixin):
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()
        self.ensure_default_admin()
        self.finalize_expired_attempts()

    # ------------------------------------------------------------ setup
    def create_tables(self):
        self.init_users_table()
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS exams (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                subject      TEXT,
                duration_min INTEGER NOT NULL CHECK (duration_min > 0),
                pass_percent INTEGER NOT NULL CHECK (pass_percent BETWEEN 0 AND 100),
                active       INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS questions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id   INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
                text      TEXT NOT NULL,
                opt_a     TEXT NOT NULL,
                opt_b     TEXT NOT NULL,
                opt_c     TEXT NOT NULL,
                opt_d     TEXT NOT NULL,
                correct   TEXT NOT NULL CHECK (correct IN ('A','B','C','D')),
                marks     INTEGER NOT NULL DEFAULT 1 CHECK (marks > 0)
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id      INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                started_at   TEXT NOT NULL,
                submitted_at TEXT,
                score        INTEGER,
                total        INTEGER,
                percent      REAL,
                passed       INTEGER,
                UNIQUE (exam_id, user_id)          -- one attempt per student per exam
            );
            CREATE TABLE IF NOT EXISTS answers (
                attempt_id  INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
                question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                selected    TEXT NOT NULL CHECK (selected IN ('A','B','C','D')),
                PRIMARY KEY (attempt_id, question_id)
            );
            """
        )
        self.conn.commit()

    def ensure_default_admin(self):
        has_admin = self.conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
        if not has_admin:
            self.register(DEFAULT_ADMIN[0], DEFAULT_ADMIN[1], DEFAULT_ADMIN[2], role="admin")

    def register_student(self, username, full_name, password):
        return self.register(username, full_name, password, role="student")

    # ------------------------------------------------------------ exams
    @staticmethod
    def _check_exam(title, duration, pass_percent):
        if not title.strip():
            raise ValueError("Exam title is required.")
        if not (1 <= duration <= 600):
            raise ValueError("Duration must be between 1 and 600 minutes.")
        if not (0 <= pass_percent <= 100):
            raise ValueError("Pass percentage must be between 0 and 100.")

    def add_exam(self, title, subject, duration, pass_percent):
        self._check_exam(title, duration, pass_percent)
        cur = self.conn.execute(
            "INSERT INTO exams (title, subject, duration_min, pass_percent) VALUES (?, ?, ?, ?)",
            (title.strip(), subject.strip(), duration, pass_percent))
        self.conn.commit()
        return cur.lastrowid

    def update_exam(self, exam_id, title, subject, duration, pass_percent):
        self._check_exam(title, duration, pass_percent)
        self.conn.execute("UPDATE exams SET title=?, subject=?, duration_min=?, pass_percent=? WHERE id=?",
                          (title.strip(), subject.strip(), duration, pass_percent, exam_id))
        self.conn.commit()

    def delete_exam(self, exam_id):
        self.conn.execute("DELETE FROM exams WHERE id=?", (exam_id,))
        self.conn.commit()

    def toggle_exam(self, exam_id):
        self.conn.execute("UPDATE exams SET active = 1 - active WHERE id=?", (exam_id,))
        self.conn.commit()

    def get_exams(self, only_active=False):
        sql = ("SELECT e.*, (SELECT COUNT(*) FROM questions q WHERE q.exam_id = e.id) AS question_count, "
               "(SELECT COALESCE(SUM(marks),0) FROM questions q WHERE q.exam_id = e.id) AS total_marks "
               "FROM exams e")
        if only_active:
            sql += " WHERE e.active = 1"
        return self.conn.execute(sql + " ORDER BY e.title").fetchall()

    def get_exam(self, exam_id):
        return self.conn.execute("SELECT * FROM exams WHERE id=?", (exam_id,)).fetchone()

    # ------------------------------------------------------------ questions
    @staticmethod
    def _check_question(text, options, correct, marks):
        if not text.strip() or any(not o.strip() for o in options):
            raise ValueError("Question text and all four options are required.")
        if correct not in ("A", "B", "C", "D"):
            raise ValueError("Correct answer must be A, B, C or D.")
        if marks < 1:
            raise ValueError("Marks must be at least 1.")

    def add_question(self, exam_id, text, a, b, c, d, correct, marks=1):
        self._check_question(text, (a, b, c, d), correct, marks)
        self.conn.execute(
            "INSERT INTO questions (exam_id, text, opt_a, opt_b, opt_c, opt_d, correct, marks) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (exam_id, text.strip(), a.strip(), b.strip(), c.strip(), d.strip(), correct, marks))
        self.conn.commit()

    def update_question(self, q_id, text, a, b, c, d, correct, marks=1):
        self._check_question(text, (a, b, c, d), correct, marks)
        self.conn.execute(
            "UPDATE questions SET text=?, opt_a=?, opt_b=?, opt_c=?, opt_d=?, correct=?, marks=? WHERE id=?",
            (text.strip(), a.strip(), b.strip(), c.strip(), d.strip(), correct, marks, q_id))
        self.conn.commit()

    def delete_question(self, q_id):
        self.conn.execute("DELETE FROM questions WHERE id=?", (q_id,))
        self.conn.commit()

    def get_questions(self, exam_id, include_answers=False):
        """Students call this WITHOUT answers, so correct answers never reach the exam screen."""
        cols = "id, exam_id, text, opt_a, opt_b, opt_c, opt_d, marks"
        if include_answers:
            cols += ", correct"
        return self.conn.execute(f"SELECT {cols} FROM questions WHERE exam_id=? ORDER BY id",
                                 (exam_id,)).fetchall()

    # ------------------------------------------------------------ attempts
    def get_attempt_for(self, exam_id, user_id):
        return self.conn.execute("SELECT * FROM attempts WHERE exam_id=? AND user_id=?",
                                 (exam_id, user_id)).fetchone()

    def start_attempt(self, exam_id, user_id):
        exam = self.get_exam(exam_id)
        if exam is None or not exam["active"]:
            raise ValueError("This exam is not available.")
        if not self.get_questions(exam_id):
            raise ValueError("This exam has no questions yet.")
        if self.get_attempt_for(exam_id, user_id):
            raise ValueError("You have already attempted this exam.")
        cur = self.conn.execute("INSERT INTO attempts (exam_id, user_id, started_at) VALUES (?, ?, ?)",
                                (exam_id, user_id, datetime.now().strftime(TS_FMT)))
        self.conn.commit()
        return cur.lastrowid

    def submit_attempt(self, attempt_id, user_id, answers):
        """
        Result calculation is done HERE, from the database - never trusted from the UI.
        answers: {question_id: 'A'|'B'|'C'|'D'}
        """
        att = self.conn.execute(
            "SELECT a.*, e.duration_min, e.pass_percent FROM attempts a JOIN exams e ON e.id = a.exam_id "
            "WHERE a.id=?", (attempt_id,)).fetchone()
        if att is None or att["user_id"] != user_id:
            raise PermissionError("This attempt does not belong to you.")
        if att["submitted_at"]:
            raise ValueError("This exam has already been submitted.")

        now = datetime.now()
        deadline = (datetime.strptime(att["started_at"], TS_FMT)
                    + timedelta(minutes=att["duration_min"], seconds=GRACE_SECONDS))
        if now > deadline:
            answers = {}                       # too late: answers are rejected

        valid_ids = {r["id"] for r in self.conn.execute(
            "SELECT id FROM questions WHERE exam_id=?", (att["exam_id"],))}
        with self.conn:
            for qid, sel in answers.items():
                if qid in valid_ids and sel in ("A", "B", "C", "D"):
                    self.conn.execute("INSERT OR REPLACE INTO answers (attempt_id, question_id, selected) "
                                      "VALUES (?, ?, ?)", (attempt_id, qid, sel))
            total = self.conn.execute("SELECT COALESCE(SUM(marks),0) FROM questions WHERE exam_id=?",
                                      (att["exam_id"],)).fetchone()[0]
            score = self.conn.execute(
                "SELECT COALESCE(SUM(q.marks),0) FROM answers a JOIN questions q ON q.id = a.question_id "
                "WHERE a.attempt_id=? AND a.selected = q.correct", (attempt_id,)).fetchone()[0]
            percent = round(score * 100.0 / total, 2) if total else 0.0
            passed = 1 if percent >= att["pass_percent"] else 0
            self.conn.execute(
                "UPDATE attempts SET submitted_at=?, score=?, total=?, percent=?, passed=? WHERE id=?",
                (now.strftime(TS_FMT), score, total, percent, passed, attempt_id))
        return {"score": score, "total": total, "percent": percent, "passed": bool(passed)}

    def finalize_expired_attempts(self):
        """Attempts left open (app closed / crashed) are closed once their time is over."""
        rows = self.conn.execute(
            "SELECT a.id, a.user_id, a.started_at, e.duration_min FROM attempts a "
            "JOIN exams e ON e.id = a.exam_id WHERE a.submitted_at IS NULL").fetchall()
        for r in rows:
            deadline = (datetime.strptime(r["started_at"], TS_FMT)
                        + timedelta(minutes=r["duration_min"], seconds=GRACE_SECONDS))
            if datetime.now() > deadline:
                self.submit_attempt(r["id"], r["user_id"], {})

    # ------------------------------------------------------------ reports
    def get_results(self, exam_id=None, user_id=None):
        sql = ("SELECT a.id, u.full_name, u.username, e.title, a.score, a.total, a.percent, a.passed, "
               "a.submitted_at FROM attempts a JOIN users u ON u.id = a.user_id "
               "JOIN exams e ON e.id = a.exam_id WHERE a.submitted_at IS NOT NULL")
        params = []
        if exam_id:
            sql += " AND a.exam_id=?"; params.append(exam_id)
        if user_id:
            sql += " AND a.user_id=?"; params.append(user_id)
        return self.conn.execute(sql + " ORDER BY a.submitted_at DESC", params).fetchall()

    def get_stats(self, exam_id=None):
        sql = ("SELECT COUNT(*) AS attempts, COALESCE(AVG(percent),0) AS avg_percent, "
               "COALESCE(MAX(percent),0) AS highest, COALESCE(MIN(percent),0) AS lowest, "
               "COALESCE(SUM(passed),0) AS passed FROM attempts WHERE submitted_at IS NOT NULL")
        params = []
        if exam_id:
            sql += " AND exam_id=?"; params.append(exam_id)
        return dict(self.conn.execute(sql, params).fetchone())

    def get_attempt_detail(self, attempt_id, requester):
        """Score report. Only the owner of the attempt or an admin may view it."""
        att = self.conn.execute(
            "SELECT a.*, e.title, e.pass_percent, u.full_name FROM attempts a "
            "JOIN exams e ON e.id = a.exam_id JOIN users u ON u.id = a.user_id WHERE a.id=?",
            (attempt_id,)).fetchone()
        if att is None:
            raise ValueError("Attempt not found.")
        if requester["role"] != "admin" and att["user_id"] != requester["id"]:
            raise PermissionError("You are not allowed to view this report.")
        if not att["submitted_at"]:
            raise ValueError("This attempt has not been submitted yet.")
        rows = self.conn.execute(
            "SELECT q.id, q.text, q.opt_a, q.opt_b, q.opt_c, q.opt_d, q.correct, q.marks, a.selected "
            "FROM questions q LEFT JOIN answers a ON a.question_id = q.id AND a.attempt_id = ? "
            "WHERE q.exam_id = ? ORDER BY q.id", (attempt_id, att["exam_id"])).fetchall()
        return att, rows

    @staticmethod
    def export_csv(path, headers, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)

    # ------------------------------------------------------------ demo
    def load_sample_exam(self):
        exam_id = self.add_exam("Python Basics Quiz", "Programming", 10, 50)
        qs = [
            ("Which keyword defines a function in Python?", "func", "def", "function", "lambda", "B"),
            ("What is the output of len([1, 2, 3])?", "2", "3", "4", "Error", "B"),
            ("Which data type is immutable?", "list", "dict", "tuple", "set", "C"),
            ("Which symbol starts a single-line comment?", "//", "#", "/*", "--", "B"),
            ("What does 'pip' do?", "Runs tests", "Installs packages", "Compiles code", "Formats code", "B"),
        ]
        for text, a, b, c, d, correct in qs:
            self.add_question(exam_id, text, a, b, c, d, correct, 2)
        return exam_id

    def close(self):
        self.conn.close()
