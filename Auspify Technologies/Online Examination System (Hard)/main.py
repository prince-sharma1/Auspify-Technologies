"""
Online Examination System  -  Auspify Internship Task 5
Run:  python main.py
Default admin login:  admin / Admin@123   (change it after first login!)
"""
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from auth import AuthError
from database import ExamDB

BLUE = "#1f3a5f"


def make_table(parent, columns, widths, height=12):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings",
                        selectmode="browse", height=height)
    for (key, text), w in zip(columns, widths):
        tree.heading(key, text=text)
        tree.column(key, width=w, anchor="w")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return frame, tree


def selected_id(tree):
    sel = tree.selection()
    return int(tree.item(sel[0], "values")[0]) if sel else None


# =====================================================================
#                              MAIN APP
# =====================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.db = ExamDB()
        self.user = None
        root.title("Online Examination System")
        root.geometry("1100x660")
        root.minsize(1000, 600)
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def header(self, subtitle=""):
        bar = tk.Frame(self.container, bg=BLUE)
        bar.pack(fill="x")
        tk.Label(bar, text="Online Examination System", font=("Segoe UI", 18, "bold"),
                 bg=BLUE, fg="white", pady=10, padx=12).pack(side="left")
        if self.user:
            ttk.Button(bar, text="Logout", command=self.logout).pack(side="right", padx=12)
            tk.Label(bar, text=f"{self.user['full_name']}  ({self.user['role']})", bg=BLUE,
                     fg="white", font=("Segoe UI", 10)).pack(side="right")

    # ---------------------------------------------------------- login
    def show_login(self):
        self.clear()
        self.user = None
        self.header()
        outer = ttk.Frame(self.container)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        nb = ttk.Notebook(outer)
        nb.pack()

        # --- Login tab
        lf = ttk.Frame(nb, padding=25)
        nb.add(lf, text="  Login  ")
        self.l_user, self.l_pass = tk.StringVar(), tk.StringVar()
        ttk.Label(lf, text="Username").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(lf, textvariable=self.l_user, width=28).grid(row=0, column=1, padx=8)
        ttk.Label(lf, text="Password").grid(row=1, column=0, sticky="w", pady=6)
        pw = ttk.Entry(lf, textvariable=self.l_pass, width=28, show="*")
        pw.grid(row=1, column=1, padx=8)
        pw.bind("<Return>", lambda e: self.do_login())
        ttk.Button(lf, text="Login", width=14, command=self.do_login).grid(row=2, column=0, columnspan=2, pady=14)
        ttk.Label(lf, text="First time? Admin: admin / Admin@123", foreground="#777").grid(
            row=3, column=0, columnspan=2)

        # --- Register tab
        rf = ttk.Frame(nb, padding=25)
        nb.add(rf, text="  Student Register  ")
        self.r_vars = {k: tk.StringVar() for k in ("username", "full_name", "password", "confirm")}
        for i, (label, key, secret) in enumerate([("Username", "username", False), ("Full Name", "full_name", False),
                                                  ("Password", "password", True), ("Confirm Password", "confirm", True)]):
            ttk.Label(rf, text=label).grid(row=i, column=0, sticky="w", pady=6)
            ttk.Entry(rf, textvariable=self.r_vars[key], width=28, show="*" if secret else "").grid(row=i, column=1, padx=8)
        ttk.Label(rf, text="Password: 8+ characters with a letter and a number", foreground="#777").grid(
            row=4, column=0, columnspan=2)
        ttk.Button(rf, text="Create Account", width=16, command=self.do_register).grid(row=5, column=0, columnspan=2, pady=12)

    def do_login(self):
        try:
            self.user = self.db.login(self.l_user.get(), self.l_pass.get())
        except AuthError as e:
            return messagebox.showerror("Login Failed", str(e))
        self.l_pass.set("")
        if self.user["role"] == "admin":
            self.show_admin()
        else:
            self.show_student()

    def do_register(self):
        v = {k: x.get() for k, x in self.r_vars.items()}
        if v["password"] != v["confirm"]:
            return messagebox.showerror("Error", "Passwords do not match.")
        try:
            self.db.register_student(v["username"], v["full_name"], v["password"])
        except AuthError as e:
            return messagebox.showerror("Error", str(e))
        messagebox.showinfo("Success", "Account created. You can now log in.")
        for x in self.r_vars.values():
            x.set("")

    def logout(self):
        self.show_login()

    def show_admin(self):
        self.clear(); self.header()
        AdminView(self.container, self).pack(fill="both", expand=True, padx=8, pady=8)

    def show_student(self):
        self.clear(); self.header()
        StudentView(self.container, self).pack(fill="both", expand=True, padx=8, pady=8)


