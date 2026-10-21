"""
Task Management App  -  Auspify Internship Task 6
Run:  python main.py
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta

from auth import AuthError
from database import TaskDB, PRIORITIES, STATUSES

TEAL = "#1d5c63"


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


def draw_bars(canvas, data, colors, title):
    """Tiny bar chart drawn on a Canvas (no extra libraries needed)."""
    canvas.delete("all")
    w, h = int(canvas["width"]), int(canvas["height"])
    canvas.create_text(w // 2, 14, text=title, font=("Segoe UI", 10, "bold"))
    top = max(max(data.values()), 1)
    n = len(data)
    slot = (w - 40) / n
    for i, (label, value) in enumerate(data.items()):
        x0 = 30 + i * slot + slot * 0.2
        x1 = 30 + i * slot + slot * 0.8
        bar_h = (h - 70) * value / top
        y1 = h - 30
        canvas.create_rectangle(x0, y1 - bar_h, x1, y1, fill=colors[i], outline="")
        canvas.create_text((x0 + x1) / 2, y1 - bar_h - 10, text=str(value), font=("Segoe UI", 10, "bold"))
        canvas.create_text((x0 + x1) / 2, y1 + 14, text=label, font=("Segoe UI", 9))


class App:
    def __init__(self, root):
        self.root = root
        self.db = TaskDB()
        self.user = None
        root.title("Task Management App")
        root.geometry("1150x680")
        root.minsize(1050, 620)
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def header(self):
        bar = tk.Frame(self.container, bg=TEAL)
        bar.pack(fill="x")
        tk.Label(bar, text="Task Management App", font=("Segoe UI", 18, "bold"),
                 bg=TEAL, fg="white", pady=10, padx=12).pack(side="left")
        if self.user:
            ttk.Button(bar, text="Logout", command=self.show_login).pack(side="right", padx=12)
            tk.Label(bar, text=f"Hello, {self.user['full_name']}", bg=TEAL, fg="white",
                     font=("Segoe UI", 11)).pack(side="right")

    # ------------------------------------------------------------ login
    def show_login(self):
        self.clear()
        self.user = None
        self.header()
        outer = ttk.Frame(self.container)
        outer.place(relx=0.5, rely=0.5, anchor="center")
        nb = ttk.Notebook(outer)
        nb.pack()

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

        rf = ttk.Frame(nb, padding=25)
        nb.add(rf, text="  Create Account  ")
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
        self.clear()
        self.header()
        MainView(self.container, self).pack(fill="both", expand=True, padx=8, pady=8)
        self.show_reminders()

    def do_register(self):
        v = {k: x.get() for k, x in self.r_vars.items()}
        if v["password"] != v["confirm"]:
            return messagebox.showerror("Error", "Passwords do not match.")
        try:
            self.db.register(v["username"], v["full_name"], v["password"], role="user")
        except AuthError as e:
            return messagebox.showerror("Error", str(e))
        messagebox.showinfo("Success", "Account created. You can now log in.")
        for x in self.r_vars.values():
            x.set("")

    def show_reminders(self):
        due = self.db.get_reminders(self.user["id"])
        if not due:
            return
        today = date.today().strftime("%Y-%m-%d")
        lines = [f"{'OVERDUE' if t['due_date'] < today else 'DUE TODAY'}:  {t['title']}  ({t['due_date']})"
                 for t in due[:8]]
        more = f"\n...and {len(due) - 8} more" if len(due) > 8 else ""
        messagebox.showwarning("Deadline Reminder", "\n".join(lines) + more)


class MainView(ttk.Notebook):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app, self.db, self.uid = app, app.db, app.user["id"]
        self.task_id = None
        self.build_tasks_tab()
        self.build_dashboard_tab()
        self.bind("<<NotebookTabChanged>>", lambda e: self.refresh())
        self.refresh()

    def refresh(self):
        self.load_tasks()
        self.load_dashboard()

    # ===================================================== TASKS TAB
    def build_tasks_tab(self):
        tab = ttk.Frame(self, padding=10)
        self.add(tab, text="  My Tasks  ")

        self.tv = {k: tk.StringVar() for k in ("title", "category", "priority", "status", "due")}
        self.reset_vars()

        form = ttk.LabelFrame(tab, text="Task Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(form, text="Title *").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.tv["title"], width=28).grid(row=0, column=1, padx=(8, 0), columnspan=3)
        ttk.Label(form, text="Description").grid(row=1, column=0, sticky="nw", pady=5)
        self.desc = tk.Text(form, width=28, height=4, wrap="word")
        self.desc.grid(row=1, column=1, padx=(8, 0), columnspan=3)
        ttk.Label(form, text="Category").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.tv["category"], width=28).grid(row=2, column=1, padx=(8, 0), columnspan=3)
        ttk.Label(form, text="Priority").grid(row=3, column=0, sticky="w", pady=5)
        ttk.Combobox(form, textvariable=self.tv["priority"], values=PRIORITIES, width=26,
                     state="readonly").grid(row=3, column=1, padx=(8, 0), columnspan=3)
        ttk.Label(form, text="Status").grid(row=4, column=0, sticky="w", pady=5)
        ttk.Combobox(form, textvariable=self.tv["status"], values=STATUSES, width=26,
                     state="readonly").grid(row=4, column=1, padx=(8, 0), columnspan=3)
        ttk.Label(form, text="Due Date *").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.tv["due"], width=28).grid(row=5, column=1, padx=(8, 0), columnspan=3)
        quick = ttk.Frame(form)
        quick.grid(row=6, column=1, columnspan=3, sticky="w", padx=(8, 0))
        for text, days in (("Today", 0), ("Tomorrow", 1), ("+7 days", 7)):
            ttk.Button(quick, text=text, width=9,
                       command=lambda d=days: self.tv["due"].set(
                           (date.today() + timedelta(days=d)).strftime("%Y-%m-%d"))).pack(side="left", padx=(0, 4))
        ttk.Label(form, text="Date format: YYYY-MM-DD", foreground="#777").grid(row=7, column=1, sticky="w", padx=8)

        b = ttk.Frame(form)
        b.grid(row=8, column=0, columnspan=4, pady=(12, 0))
        for i, (t, c) in enumerate([("Add", self.add_task), ("Update", self.update_task),
                                    ("Delete", self.delete_task), ("Clear", self.clear_form)]):
            ttk.Button(b, text=t, width=10, command=c).grid(row=i // 2, column=i % 2, padx=3, pady=3)

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, 8))
        self.f_search, self.f_status = tk.StringVar(), tk.StringVar(value="All")
        self.f_priority, self.f_sort = tk.StringVar(value="All"), tk.StringVar(value="Due date")
        ttk.Label(bar, text="Search:").pack(side="left")
        e = ttk.Entry(bar, textvariable=self.f_search, width=16)
        e.pack(side="left", padx=4)
        e.bind("<KeyRelease>", lambda ev: self.load_tasks())
        for var, values, w in ((self.f_status, ["All"] + list(STATUSES), 11),
                               (self.f_priority, ["All"] + list(PRIORITIES), 8),
                               (self.f_sort, ["Due date", "Priority", "Newest"], 9)):
            cb = ttk.Combobox(bar, textvariable=var, values=values, width=w, state="readonly")
            cb.pack(side="left", padx=3)
            cb.bind("<<ComboboxSelected>>", lambda ev: self.load_tasks())
        ttk.Button(bar, text="Export CSV", command=self.export_csv).pack(side="right")

        cols = [("id", "ID"), ("title", "Title"), ("cat", "Category"), ("pri", "Priority"),
                ("status", "Status"), ("due", "Due Date"), ("flag", "Deadline")]
        frame, self.tree = make_table(right, cols, [35, 220, 90, 70, 90, 90, 100], height=16)
        frame.pack(fill="both", expand=True)
        self.tree.tag_configure("overdue", background="#f8d7da")
        self.tree.tag_configure("today", background="#fff3cd")
        self.tree.tag_configure("done", foreground="#999")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        act = ttk.Frame(right)
        act.pack(fill="x", pady=(8, 0))
        ttk.Button(act, text="Mark In Progress", command=lambda: self.quick_status("In Progress")).pack(side="left")
        ttk.Button(act, text="Mark Completed", command=lambda: self.quick_status("Completed")).pack(side="left", padx=6)
        tk.Label(act, text="Red = overdue   Yellow = due today   Grey = completed", fg="#555").pack(side="right")

    def reset_vars(self):
        self.tv["title"].set(""); self.tv["category"].set("")
        self.tv["priority"].set("Medium"); self.tv["status"].set("Pending")
        self.tv["due"].set(date.today().strftime("%Y-%m-%d"))

    def form_data(self):
        return (self.tv["title"].get(), self.desc.get("1.0", "end").strip(), self.tv["category"].get(),
                self.tv["priority"].get(), self.tv["status"].get(), self.tv["due"].get().strip())

    def add_task(self):
        try:
            self.db.add_task(self.uid, *self.form_data())
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_form(); self.refresh()

    def update_task(self):
        if self.task_id is None:
            return messagebox.showwarning("Select", "Select a task from the table first.")
        try:
            self.db.update_task(self.uid, self.task_id, *self.form_data())
        except (ValueError, PermissionError) as e:
            return messagebox.showerror("Error", str(e))
        self.clear_form(); self.refresh()

    def delete_task(self):
        if self.task_id is None:
            return messagebox.showwarning("Select", "Select a task from the table first.")
        if not messagebox.askyesno("Confirm", "Delete this task permanently?"):
            return
        try:
            self.db.delete_task(self.uid, self.task_id)
        except PermissionError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_form(); self.refresh()

    def quick_status(self, status):
        if self.task_id is None:
            return messagebox.showwarning("Select", "Select a task from the table first.")
        try:
            self.db.set_status(self.uid, self.task_id, status)
        except PermissionError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_form(); self.refresh()

    def clear_form(self):
        self.reset_vars()
        self.desc.delete("1.0", "end")
        self.task_id = None
        self.tree.selection_remove(self.tree.selection())

    def load_tasks(self):
        self.tree.delete(*self.tree.get_children())
        today = date.today().strftime("%Y-%m-%d")
        rows = self.db.get_tasks(self.uid, self.f_search.get().strip(), self.f_status.get(),
                                 self.f_priority.get(), self.f_sort.get())
        self._tasks = {t["id"]: t for t in rows}
        for t in rows:
            if t["status"] == "Completed":
                tag, flag = "done", "Done"
            elif t["due_date"] < today:
                tag, flag = "overdue", "OVERDUE"
            elif t["due_date"] == today:
                tag, flag = "today", "Due today"
            else:
                tag, flag = "", ""
            self.tree.insert("", "end", tags=(tag,), values=(
                t["id"], t["title"], t["category"] or "", t["priority"], t["status"], t["due_date"], flag))

    def on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        t = self._tasks[int(self.tree.item(sel[0], "values")[0])]
        self.task_id = t["id"]
        self.tv["title"].set(t["title"]); self.tv["category"].set(t["category"] or "")
        self.tv["priority"].set(t["priority"]); self.tv["status"].set(t["status"])
        self.tv["due"].set(t["due_date"])
        self.desc.delete("1.0", "end"); self.desc.insert("1.0", t["description"] or "")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="my_tasks.csv")
        if not path:
            return
        rows = self.db.get_tasks(self.uid, self.f_search.get().strip(), self.f_status.get(),
                                 self.f_priority.get(), self.f_sort.get())
        self.db.export_csv(path, rows)
        messagebox.showinfo("Exported", f"{len(rows)} tasks exported.")

    # ===================================================== DASHBOARD TAB
    def build_dashboard_tab(self):
        tab = ttk.Frame(self, padding=10)
        self.add(tab, text="  Dashboard  ")

        cards = tk.Frame(tab)
        cards.pack(fill="x")
        self.card_vars = {}
        for i, (key, title, color) in enumerate([("total", "Total Tasks", "#2d6a9f"), ("completed", "Completed", "#2d8f6f"),
                                                 ("in_progress", "In Progress", "#7a4fa3"), ("pending", "Pending", "#d08a00"),
                                                 ("overdue", "Overdue", "#c0392b")]):
            card = tk.Frame(cards, bg=color, padx=14, pady=10)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            cards.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=color, fg="white", font=("Segoe UI", 10)).pack()
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, bg=color, fg="white", font=("Segoe UI", 20, "bold")).pack()
            self.card_vars[key] = var

        prog = ttk.Frame(tab)
        prog.pack(fill="x", pady=14)
        self.progress_label = tk.StringVar()
        ttk.Label(prog, textvariable=self.progress_label, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.progress = ttk.Progressbar(prog, maximum=100, length=400)
        self.progress.pack(fill="x", pady=4)

        lower = ttk.Frame(tab)
        lower.pack(fill="both", expand=True)
        charts = ttk.Frame(lower)
        charts.pack(side="left", padx=(0, 10))
        self.status_canvas = tk.Canvas(charts, width=330, height=190, bg="white", highlightthickness=1,
                                       highlightbackground="#ccc")
        self.status_canvas.pack(pady=(0, 8))
        self.priority_canvas = tk.Canvas(charts, width=330, height=190, bg="white", highlightthickness=1,
                                         highlightbackground="#ccc")
        self.priority_canvas.pack()

        up = ttk.LabelFrame(lower, text="Upcoming Deadlines (next 7 days)", padding=6)
        up.pack(side="left", fill="both", expand=True)
        frame, self.up_tree = make_table(up, [("title", "Task"), ("pri", "Priority"), ("due", "Due Date")],
                                         [200, 70, 90], height=14)
        frame.pack(fill="both", expand=True)

    def load_dashboard(self):
        s = self.db.get_stats(self.uid)
        for k in self.card_vars:
            self.card_vars[k].set(s[k])
        self.progress["value"] = s["percent_done"]
        self.progress_label.set(f"Overall completion: {s['percent_done']}%")
        draw_bars(self.status_canvas, {"Pending": s["pending"], "In Progress": s["in_progress"],
                                       "Completed": s["completed"]},
                  ["#d08a00", "#7a4fa3", "#2d8f6f"], "Tasks by Status")
        draw_bars(self.priority_canvas, {"Low": s["low"], "Medium": s["medium"], "High": s["high"]},
                  ["#5aa469", "#e0a526", "#c0392b"], "Tasks by Priority")
        self.up_tree.delete(*self.up_tree.get_children())
        for t in self.db.get_upcoming(self.uid):
            self.up_tree.insert("", "end", values=(t["title"], t["priority"], t["due_date"]))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
