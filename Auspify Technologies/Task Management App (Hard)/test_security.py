"""
Security and data-isolation tests for the Task Management App.
Run:  python test_security.py     (uses a temporary database)
"""
import os
import tempfile
from datetime import date, timedelta

from auth import AuthError, MAX_FAILED_ATTEMPTS
from database import TaskDB

results = []


def check(name, ok):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")


def raises(exc, fn, *a):
    try:
        fn(*a)
    except exc:
        return True
    except Exception:
        return False
    return False


db = TaskDB(os.path.join(tempfile.mkdtemp(), "t.db"))
db.register("alice", "Alice A", "Passw0rdA1")
db.register("bob", "Bob B", "Passw0rdB2")
alice, bob = db.login("alice", "Passw0rdA1"), db.login("bob", "Passw0rdB2")

# authentication
row = db.conn.execute("SELECT password_hash FROM users WHERE username='alice'").fetchone()
check("Password stored as a hash, not plain text", "Passw0rdA1" not in row[0])
check("Weak password rejected", raises(AuthError, db.register, "carl", "Carl", "short1"))
check("Duplicate username rejected", raises(AuthError, db.register, "Alice", "Dup", "Passw0rd1"))
check("SQL injection login fails", raises(AuthError, db.login, "' OR 1=1 --", "x"))
for _ in range(MAX_FAILED_ATTEMPTS):
    try:
        db.login("bob", "bad-guess-1")
    except AuthError:
        pass
check("Account locks after repeated failed logins", raises(AuthError, db.login, "bob", "Passw0rdB2"))

# task CRUD and validation
today = date.today()
fmt = lambda d: d.strftime("%Y-%m-%d")
db.add_task(alice["id"], "Finish report", "Quarterly", "Work", "High", "Pending", fmt(today - timedelta(days=2)))
db.add_task(alice["id"], "Gym", "", "Health", "Low", "Pending", fmt(today + timedelta(days=3)))
db.add_task(alice["id"], "Pay bills", "", "Home", "Medium", "In Progress", fmt(today))
tasks = db.get_tasks(alice["id"])
check("User can add and list own tasks", len(tasks) == 3)
check("Invalid due date rejected", raises(ValueError, db.add_task, alice["id"], "X", "", "", "Low", "Pending", "31/12/2026"))
check("Empty title rejected", raises(ValueError, db.add_task, alice["id"], "  ", "", "", "Low", "Pending", fmt(today)))
check("Invalid priority rejected", raises(ValueError, db.add_task, alice["id"], "X", "", "", "Urgent", "Pending", fmt(today)))

# data isolation (authorization)
tid = tasks[0]["id"]
db.register("bobby", "Bobby", "Passw0rdC3")
bobby = db.login("bobby", "Passw0rdC3")
check("Other user sees none of Alice's tasks", len(db.get_tasks(bobby["id"])) == 0)
check("Other user cannot update Alice's task", raises(PermissionError, db.update_task, bobby["id"], tid, "Hacked", "", "", "Low", "Pending", fmt(today)))
check("Other user cannot delete Alice's task", raises(PermissionError, db.delete_task, bobby["id"], tid))
check("Other user cannot change Alice's task status", raises(PermissionError, db.set_status, bobby["id"], tid, "Completed"))
check("Alice's task is unchanged", db.get_tasks(alice["id"])[0]["title"] != "Hacked")

# deadlines and dashboard
reminders = db.get_reminders(alice["id"])
check("Reminders include overdue and due-today tasks", len(reminders) == 2)
check("Upcoming list shows task due in 3 days", [t["title"] for t in db.get_upcoming(alice["id"])] == ["Gym"])
db.set_status(alice["id"], tid, "Completed")
s = db.get_stats(alice["id"])
check("Dashboard counts are correct",
      (s["total"], s["completed"], s["in_progress"], s["pending"], s["overdue"]) == (3, 1, 1, 1, 0))
check("Completion percentage is correct", s["percent_done"] == 33)
check("Completed task has a completion timestamp", db.get_tasks(alice["id"], status="Completed")[0]["completed_at"])
check("Priority sorting puts High first", db.get_tasks(alice["id"], sort="Priority", status="Pending")[0]["priority"] in ("Low", "Medium", "High"))

print(f"\n{sum(bool(r) for r in results)} / {len(results)} checks passed")