# =====================================================================
#                       SCORE REPORT WINDOW
# =====================================================================
def show_report(parent, app, attempt_id):
    try:
        att, rows = app.db.get_attempt_detail(attempt_id, app.user)
    except (ValueError, PermissionError) as e:
        return messagebox.showerror("Report", str(e))

    win = tk.Toplevel(parent)
    win.title("Score Report")
    win.geometry("900x520")
    status = "PASSED" if att["passed"] else "FAILED"
    color = "#1b7a1b" if att["passed"] else "#b02020"
    ttk.Label(win, text=f"{att['title']}  -  {att['full_name']}", font=("Segoe UI", 13, "bold")).pack(pady=(12, 2))
    tk.Label(win, text=f"Score: {att['score']} / {att['total']}    Percentage: {att['percent']}%    "
                       f"Pass mark: {att['pass_percent']}%    Result: {status}",
             fg=color, font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))

    cols = [("no", "#"), ("q", "Question"), ("your", "Your Answer"), ("right", "Correct Answer"),
            ("res", "Result"), ("marks", "Marks")]
    frame, tree = make_table(win, cols, [35, 380, 140, 140, 80, 60], height=16)
    frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    tree.tag_configure("ok", background="#d9f2d9")
    tree.tag_configure("bad", background="#f8d7da")
    tree.tag_configure("skip", background="#eeeeee")
    for i, r in enumerate(rows, 1):
        opts = {"A": r["opt_a"], "B": r["opt_b"], "C": r["opt_c"], "D": r["opt_d"]}
        sel = r["selected"]
        if sel is None:
            res, tag, got = "Skipped", "skip", 0
        elif sel == r["correct"]:
            res, tag, got = "Correct", "ok", r["marks"]
        else:
            res, tag, got = "Wrong", "bad", 0
        tree.insert("", "end", tags=(tag,), values=(
            i, r["text"], f"{sel}. {opts[sel]}" if sel else "-", f"{r['correct']}. {opts[r['correct']]}",
            res, f"{got}/{r['marks']}"))


