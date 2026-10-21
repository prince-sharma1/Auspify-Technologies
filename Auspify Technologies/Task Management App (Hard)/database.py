"""Database layer for the Task Management App (SQLite)."""
import csv
import os
import sqlite3
from datetime import date, datetime, timedelta

from auth import AuthMixin, AuthError

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.db")
DATE_FMT = "%Y-%m-%d"
PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("Pending", "In Progress", "Completed")


class TaskDB(AuthMixin):
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.init_users_table()
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title        TEXT NOT NULL,
                description  TEXT,
                category     TEXT,
                priority     TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low','Medium','High')),
                status       TEXT NOT NULL DEFAULT 'Pending'
                             CHECK (status IN ('Pending','In Progress','Completed')),
                due_date     TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, status, due_date);
            """
        )
        self.conn.commit()

    # ---------------------------------------------------------- validation
    @staticmethod
    def _check(title, priority, status, due_date):
        if not title.strip():
            raise ValueError("Task title is required.")
        if priority not in PRIORITIES:
            raise ValueError("Invalid priority.")
        if status not in STATUSES:
            raise ValueError("Invalid status.")
        try:
            datetime.strptime(due_date, DATE_FMT)
        except ValueError:
            raise ValueError("Due date must be in YYYY-MM-DD format.")

    @staticmethod
    def _completed_at(status):
        return datetime.now().strftime("%Y-%m-%d %H:%M") if status == "Completed" else None

    # ---------------------------------------------------------- CRUD (every query is scoped to user_id)
    def add_task(self, user_id, title, description, category, priority, status, due_date):
        self._check(title, priority, status, due_date)
        self.conn.execute(
            "INSERT INTO tasks (user_id, title, description, category, priority, status, due_date, "
            "created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, title.strip(), description.strip(), category.strip(), priority, status, due_date,
             datetime.now().strftime("%Y-%m-%d %H:%M"), self._completed_at(status)))
        self.conn.commit()

    def update_task(self, user_id, task_id, title, description, category, priority, status, due_date):
        self._check(title, priority, status, due_date)
        cur = self.conn.execute(
            "UPDATE tasks SET title=?, description=?, category=?, priority=?, status=?, due_date=?, "
            "completed_at=? WHERE id=? AND user_id=?",
            (title.strip(), description.strip(), category.strip(), priority, status, due_date,
             self._completed_at(status), task_id, user_id))
        if cur.rowcount == 0:
            raise PermissionError("Task not found or not yours.")
        self.conn.commit()

    def set_status(self, user_id, task_id, status):
        if status not in STATUSES:
            raise ValueError("Invalid status.")
        cur = self.conn.execute("UPDATE tasks SET status=?, completed_at=? WHERE id=? AND user_id=?",
                                (status, self._completed_at(status), task_id, user_id))
        if cur.rowcount == 0:
            raise PermissionError("Task not found or not yours.")
        self.conn.commit()

    def delete_task(self, user_id, task_id):
        cur = self.conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
        if cur.rowcount == 0:
            raise PermissionError("Task not found or not yours.")
        self.conn.commit()

    def get_tasks(self, user_id, keyword="", status="All", priority="All", sort="Due date"):
        like = f"%{keyword}%"
        sql = ("SELECT * FROM tasks WHERE user_id=? AND (title LIKE ? OR description LIKE ? OR category LIKE ?)")
        params = [user_id, like, like, like]
        if status != "All":
            sql += " AND status=?"; params.append(status)
        if priority != "All":
            sql += " AND priority=?"; params.append(priority)
        order = {
            "Due date": "due_date ASC",
            "Priority": "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, due_date ASC",
            "Newest": "id DESC",
        }.get(sort, "due_date ASC")
        # completed tasks sink to the bottom for the default views
        return self.conn.execute(sql + f" ORDER BY (status='Completed'), {order}", params).fetchall()

    # ---------------------------------------------------------- deadlines / reminders
    def get_reminders(self, user_id):
        """Open tasks that are overdue or due today."""
        today = date.today().strftime(DATE_FMT)
        return self.conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND status != 'Completed' AND due_date <= ? ORDER BY due_date",
            (user_id, today)).fetchall()

    def get_upcoming(self, user_id, days=7):
        today = date.today()
        end = (today + timedelta(days=days)).strftime(DATE_FMT)
        return self.conn.execute(
            "SELECT * FROM tasks WHERE user_id=? AND status != 'Completed' AND due_date > ? AND due_date <= ? "
            "ORDER BY due_date", (user_id, today.strftime(DATE_FMT), end)).fetchall()

    # ---------------------------------------------------------- dashboard
    def get_stats(self, user_id):
        today = date.today().strftime(DATE_FMT)
        r = self.conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(status='Completed'),0) AS completed, "
            "COALESCE(SUM(status='In Progress'),0) AS in_progress, "
            "COALESCE(SUM(status='Pending'),0) AS pending, "
            "COALESCE(SUM(status != 'Completed' AND due_date < ?),0) AS overdue, "
            "COALESCE(SUM(priority='High'),0) AS high, "
            "COALESCE(SUM(priority='Medium'),0) AS medium, "
            "COALESCE(SUM(priority='Low'),0) AS low "
            "FROM tasks WHERE user_id=?", (today, user_id)).fetchone()
        s = dict(r)
        s["percent_done"] = round(s["completed"] * 100 / s["total"]) if s["total"] else 0
        return s

    @staticmethod
    def export_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Title", "Description", "Category", "Priority", "Status", "Due Date", "Created", "Completed"])
            for t in rows:
                w.writerow([t["title"], t["description"], t["category"], t["priority"], t["status"],
                            t["due_date"], t["created_at"], t["completed_at"] or ""])

    def close(self):
        self.conn.close()
