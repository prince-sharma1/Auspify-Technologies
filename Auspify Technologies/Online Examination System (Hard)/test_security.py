"""
Security test script  -  Task 5 workflow Step 5: "Test system security".
Run:  python test_security.py
Uses a temporary database, so your real data is not touched.
"""
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

from auth import AuthError, MAX_FAILED_ATTEMPTS
from database import ExamDB

results = []


def check(name, condition):
    results.append(condition)
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")


def raises(exc, fn, *a):
    try:
        fn(*a)
    except exc:
        return True
    except Exception:
        return False
    return False


db = ExamDB(os.path.join(tempfile.mkdtemp(), "sec_test.db"))
db.register_student("alice", "Alice A", "Passw0rdA1")
db.register_student("bob", "Bob B", "Passw0rdB2")
alice, bob = db.login("alice", "Passw0rdA1"), db.login("bob", "Passw0rdB2")

# 1 - passwords are hashed + salted
row = db.conn.execute("SELECT password_hash, salt FROM users WHERE username='alice'").fetchone()
check("Password is not stored in plain text", "Passw0rdA1" not in row["password_hash"])
check("Salt is stored and hash is 64 hex chars (SHA-256)", len(row["salt"]) == 32 and len(row["password_hash"]) == 64)
db.register_student("carol", "Carol C", "Passw0rdA1")
rows = db.conn.execute("SELECT password_hash FROM users WHERE username IN ('alice','carol')").fetchall()
check("Same password gives different hashes (unique salt)", rows[0][0] != rows[1][0])

# 2 - password policy and username rules
check("Weak password (too short) rejected", raises(AuthError, db.register_student, "dave", "Dave", "abc1"))
check("Weak password (no number) rejected", raises(AuthError, db.register_student, "dave", "Dave", "onlyletters"))
check("Invalid username rejected", raises(AuthError, db.register_student, "bad name!", "X", "Passw0rd1"))
check("Duplicate username rejected (case-insensitive)", raises(AuthError, db.register_student, "ALICE", "X", "Passw0rd1"))

# 3 - SQL injection
check("SQL injection in username fails", raises(AuthError, db.login, "' OR '1'='1' --", "x"))
check("SQL injection in password fails", raises(AuthError, db.login, "alice", "' OR '1'='1"))
check("Users table still intact after attacks", db.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 3)

# 4 - generic error message
msgs = set()
for u, p in (("alice", "wrongpass1"), ("nobody", "wrongpass1")):
    try:
        db.login(u, p)
    except AuthError as e:
        msgs.add(str(e))
check("Same error for wrong password and unknown user", len(msgs) == 1)

# 5 - brute force lockout
for _ in range(MAX_FAILED_ATTEMPTS):
    try:
        db.login("bob", "wrong-guess1")
    except AuthError:
        pass
check("Account locks after repeated failures", raises(AuthError, db.login, "bob", "Passw0rdB2"))
db.conn.execute("UPDATE users SET locked_until=? WHERE username='bob'",
                ((datetime.now() - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S"),))
db.conn.commit()
check("Account unlocks after lock period", db.login("bob", "Passw0rdB2")["username"] == "bob")

# 6 - exam security
exam_id = db.load_sample_exam()
qs = db.get_questions(exam_id)
check("Student question list does not contain correct answers", "correct" not in qs[0].keys())
att = db.start_attempt(exam_id, alice["id"])
check("Second attempt of same exam is blocked", raises(ValueError, db.start_attempt, exam_id, alice["id"]))
check("Student cannot submit another student's attempt", raises(PermissionError, db.submit_attempt, att, bob["id"], {}))
res = db.submit_attempt(att, alice["id"], {qs[0]["id"]: "B", 99999: "A", qs[1]["id"]: "Z"})
check("Fake question IDs / invalid options are ignored (score = 2 of 10)", res["score"] == 2 and res["total"] == 10)
check("Cannot submit the same attempt twice", raises(ValueError, db.submit_attempt, att, alice["id"], {qs[0]["id"]: "B"}))
check("Student cannot view another student's report",
      raises(PermissionError, db.get_attempt_detail, att, {"id": bob["id"], "role": "student"}))
check("Owner can view own report", db.get_attempt_detail(att, {"id": alice["id"], "role": "student"}) is not None)

# 7 - late submission rejected
att2 = db.start_attempt(exam_id, bob["id"])
old = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
db.conn.execute("UPDATE attempts SET started_at=? WHERE id=?", (old, att2))
db.conn.commit()
late = db.submit_attempt(att2, bob["id"], {q["id"]: "B" for q in qs})
check("Answers sent after the time limit are rejected (score 0)", late["score"] == 0)

# 8 - role check
check("Default admin account exists with admin role", db.login("admin", "Admin@123")["role"] == "admin")

print(f"\n{sum(results)} / {len(results)} security checks passed")