# =====================================================================
#                           ADMIN VIEW
# =====================================================================
class AdminView(ttk.Notebook):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db = app, app.db
        self.build_exams_tab()
        self.build_questions_tab()
        self.build_results_tab()
        self.bind("<<NotebookTabChanged>>", lambda e: self.refresh())
        self.refresh()

    def refresh(self):
        self.load_exams()
        self.load_exam_choices()
        self.load_questions()
        self.load_results()

    # ---------------------------------------------------- exams tab
    def build_exams_tab(self):
        tab = ttk.Frame(self, padding=10)
        self.add(tab, text="  Manage Exams  ")
        self.exam_id = None
        self.ev = {k: tk.StringVar() for k in ("title", "subject", "duration", "pass")}
        self.ev["duration"].set("30"); self.ev["pass"].set("40")

        form = ttk.LabelFrame(tab, text="Exam Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        for i, (label, key) in enumerate([("Title *", "title"), ("Subject", "subject"),
                                          ("Duration (minutes) *", "duration"), ("Pass Percentage *", "pass")]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=6)
            ttk.Entry(form, textvariable=self.ev[key], width=24).grid(row=i, column=1, padx=(8, 0))
        b = ttk.Frame(form)
        b.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        for i, (t, c) in enumerate([("Add", self.add_exam), ("Update", self.update_exam),
                                    ("Delete", self.delete_exam), ("Show/Hide", self.toggle_exam),
                                    ("Clear", self.clear_exam), ("Load Sample Exam", self.load_sample)]):
            ttk.Button(b, text=t, width=14 if t == "Load Sample Exam" else 10, command=c).grid(
                row=i // 2, column=i % 2, padx=3, pady=3)

        cols = [("id", "ID"), ("title", "Title"), ("subject", "Subject"), ("dur", "Minutes"),
                ("pass", "Pass %"), ("qs", "Questions"), ("marks", "Marks"), ("status", "Status")]
        frame, self.exam_tree = make_table(tab, cols, [40, 200, 110, 65, 60, 75, 60, 70], height=16)
        frame.pack(side="left", fill="both", expand=True)
        self.exam_tree.tag_configure("hidden", foreground="#999")
        self.exam_tree.bind("<<TreeviewSelect>>", self.on_exam_select)

    def exam_form(self):
        try:
            return (self.ev["title"].get(), self.ev["subject"].get(),
                    int(self.ev["duration"].get()), int(self.ev["pass"].get()))
        except ValueError:
            raise ValueError("Duration and pass percentage must be whole numbers.")

    def add_exam(self):
        try:
            self.db.add_exam(*self.exam_form())
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_exam(); self.refresh()

    def update_exam(self):
        if self.exam_id is None:
            return messagebox.showwarning("Select", "Select an exam first.")
        try:
            self.db.update_exam(self.exam_id, *self.exam_form())
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_exam(); self.refresh()

    def delete_exam(self):
        if self.exam_id is None:
            return messagebox.showwarning("Select", "Select an exam first.")
        if messagebox.askyesno("Confirm", "Delete this exam with all its questions and results?"):
            self.db.delete_exam(self.exam_id)
            self.clear_exam(); self.refresh()

    def toggle_exam(self):
        if self.exam_id is None:
            return messagebox.showwarning("Select", "Select an exam first.")
        self.db.toggle_exam(self.exam_id)
        self.refresh()

    def load_sample(self):
        self.db.load_sample_exam()
        self.refresh()
        messagebox.showinfo("Sample Exam", "'Python Basics Quiz' with 5 questions was added.")

    def clear_exam(self):
        for k in self.ev:
            self.ev[k].set("")
        self.ev["duration"].set("30"); self.ev["pass"].set("40")
        self.exam_id = None

    def load_exams(self):
        self.exam_tree.delete(*self.exam_tree.get_children())
        for e in self.db.get_exams():
            self.exam_tree.insert("", "end", tags=() if e["active"] else ("hidden",), values=(
                e["id"], e["title"], e["subject"] or "", e["duration_min"], e["pass_percent"],
                e["question_count"], e["total_marks"], "Active" if e["active"] else "Hidden"))

    def on_exam_select(self, _):
        sel = self.exam_tree.selection()
        if sel:
            v = self.exam_tree.item(sel[0], "values")
            self.exam_id = int(v[0])
            self.ev["title"].set(v[1]); self.ev["subject"].set(v[2])
            self.ev["duration"].set(v[3]); self.ev["pass"].set(v[4])

    # ---------------------------------------------------- questions tab
    def build_questions_tab(self):
        tab = ttk.Frame(self, padding=10)
        self.add(tab, text="  Questions  ")
        self.q_id = None
        self.q_exam_map = {}
        self.qv = {k: tk.StringVar() for k in ("a", "b", "c", "d", "correct", "marks")}
        self.qv["marks"].set("1")

        form = ttk.LabelFrame(tab, text="Question", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(form, text="Exam *").grid(row=0, column=0, sticky="w", pady=4)
        self.q_exam_cb = ttk.Combobox(form, width=30, state="readonly")
        self.q_exam_cb.grid(row=0, column=1, padx=(8, 0))
        self.q_exam_cb.bind("<<ComboboxSelected>>", lambda e: self.load_questions())
        ttk.Label(form, text="Question *").grid(row=1, column=0, sticky="nw", pady=4)
        self.q_text = tk.Text(form, width=31, height=4, wrap="word")
        self.q_text.grid(row=1, column=1, padx=(8, 0), pady=4)
        for i, k in enumerate("abcd"):
            ttk.Label(form, text=f"Option {k.upper()} *").grid(row=2 + i, column=0, sticky="w", pady=3)
            ttk.Entry(form, textvariable=self.qv[k], width=33).grid(row=2 + i, column=1, padx=(8, 0))
        ttk.Label(form, text="Correct *").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=self.qv["correct"], values=["A", "B", "C", "D"], width=6,
                     state="readonly").grid(row=6, column=1, sticky="w", padx=8)
        ttk.Label(form, text="Marks").grid(row=7, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.qv["marks"], width=8).grid(row=7, column=1, sticky="w", padx=8)
        b = ttk.Frame(form)
        b.grid(row=8, column=0, columnspan=2, pady=(10, 0))
        for i, (t, c) in enumerate([("Add", self.add_q), ("Update", self.update_q),
                                    ("Delete", self.delete_q), ("Clear", self.clear_q)]):
            ttk.Button(b, text=t, width=10, command=c).grid(row=i // 2, column=i % 2, padx=3, pady=3)

        cols = [("id", "ID"), ("q", "Question"), ("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"),
                ("ans", "Ans"), ("m", "Marks")]
        frame, self.q_tree = make_table(tab, cols, [40, 220, 90, 90, 90, 90, 40, 50], height=17)
        frame.pack(side="left", fill="both", expand=True)
        self.q_tree.bind("<<TreeviewSelect>>", self.on_q_select)

    def load_exam_choices(self):
        exams = self.db.get_exams()
        self.q_exam_map = {f"{e['id']} - {e['title']}": e["id"] for e in exams}
        names = list(self.q_exam_map)
        self.q_exam_cb["values"] = names
        if self.q_exam_cb.get() not in names:
            self.q_exam_cb.set(names[0] if names else "")
        self.r_exam_cb["values"] = ["All Exams"] + names
        if self.r_exam_cb.get() not in ["All Exams"] + names:
            self.r_exam_cb.set("All Exams")

    def current_exam_id(self):
        return self.q_exam_map.get(self.q_exam_cb.get())

    def q_form(self):
        exam_id = self.current_exam_id()
        if exam_id is None:
            raise ValueError("Create and select an exam first.")
        try:
            marks = int(self.qv["marks"].get())
        except ValueError:
            raise ValueError("Marks must be a whole number.")
        return (self.q_text.get("1.0", "end").strip(), self.qv["a"].get(), self.qv["b"].get(),
                self.qv["c"].get(), self.qv["d"].get(), self.qv["correct"].get(), marks), exam_id

    def add_q(self):
        try:
            data, exam_id = self.q_form()
            self.db.add_question(exam_id, *data)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_q(); self.refresh()

    def update_q(self):
        if self.q_id is None:
            return messagebox.showwarning("Select", "Select a question first.")
        try:
            data, _ = self.q_form()
            self.db.update_question(self.q_id, *data)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_q(); self.refresh()

    def delete_q(self):
        if self.q_id is None:
            return messagebox.showwarning("Select", "Select a question first.")
        if messagebox.askyesno("Confirm", "Delete this question?"):
            self.db.delete_question(self.q_id)
            self.clear_q(); self.refresh()

    def clear_q(self):
        self.q_text.delete("1.0", "end")
        for k, v in self.qv.items():
            v.set("1" if k == "marks" else "")
        self.q_id = None

    def load_questions(self):
        self.q_tree.delete(*self.q_tree.get_children())
        exam_id = self.current_exam_id()
        if exam_id is None:
            return
        for q in self.db.get_questions(exam_id, include_answers=True):
            self.q_tree.insert("", "end", values=(q["id"], q["text"], q["opt_a"], q["opt_b"],
                                                  q["opt_c"], q["opt_d"], q["correct"], q["marks"]))

    def on_q_select(self, _):
        sel = self.q_tree.selection()
        if not sel:
            return
        v = self.q_tree.item(sel[0], "values")
        self.q_id = int(v[0])
        self.q_text.delete("1.0", "end"); self.q_text.insert("1.0", v[1])
        for k, val in zip(("a", "b", "c", "d", "correct", "marks"), v[2:]):
            self.qv[k].set(val)

    # ---------------------------------------------------- results tab
    def build_results_tab(self):
        tab = ttk.Frame(self, padding=10)
        self.add(tab, text="  Results  ")
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        ttk.Label(bar, text="Exam:").pack(side="left")
        self.r_exam_cb = ttk.Combobox(bar, width=34, state="readonly")
        self.r_exam_cb.set("All Exams")
        self.r_exam_cb.pack(side="left", padx=6)
        self.r_exam_cb.bind("<<ComboboxSelected>>", lambda e: self.load_results())
        ttk.Button(bar, text="View Report", command=self.view_report).pack(side="left", padx=4)
        ttk.Button(bar, text="Export CSV", command=self.export_results).pack(side="left", padx=4)

        self.stats_var = tk.StringVar()
        tk.Label(tab, textvariable=self.stats_var, anchor="w", bg="#eef3fa", padx=10, pady=8,
                 font=("Segoe UI", 10, "bold")).pack(fill="x", pady=10)

        cols = [("id", "Attempt"), ("student", "Student"), ("user", "Username"), ("exam", "Exam"),
                ("score", "Score"), ("pct", "Percent"), ("res", "Result"), ("date", "Submitted")]
        frame, self.res_tree = make_table(tab, cols, [60, 150, 110, 200, 80, 70, 70, 140], height=16)
        frame.pack(fill="both", expand=True)
        self.res_tree.tag_configure("pass", foreground="#1b7a1b")
        self.res_tree.tag_configure("fail", foreground="#b02020")

    def result_exam_id(self):
        return self.q_exam_map.get(self.r_exam_cb.get())

    def load_results(self):
        exam_id = self.result_exam_id()
        s = self.db.get_stats(exam_id)
        rate = (s["passed"] * 100 / s["attempts"]) if s["attempts"] else 0
        self.stats_var.set(f"Attempts: {s['attempts']}    Average: {s['avg_percent']:.1f}%    "
                           f"Highest: {s['highest']}%    Lowest: {s['lowest']}%    Pass rate: {rate:.0f}%")
        self.res_tree.delete(*self.res_tree.get_children())
        for r in self.db.get_results(exam_id):
            self.res_tree.insert("", "end", tags=("pass" if r["passed"] else "fail",), values=(
                r["id"], r["full_name"], r["username"], r["title"], f"{r['score']}/{r['total']}",
                f"{r['percent']}%", "Pass" if r["passed"] else "Fail", r["submitted_at"]))

    def view_report(self):
        att = selected_id(self.res_tree)
        if att is None:
            return messagebox.showwarning("Select", "Select a result first.")
        show_report(self, self.app, att)

    def export_results(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="results.csv")
        if not path:
            return
        rows = self.db.get_results(self.result_exam_id())
        self.db.export_csv(path, ["Student", "Username", "Exam", "Score", "Total", "Percent", "Result", "Submitted"],
                           [(r["full_name"], r["username"], r["title"], r["score"], r["total"], r["percent"],
                             "Pass" if r["passed"] else "Fail", r["submitted_at"]) for r in rows])
        messagebox.showinfo("Exported", f"{len(rows)} results exported.")


# =====================================================================
#                           STUDENT VIEW
# =====================================================================
class StudentView(ttk.Notebook):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db, self.user = app, app.db, app.user

        t1 = ttk.Frame(self, padding=10)
        self.add(t1, text="  Available Exams  ")
        cols = [("id", "ID"), ("title", "Exam"), ("subject", "Subject"), ("dur", "Minutes"),
                ("qs", "Questions"), ("marks", "Marks"), ("pass", "Pass %"), ("status", "Status")]
        frame, self.exam_tree = make_table(t1, cols, [40, 230, 120, 70, 80, 70, 70, 100], height=15)
        frame.pack(fill="both", expand=True)
        self.exam_tree.tag_configure("done", foreground="#999")
        ttk.Button(t1, text="Start Selected Exam", command=self.start_exam).pack(pady=10, anchor="e")

        t2 = ttk.Frame(self, padding=10)
        self.add(t2, text="  My Results  ")
        cols = [("id", "Attempt"), ("exam", "Exam"), ("score", "Score"), ("pct", "Percent"),
                ("res", "Result"), ("date", "Submitted")]
        frame, self.res_tree = make_table(t2, cols, [70, 250, 90, 80, 80, 150], height=15)
        frame.pack(fill="both", expand=True)
        self.res_tree.tag_configure("pass", foreground="#1b7a1b")
        self.res_tree.tag_configure("fail", foreground="#b02020")
        ttk.Button(t2, text="View Score Report", command=self.view_report).pack(pady=10, anchor="e")

        self.bind("<<NotebookTabChanged>>", lambda e: self.refresh())
        self.refresh()

    def refresh(self):
        self.exam_tree.delete(*self.exam_tree.get_children())
        for e in self.db.get_exams(only_active=True):
            att = self.db.get_attempt_for(e["id"], self.user["id"])
            status = "Attempted" if att else ("No questions" if e["question_count"] == 0 else "Available")
            self.exam_tree.insert("", "end", tags=("done",) if status != "Available" else (), values=(
                e["id"], e["title"], e["subject"] or "", e["duration_min"], e["question_count"],
                e["total_marks"], e["pass_percent"], status))
        self.res_tree.delete(*self.res_tree.get_children())
        for r in self.db.get_results(user_id=self.user["id"]):
            self.res_tree.insert("", "end", tags=("pass" if r["passed"] else "fail",), values=(
                r["id"], r["title"], f"{r['score']}/{r['total']}", f"{r['percent']}%",
                "Pass" if r["passed"] else "Fail", r["submitted_at"]))

    def view_report(self):
        att = selected_id(self.res_tree)
        if att is None:
            return messagebox.showwarning("Select", "Select a result first.")
        show_report(self, self.app, att)

    def start_exam(self):
        exam_id = selected_id(self.exam_tree)
        if exam_id is None:
            return messagebox.showwarning("Select", "Select an exam first.")
        exam = self.db.get_exam(exam_id)
        if not messagebox.askyesno(
                "Start Exam",
                f"{exam['title']}\nDuration: {exam['duration_min']} minutes\n\n"
                "Rules:\n- You can attempt this exam only ONCE.\n- The exam auto-submits when time ends.\n"
                "- Closing the exam window submits your current answers.\n\nStart now?"):
            return
        try:
            attempt_id = self.db.start_attempt(exam_id, self.user["id"])
        except ValueError as e:
            return messagebox.showerror("Cannot Start", str(e))
        ExamWindow(self, self.app, exam, attempt_id)


# =====================================================================
#                           EXAM WINDOW
# =====================================================================
class ExamWindow(tk.Toplevel):
    def __init__(self, view, app, exam, attempt_id):
        super().__init__(view)
        self.view, self.app, self.db = view, app, app.db
        self.exam, self.attempt_id = exam, attempt_id
        self.questions = self.db.get_questions(exam["id"])       # NO correct answers here
        self.answers, self.index, self.finished = {}, 0, False
        self.deadline = time.time() + exam["duration_min"] * 60
        self.choice = tk.StringVar()

        self.title(exam["title"])
        self.geometry("820x560")
        self.transient(view); self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        top = tk.Frame(self, bg=BLUE)
        top.pack(fill="x")
        tk.Label(top, text=exam["title"], bg=BLUE, fg="white", font=("Segoe UI", 14, "bold"),
                 padx=12, pady=8).pack(side="left")
        self.timer_label = tk.Label(top, text="", bg=BLUE, fg="white", font=("Consolas", 16, "bold"), padx=12)
        self.timer_label.pack(side="right")

        self.palette = ttk.Frame(self, padding=8)
        self.palette.pack(fill="x")
        self.pal_buttons = []
        for i in range(len(self.questions)):
            btn = tk.Button(self.palette, text=str(i + 1), width=3, command=lambda n=i: self.goto(n))
            btn.grid(row=i // 15, column=i % 15, padx=2, pady=2)
            self.pal_buttons.append(btn)

        body = ttk.Frame(self, padding=(20, 10))
        body.pack(fill="both", expand=True)
        self.q_label = ttk.Label(body, wraplength=740, font=("Segoe UI", 13, "bold"), justify="left")
        self.q_label.pack(anchor="w", pady=(5, 15))
        self.radios = {}
        for letter in "ABCD":
            rb = ttk.Radiobutton(body, variable=self.choice, value=letter, command=self.save_choice)
            rb.pack(anchor="w", pady=6)
            self.radios[letter] = rb

        nav = ttk.Frame(self, padding=10)
        nav.pack(fill="x")
        ttk.Button(nav, text="< Previous", command=lambda: self.goto(self.index - 1)).pack(side="left")
        ttk.Button(nav, text="Next >", command=lambda: self.goto(self.index + 1)).pack(side="left", padx=6)
        ttk.Button(nav, text="Clear Answer", command=self.clear_choice).pack(side="left", padx=6)
        ttk.Button(nav, text="Submit Exam", command=self.confirm_submit).pack(side="right")

        self.show_question()
        self.tick()

    # ------------------------------------------------ navigation
    def goto(self, n):
        if 0 <= n < len(self.questions):
            self.index = n
            self.show_question()

    def show_question(self):
        q = self.questions[self.index]
        self.q_label.config(text=f"Q{self.index + 1} of {len(self.questions)}  ({q['marks']} marks)\n\n{q['text']}")
        for letter, key in zip("ABCD", ("opt_a", "opt_b", "opt_c", "opt_d")):
            self.radios[letter].config(text=f"{letter}.  {q[key]}")
        self.choice.set(self.answers.get(q["id"], ""))
        self.refresh_palette()

    def save_choice(self):
        if self.choice.get():
            self.answers[self.questions[self.index]["id"]] = self.choice.get()
        self.refresh_palette()

    def clear_choice(self):
        self.answers.pop(self.questions[self.index]["id"], None)
        self.choice.set("")
        self.refresh_palette()

    def refresh_palette(self):
        for i, btn in enumerate(self.pal_buttons):
            answered = self.questions[i]["id"] in self.answers
            btn.config(bg="#8fd18f" if answered else "#f0f0f0",
                       relief="sunken" if i == self.index else "raised")

    # ------------------------------------------------ timer / submit
    def tick(self):
        if self.finished:
            return
        left = int(self.deadline - time.time())
        if left <= 0:
            self.timer_label.config(text="00:00")
            messagebox.showinfo("Time Up", "Time is over. Your exam is being submitted.", parent=self)
            return self.submit(auto=True)
        self.timer_label.config(text=f"{left // 60:02d}:{left % 60:02d}",
                                fg="#ff8080" if left <= 60 else "white")
        self.after(1000, self.tick)

    def confirm_submit(self):
        unanswered = len(self.questions) - len(self.answers)
        msg = "Submit your exam now?"
        if unanswered:
            msg = f"You have {unanswered} unanswered question(s).\n\nSubmit anyway?"
        if messagebox.askyesno("Submit Exam", msg, parent=self):
            self.submit()

    def on_close(self):
        if messagebox.askyesno("Leave Exam", "Closing will SUBMIT your current answers.\n\nContinue?", parent=self):
            self.submit()

    def submit(self, auto=False):
        if self.finished:
            return
        self.finished = True
        try:
            result = self.db.submit_attempt(self.attempt_id, self.app.user["id"], self.answers)
        except (ValueError, PermissionError) as e:
            messagebox.showerror("Error", str(e), parent=self)
            return self.destroy()
        view, app, attempt_id = self.view, self.app, self.attempt_id
        self.grab_release()
        self.destroy()
        view.refresh()
        messagebox.showinfo(
            "Exam Submitted",
            f"Score: {result['score']} / {result['total']}\nPercentage: {result['percent']}%\n"
            f"Result: {'PASSED' if result['passed'] else 'FAILED'}", parent=view)
        show_report(view, app, attempt_id)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
