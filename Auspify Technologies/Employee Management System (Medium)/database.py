"""Database layer for the Employee Management System (SQLite)."""
import csv
import os
import random
import sqlite3
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.db")
DATE_FMT = "%Y-%m-%d"


class EmployeeDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS employees (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_code    TEXT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                email       TEXT,
                phone       TEXT,
                dept_id     INTEGER REFERENCES departments(id),
                designation TEXT,
                salary      REAL NOT NULL CHECK (salary >= 0),
                join_date   TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'Active'
            );
            -- Performance optimization: indexes speed up filtering, sorting and joins
            CREATE INDEX IF NOT EXISTS idx_emp_dept   ON employees(dept_id);
            CREATE INDEX IF NOT EXISTS idx_emp_status ON employees(status);
            CREATE INDEX IF NOT EXISTS idx_emp_name   ON employees(name);
            CREATE INDEX IF NOT EXISTS idx_emp_join   ON employees(join_date);
            """
        )
        self.conn.commit()

    # ========================== DEPARTMENTS ==========================
    def add_department(self, name):
        try:
            self.conn.execute("INSERT INTO departments (name) VALUES (?)", (name,))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Department '{name}' already exists.")

    def rename_department(self, dept_id, name):
        try:
            self.conn.execute("UPDATE departments SET name=? WHERE id=?", (name, dept_id))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Department '{name}' already exists.")

    def delete_department(self, dept_id):
        n = self.conn.execute("SELECT COUNT(*) FROM employees WHERE dept_id=?", (dept_id,)).fetchone()[0]
        if n:
            raise ValueError(f"Cannot delete: {n} employee(s) belong to this department.")
        self.conn.execute("DELETE FROM departments WHERE id=?", (dept_id,))
        self.conn.commit()

    def get_departments(self):
        return self.conn.execute(
            "SELECT d.id, d.name, COUNT(e.id) AS headcount FROM departments d "
            "LEFT JOIN employees e ON e.dept_id = d.id GROUP BY d.id ORDER BY d.name").fetchall()

    # ========================== EMPLOYEES ==========================
    @staticmethod
    def validate_date(text):
        try:
            datetime.strptime(text, DATE_FMT)
        except ValueError:
            raise ValueError("Join date must be in YYYY-MM-DD format.")

    def add_employee(self, emp_code, name, email, phone, dept_id, designation, salary, join_date, status="Active"):
        self.validate_date(join_date)
        try:
            self.conn.execute(
                "INSERT INTO employees (emp_code, name, email, phone, dept_id, designation, salary, join_date, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (emp_code, name, email, phone, dept_id, designation, salary, join_date, status))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Employee code '{emp_code}' already exists.")

    def update_employee(self, emp_id, emp_code, name, email, phone, dept_id, designation, salary, join_date, status):
        self.validate_date(join_date)
        try:
            self.conn.execute(
                "UPDATE employees SET emp_code=?, name=?, email=?, phone=?, dept_id=?, designation=?, "
                "salary=?, join_date=?, status=? WHERE id=?",
                (emp_code, name, email, phone, dept_id, designation, salary, join_date, status, emp_id))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Employee code '{emp_code}' already exists.")

    def delete_employee(self, emp_id):
        self.conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        self.conn.commit()

    @staticmethod
    def _where(keyword, dept_id, status):
        sql, params = " WHERE 1=1", []
        if keyword:
            like = f"%{keyword}%"
            sql += " AND (e.name LIKE ? OR e.emp_code LIKE ? OR e.email LIKE ? OR e.designation LIKE ?)"
            params += [like, like, like, like]
        if dept_id:
            sql += " AND e.dept_id = ?"
            params.append(dept_id)
        if status and status != "All":
            sql += " AND e.status = ?"
            params.append(status)
        return sql, params

    def count_employees(self, keyword="", dept_id=None, status="All"):
        where, params = self._where(keyword, dept_id, status)
        return self.conn.execute("SELECT COUNT(*) FROM employees e" + where, params).fetchone()[0]

    def get_employees(self, keyword="", dept_id=None, status="All", limit=None, offset=0):
        """Paginated query: only `limit` rows are loaded into the UI at a time."""
        where, params = self._where(keyword, dept_id, status)
        sql = ("SELECT e.*, d.name AS dept_name FROM employees e "
               "LEFT JOIN departments d ON d.id = e.dept_id" + where + " ORDER BY e.name")
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params += [limit, offset]
        return self.conn.execute(sql, params).fetchall()

    # ========================== REPORTS ==========================
    def get_summary(self):
        r = self.conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(status='Active'),0) AS active, "
            "COALESCE(SUM(CASE WHEN status='Active' THEN salary END),0) AS payroll, "
            "COALESCE(AVG(CASE WHEN status='Active' THEN salary END),0) AS avg_salary "
            "FROM employees").fetchone()
        out = dict(r)
        out["departments"] = self.conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
        return out

    def department_report(self):
        return self.conn.execute(
            "SELECT COALESCE(d.name,'Unassigned') AS dept, COUNT(*) AS headcount, "
            "AVG(e.salary) AS avg_salary, SUM(e.salary) AS total_salary "
            "FROM employees e LEFT JOIN departments d ON d.id = e.dept_id "
            "WHERE e.status='Active' GROUP BY 1 ORDER BY headcount DESC").fetchall()

    def recent_joiners(self, limit=10):
        return self.conn.execute(
            "SELECT e.emp_code, e.name, d.name AS dept_name, e.designation, e.join_date "
            "FROM employees e LEFT JOIN departments d ON d.id = e.dept_id "
            "ORDER BY e.join_date DESC LIMIT ?", (limit,)).fetchall()

    # ========================== EXPORT / DEMO ==========================
    @staticmethod
    def export_csv(path, headers, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)

    def seed_demo_data(self, count=1000):
        """Insert sample employees in ONE transaction (fast) to test performance."""
        for d in ("Engineering", "HR", "Finance", "Sales", "Marketing", "Operations"):
            self.conn.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (d,))
        dept_ids = [r[0] for r in self.conn.execute("SELECT id FROM departments")]
        first = ["Aarav", "Riya", "Kabir", "Meera", "Arjun", "Isha", "Vikram", "Neha", "Rohan", "Sana"]
        last = ["Sharma", "Verma", "Gupta", "Singh", "Patel", "Khan", "Reddy", "Nair", "Das", "Joshi"]
        titles = ["Associate", "Senior Associate", "Team Lead", "Manager", "Analyst", "Specialist"]
        start = self.conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        rows = []
        for i in range(count):
            n = f"{random.choice(first)} {random.choice(last)}"
            code = f"DEMO{start + i + 1:05d}"
            joined = (date.today() - timedelta(days=random.randint(0, 3000))).strftime(DATE_FMT)
            rows.append((code, n, f"{n.split()[0].lower()}{start + i}@example.com",
                         str(random.randint(6000000000, 9999999999)), random.choice(dept_ids),
                         random.choice(titles), random.randrange(250000, 1800000, 5000),
                         joined, random.choice(["Active"] * 9 + ["Inactive"])))
        with self.conn:
            self.conn.executemany(
                "INSERT OR IGNORE INTO employees (emp_code, name, email, phone, dept_id, designation, "
                "salary, join_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

    def close(self):
        self.conn.close()
