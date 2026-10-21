"""
Library Management System  -  Auspify Internship Task 2
Run:  python main.py
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from database import LibraryDB, FINE_PER_DAY, LOAN_DAYS


def make_table(parent, columns, widths=None, height=12):
    """Create a Treeview with a vertical scrollbar. columns = [(key, heading), ...]"""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns],
                        show="headings", selectmode="browse", height=height)
    for i, (key, text) in enumerate(columns):
        tree.heading(key, text=text)
        tree.column(key, width=(widths[i] if widths else 110), anchor="w")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return frame, tree


class LibraryApp:
    def __init__(self, root):
        self.root = root
        self.db = LibraryDB()
        root.title("Library Management System")
        root.geometry("1050x620")
        root.minsize(950, 560)

        tk.Label(root, text="Library Management System", font=("Segoe UI", 18, "bold"),
                 bg="#2d4a3e", fg="white", pady=10).pack(fill="x")

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.build_books_tab()
        self.build_members_tab()
        self.build_issue_tab()
        self.build_reports_tab()

        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()

    def refresh_all(self):
        self.load_books()
        self.load_members()
        self.load_issue_tab()

    # ================================================================
    #                            BOOKS TAB
    # ================================================================
    def build_books_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Books  ")

        self.book_id = None
        self.book_vars = {k: tk.StringVar() for k in ("title", "author", "isbn", "category", "copies")}
        self.book_search = tk.StringVar()

        form = ttk.LabelFrame(tab, text="Book Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        for i, (label, key) in enumerate([("Title *", "title"), ("Author *", "author"),
                                          ("ISBN *", "isbn"), ("Category", "category"),
                                          ("Copies *", "copies")]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=6)
            ttk.Entry(form, textvariable=self.book_vars[key], width=26).grid(row=i, column=1, padx=(8, 0))
        b = ttk.Frame(form)
        b.grid(row=5, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(b, text="Add", width=10, command=self.add_book).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(b, text="Update", width=10, command=self.update_book).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(b, text="Delete", width=10, command=self.delete_book).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(b, text="Clear", width=10, command=self.clear_book).grid(row=1, column=1, padx=3, pady=3)

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Search (title / author / ISBN / category):").pack(side="left")
        e = ttk.Entry(bar, textvariable=self.book_search, width=28)
        e.pack(side="left", padx=6)
        e.bind("<KeyRelease>", lambda ev: self.load_books())

        frame, self.book_tree = make_table(
            right,
            [("id", "ID"), ("title", "Title"), ("author", "Author"), ("isbn", "ISBN"),
             ("category", "Category"), ("total", "Total"), ("avail", "Available")],
            [40, 200, 140, 110, 100, 50, 70])
        frame.pack(fill="both", expand=True)
        self.book_tree.bind("<<TreeviewSelect>>", self.on_book_select)

    def book_form(self):
        d = {k: v.get().strip() for k, v in self.book_vars.items()}
        if not d["title"] or not d["author"] or not d["isbn"]:
            raise ValueError("Title, Author and ISBN are required.")
        if not d["copies"].isdigit() or int(d["copies"]) < 1:
            raise ValueError("Copies must be a whole number of at least 1.")
        d["copies"] = int(d["copies"])
        return d

    def add_book(self):
        try:
            d = self.book_form()
            self.db.add_book(d["title"], d["author"], d["isbn"], d["category"], d["copies"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_book(); self.refresh_all()

    def update_book(self):
        if self.book_id is None:
            return messagebox.showwarning("Select Book", "Select a book from the table first.")
        try:
            d = self.book_form()
            self.db.update_book(self.book_id, d["title"], d["author"], d["isbn"], d["category"], d["copies"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_book(); self.refresh_all()

    def delete_book(self):
        if self.book_id is None:
            return messagebox.showwarning("Select Book", "Select a book from the table first.")
        if not messagebox.askyesno("Confirm", "Delete this book and its history?"):
            return
        try:
            self.db.delete_book(self.book_id)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_book(); self.refresh_all()

    def clear_book(self):
        for v in self.book_vars.values():
            v.set("")
        self.book_id = None

    def load_books(self):
        self.book_tree.delete(*self.book_tree.get_children())
        for b in self.db.get_books(self.book_search.get().strip()):
            self.book_tree.insert("", "end", values=(b["id"], b["title"], b["author"], b["isbn"],
                                                     b["category"] or "", b["total_copies"],
                                                     b["available_copies"]))

    def on_book_select(self, _):
        sel = self.book_tree.selection()
        if not sel:
            return
        v = self.book_tree.item(sel[0], "values")
        self.book_id = int(v[0])
        for key, val in zip(("title", "author", "isbn", "category", "copies"),
                            (v[1], v[2], v[3], v[4], v[5])):
            self.book_vars[key].set(val)

    # ================================================================
    #                           MEMBERS TAB
    # ================================================================
    def build_members_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Members  ")

        self.member_id = None
        self.member_vars = {k: tk.StringVar() for k in ("name", "phone", "email")}
        self.member_search = tk.StringVar()

        form = ttk.LabelFrame(tab, text="Member Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        for i, (label, key) in enumerate([("Name *", "name"), ("Phone", "phone"), ("Email", "email")]):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=6)
            ttk.Entry(form, textvariable=self.member_vars[key], width=26).grid(row=i, column=1, padx=(8, 0))
        b = ttk.Frame(form)
        b.grid(row=3, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(b, text="Add", width=10, command=self.add_member).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(b, text="Update", width=10, command=self.update_member).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(b, text="Delete", width=10, command=self.delete_member).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(b, text="Clear", width=10, command=self.clear_member).grid(row=1, column=1, padx=3, pady=3)

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Search:").pack(side="left")
        e = ttk.Entry(bar, textvariable=self.member_search, width=28)
        e.pack(side="left", padx=6)
        e.bind("<KeyRelease>", lambda ev: self.load_members())

        frame, self.member_tree = make_table(
            right, [("id", "ID"), ("name", "Name"), ("phone", "Phone"), ("email", "Email")],
            [50, 200, 120, 220])
        frame.pack(fill="both", expand=True)
        self.member_tree.bind("<<TreeviewSelect>>", self.on_member_select)

    def member_form(self):
        d = {k: v.get().strip() for k, v in self.member_vars.items()}
        if not d["name"]:
            raise ValueError("Member name is required.")
        if d["phone"] and not re.match(r"^\d{10}$", d["phone"]):
            raise ValueError("Phone number must be exactly 10 digits.")
        if d["email"] and not re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", d["email"]):
            raise ValueError("Please enter a valid email address.")
        return d

    def add_member(self):
        try:
            d = self.member_form()
            self.db.add_member(d["name"], d["phone"], d["email"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_member(); self.refresh_all()

    def update_member(self):
        if self.member_id is None:
            return messagebox.showwarning("Select Member", "Select a member from the table first.")
        try:
            d = self.member_form()
            self.db.update_member(self.member_id, d["name"], d["phone"], d["email"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_member(); self.refresh_all()

    def delete_member(self):
        if self.member_id is None:
            return messagebox.showwarning("Select Member", "Select a member from the table first.")
        if not messagebox.askyesno("Confirm", "Delete this member and their history?"):
            return
        try:
            self.db.delete_member(self.member_id)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_member(); self.refresh_all()

    def clear_member(self):
        for v in self.member_vars.values():
            v.set("")
        self.member_id = None

    def load_members(self):
        self.member_tree.delete(*self.member_tree.get_children())
        for m in self.db.get_members(self.member_search.get().strip()):
            self.member_tree.insert("", "end", values=(m["id"], m["name"], m["phone"] or "", m["email"] or ""))

    def on_member_select(self, _):
        sel = self.member_tree.selection()
        if not sel:
            return
        v = self.member_tree.item(sel[0], "values")
        self.member_id = int(v[0])
        for key, val in zip(("name", "phone", "email"), v[1:]):
            self.member_vars[key].set(val)

    # ================================================================
    #                        ISSUE / RETURN TAB
    # ================================================================
    def build_issue_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Issue / Return  ")

        top = ttk.LabelFrame(tab, text=f"Issue a Book  (loan period {LOAN_DAYS} days, fine Rs.{FINE_PER_DAY}/day)", padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Book:").grid(row=0, column=0, sticky="w")
        self.issue_book_cb = ttk.Combobox(top, width=45, state="readonly")
        self.issue_book_cb.grid(row=0, column=1, padx=8, pady=4)
        ttk.Label(top, text="Member:").grid(row=0, column=2, sticky="w", padx=(15, 0))
        self.issue_member_cb = ttk.Combobox(top, width=30, state="readonly")
        self.issue_member_cb.grid(row=0, column=3, padx=8)
        ttk.Button(top, text="Issue Book", command=self.issue_book).grid(row=0, column=4, padx=10)

        ttk.Label(tab, text="Currently Issued Books (select a row and click Return)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 5))
        frame, self.issue_tree = make_table(
            tab,
            [("id", "Txn ID"), ("title", "Book"), ("member", "Member"),
             ("issue", "Issued On"), ("due", "Due Date"), ("status", "Status")],
            [60, 260, 180, 100, 100, 100], height=11)
        frame.pack(fill="both", expand=True)
        ttk.Button(tab, text="Return Selected Book", command=self.return_book).pack(pady=8, anchor="e")

    def load_issue_tab(self):
        self._book_map = {f"{b['id']} - {b['title']} ({b['available_copies']} left)": b["id"]
                          for b in self.db.get_books(only_available=True)}
        self._member_map = {f"{m['id']} - {m['name']}": m["id"] for m in self.db.get_members()}
        self.issue_book_cb["values"] = list(self._book_map)
        self.issue_member_cb["values"] = list(self._member_map)
        self.issue_book_cb.set("")
        self.issue_member_cb.set("")

        self.issue_tree.delete(*self.issue_tree.get_children())
        today = date.today().strftime("%Y-%m-%d")
        for t in self.db.get_active_issues():
            status = "OVERDUE" if t["due_date"] < today else "On time"
            self.issue_tree.insert("", "end", values=(t["id"], t["title"], t["member"],
                                                      t["issue_date"], t["due_date"], status))

    def issue_book(self):
        b, m = self.issue_book_cb.get(), self.issue_member_cb.get()
        if not b or not m:
            return messagebox.showwarning("Missing", "Select both a book and a member.")
        try:
            due = self.db.issue_book(self._book_map[b], self._member_map[m])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        messagebox.showinfo("Issued", f"Book issued successfully.\nDue date: {due}")
        self.refresh_all()

    def return_book(self):
        sel = self.issue_tree.selection()
        if not sel:
            return messagebox.showwarning("Select", "Select an issued book to return.")
        txn_id = int(self.issue_tree.item(sel[0], "values")[0])
        try:
            fine = self.db.return_book(txn_id)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        msg = "Book returned successfully."
        if fine:
            msg += f"\nLate fine to collect: Rs.{fine}"
        messagebox.showinfo("Returned", msg)
        self.refresh_all()

    # ================================================================
    #                           REPORTS TAB
    # ================================================================
    def build_reports_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Reports  ")

        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        ttk.Button(bar, text="Summary", command=self.report_summary).pack(side="left", padx=3)
        ttk.Button(bar, text="Currently Issued", command=lambda: self.report_table(self.db.get_active_issues())).pack(side="left", padx=3)
        ttk.Button(bar, text="Overdue Books", command=lambda: self.report_table(self.db.get_overdue())).pack(side="left", padx=3)
        ttk.Button(bar, text="Full History", command=lambda: self.report_table(self.db.get_history())).pack(side="left", padx=3)

        self.report_title = tk.StringVar(value="Choose a report above")
        ttk.Label(tab, textvariable=self.report_title, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=10)

        self.report_area = ttk.Frame(tab)
        self.report_area.pack(fill="both", expand=True)

    def _clear_report(self):
        for w in self.report_area.winfo_children():
            w.destroy()

    def report_summary(self):
        self._clear_report()
        self.report_title.set("Library Summary")
        frame, tree = make_table(self.report_area, [("k", "Metric"), ("v", "Value")], [300, 150], height=10)
        frame.pack(fill="both", expand=True)
        for k, v in self.db.get_summary().items():
            tree.insert("", "end", values=(k, f"Rs.{v}" if "fines" in k else v))

    def report_table(self, rows):
        self._clear_report()
        self.report_title.set(f"Report ({len(rows)} records)")
        frame, tree = make_table(
            self.report_area,
            [("id", "Txn ID"), ("title", "Book"), ("member", "Member"), ("issue", "Issued"),
             ("due", "Due"), ("ret", "Returned"), ("fine", "Fine (Rs.)")],
            [60, 240, 160, 100, 100, 100, 80], height=14)
        frame.pack(fill="both", expand=True)
        for r in rows:
            tree.insert("", "end", values=(r["id"], r["title"], r["member"], r["issue_date"],
                                           r["due_date"], r["return_date"] or "-", r["fine"] or 0))


if __name__ == "__main__":
    root = tk.Tk()
    LibraryApp(root)
    root.mainloop()
