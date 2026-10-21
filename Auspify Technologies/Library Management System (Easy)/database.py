"""Database layer for the Library Management System (SQLite)."""
import sqlite3
import os
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library.db")
FINE_PER_DAY = 5          # fine amount per overdue day
LOAN_DAYS = 14            # default loan period
DATE_FMT = "%Y-%m-%d"


class LibraryDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                title            TEXT NOT NULL,
                author           TEXT NOT NULL,
                isbn             TEXT NOT NULL UNIQUE,
                category         TEXT,
                total_copies     INTEGER NOT NULL CHECK (total_copies >= 0),
                available_copies INTEGER NOT NULL CHECK (available_copies >= 0)
            );
            CREATE TABLE IF NOT EXISTS members (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL,
                phone TEXT,
                email TEXT
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL REFERENCES books(id),
                member_id   INTEGER NOT NULL REFERENCES members(id),
                issue_date  TEXT NOT NULL,
                due_date    TEXT NOT NULL,
                return_date TEXT,
                fine        INTEGER DEFAULT 0
            );
            """
        )
        self.conn.commit()

    # ============================ BOOKS ============================
    def add_book(self, title, author, isbn, category, copies):
        try:
            self.conn.execute(
                "INSERT INTO books (title, author, isbn, category, total_copies, available_copies) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title, author, isbn, category, copies, copies),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"A book with ISBN '{isbn}' already exists.")

    def update_book(self, book_id, title, author, isbn, category, copies):
        row = self.conn.execute("SELECT total_copies, available_copies FROM books WHERE id=?",
                                (book_id,)).fetchone()
        if row is None:
            raise ValueError("Book not found.")
        issued = row["total_copies"] - row["available_copies"]
        if copies < issued:
            raise ValueError(f"Total copies cannot be less than copies currently issued ({issued}).")
        try:
            self.conn.execute(
                "UPDATE books SET title=?, author=?, isbn=?, category=?, "
                "total_copies=?, available_copies=? WHERE id=?",
                (title, author, isbn, category, copies, copies - issued, book_id),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"A book with ISBN '{isbn}' already exists.")

    def delete_book(self, book_id):
        active = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE book_id=? AND return_date IS NULL",
            (book_id,)).fetchone()[0]
        if active:
            raise ValueError("This book is currently issued and cannot be deleted.")
        self.conn.execute("DELETE FROM transactions WHERE book_id=?", (book_id,))
        self.conn.execute("DELETE FROM books WHERE id=?", (book_id,))
        self.conn.commit()

    def get_books(self, keyword="", only_available=False):
        like = f"%{keyword}%"
        sql = ("SELECT * FROM books WHERE (title LIKE ? OR author LIKE ? "
               "OR isbn LIKE ? OR category LIKE ?)")
        if only_available:
            sql += " AND available_copies > 0"
        return self.conn.execute(sql + " ORDER BY title", (like, like, like, like)).fetchall()

    # ============================ MEMBERS ============================
    def add_member(self, name, phone, email):
        self.conn.execute("INSERT INTO members (name, phone, email) VALUES (?, ?, ?)",
                          (name, phone, email))
        self.conn.commit()

    def update_member(self, member_id, name, phone, email):
        self.conn.execute("UPDATE members SET name=?, phone=?, email=? WHERE id=?",
                          (name, phone, email, member_id))
        self.conn.commit()

    def delete_member(self, member_id):
        active = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE member_id=? AND return_date IS NULL",
            (member_id,)).fetchone()[0]
        if active:
            raise ValueError("This member still has books issued and cannot be deleted.")
        self.conn.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
        self.conn.execute("DELETE FROM members WHERE id=?", (member_id,))
        self.conn.commit()

    def get_members(self, keyword=""):
        like = f"%{keyword}%"
        return self.conn.execute(
            "SELECT * FROM members WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY name",
            (like, like, like)).fetchall()

    # ========================= ISSUE / RETURN =========================
    def issue_book(self, book_id, member_id, days=LOAN_DAYS):
        book = self.conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if book is None:
            raise ValueError("Book not found.")
        if book["available_copies"] <= 0:
            raise ValueError("No copies of this book are available right now.")
        already = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE book_id=? AND member_id=? AND return_date IS NULL",
            (book_id, member_id)).fetchone()[0]
        if already:
            raise ValueError("This member already has a copy of this book.")

        today = date.today()
        due = today + timedelta(days=days)
        self.conn.execute(
            "INSERT INTO transactions (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
            (book_id, member_id, today.strftime(DATE_FMT), due.strftime(DATE_FMT)))
        self.conn.execute("UPDATE books SET available_copies = available_copies - 1 WHERE id=?",
                          (book_id,))
        self.conn.commit()
        return due.strftime(DATE_FMT)

    def return_book(self, transaction_id, return_on=None):
        t = self.conn.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if t is None or t["return_date"] is not None:
            raise ValueError("This transaction is not an active issue.")
        returned = return_on or date.today()
        due = datetime.strptime(t["due_date"], DATE_FMT).date()
        fine = max(0, (returned - due).days) * FINE_PER_DAY
        self.conn.execute("UPDATE transactions SET return_date=?, fine=? WHERE id=?",
                          (returned.strftime(DATE_FMT), fine, transaction_id))
        self.conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id=?",
                          (t["book_id"],))
        self.conn.commit()
        return fine

    # ============================ REPORTS ============================
    _TX_SELECT = (
        "SELECT t.id AS id, b.title AS title, m.name AS member, t.issue_date AS issue_date, "
        "t.due_date AS due_date, t.return_date AS return_date, t.fine AS fine "
        "FROM transactions t JOIN books b ON b.id = t.book_id "
        "JOIN members m ON m.id = t.member_id "
    )

    def get_active_issues(self):
        return self.conn.execute(
            self._TX_SELECT + "WHERE t.return_date IS NULL ORDER BY t.due_date").fetchall()

    def get_overdue(self):
        today = date.today().strftime(DATE_FMT)
        return self.conn.execute(
            self._TX_SELECT + "WHERE t.return_date IS NULL AND t.due_date < ? ORDER BY t.due_date",
            (today,)).fetchall()

    def get_history(self):
        return self.conn.execute(self._TX_SELECT + "ORDER BY t.id DESC").fetchall()

    def get_summary(self):
        q = lambda sql, *a: self.conn.execute(sql, a).fetchone()[0] or 0
        today = date.today().strftime(DATE_FMT)
        return {
            "Total book titles": q("SELECT COUNT(*) FROM books"),
            "Total copies": q("SELECT SUM(total_copies) FROM books"),
            "Copies available": q("SELECT SUM(available_copies) FROM books"),
            "Copies currently issued": q("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL"),
            "Overdue books": q("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL AND due_date < ?", today),
            "Total members": q("SELECT COUNT(*) FROM members"),
            "Total fines collected": q("SELECT SUM(fine) FROM transactions"),
        }

    def close(self):
        self.conn.close()
