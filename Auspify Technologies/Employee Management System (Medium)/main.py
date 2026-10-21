"""
Employee Management System  -  Auspify Internship Task 4
Run:  python main.py
"""
import math
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date

from database import EmployeeDB

PAGE_SIZE = 50   # performance optimization: load only one page of rows at a time


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


class EmployeeApp:
    def __init__(self, root):
        self.root = root
        self.db = EmployeeDB()
        self.page = 1
        root.title("Employee Management System")
        root.geometry("1200x680")
        root.minsize(1100, 620)

        tk.Label(root, text="Employee Management System", font=("Segoe UI", 18, "bold"),
                 bg="#243b6b", fg="white", pady=10).pack(fill="x")
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.build_employee_tab()
        self.build_department_tab()
        self.build_report_tab()

        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()

    def refresh_all(self):
        self.load_departments()
        self.load_employees()
        self.load_reports()

    # ================================================================
    #                         EMPLOYEES TAB
    # ================================================================
    def build_employee_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Employees  ")

        self.emp_id = None
        self.ev = {k: tk.StringVar() for k in
                   ("emp_code", "name", "email", "phone", "dept", "designation", "salary", "join_date", "status")}
        self.ev["join_date"].set(date.today().strftime("%Y-%m-%d"))
        self.ev["status"].set("Active")

        form = ttk.LabelFrame(tab, text="Employee Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        rows = [("Employee Code *", "emp_code"), ("Full Name *", "name"), ("Email", "email"),
                ("Phone", "phone"), ("Department", "dept"), ("Designation", "designation"),
                ("Salary (yearly) *", "salary"), ("Join Date *", "join_date"), ("Status", "status")]
        for i, (label, key) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=5)
            if key == "dept":
                self.dept_cb = ttk.Combobox(form, textvariable=self.ev[key], width=23, state="readonly")
                self.dept_cb.grid(row=i, column=1, padx=(8, 0))
            elif key == "status":
                ttk.Combobox(form, textvariable=self.ev[key], width=23, state="readonly",
                             values=["Active", "Inactive"]).grid(row=i, column=1, padx=(8, 0))
            else:
                ttk.Entry(form, textvariable=self.ev[key], width=26).grid(row=i, column=1, padx=(8, 0))
        ttk.Label(form, text="Date format: YYYY-MM-DD", foreground="#666").grid(
            row=len(rows), column=0, columnspan=2)
        b = ttk.Frame(form)
        b.grid(row=len(rows) + 1, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(b, text="Add", width=10, command=self.add_employee).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(b, text="Update", width=10, command=self.update_employee).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(b, text="Delete", width=10, command=self.delete_employee).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(b, text="Clear", width=10, command=self.clear_form).grid(row=1, column=1, padx=3, pady=3)

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)

        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar()
        self.filter_dept = tk.StringVar(value="All Departments")
        self.filter_status = tk.StringVar(value="All")
        ttk.Label(bar, text="Search:").pack(side="left")
        e = ttk.Entry(bar, textvariable=self.search_var, width=20)
        e.pack(side="left", padx=5)
        e.bind("<KeyRelease>", lambda ev: self.reset_and_load())
        self.dept_filter_cb = ttk.Combobox(bar, textvariable=self.filter_dept, width=17, state="readonly")
        self.dept_filter_cb.pack(side="left", padx=5)
        self.dept_filter_cb.bind("<<ComboboxSelected>>", lambda ev: self.reset_and_load())
        sc = ttk.Combobox(bar, textvariable=self.filter_status, width=9, state="readonly",
                          values=["All", "Active", "Inactive"])
        sc.pack(side="left", padx=5)
        sc.bind("<<ComboboxSelected>>", lambda ev: self.reset_and_load())
        ttk.Button(bar, text="Export CSV", command=self.export_csv).pack(side="right")

        cols = [("id", "ID"), ("code", "Code"), ("name", "Name"), ("email", "Email"), ("phone", "Phone"),
                ("dept", "Department"), ("desig", "Designation"), ("salary", "Salary"),
                ("join", "Joined"), ("status", "Status")]
        frame, self.etree = make_table(right, cols, [40, 80, 130, 160, 90, 100, 110, 80, 80, 65], height=17)
        frame.pack(fill="both", expand=True)
        self.etree.tag_configure("inactive", foreground="#999")
        self.etree.bind("<<TreeviewSelect>>", self.on_select)

        pager = ttk.Frame(right)
        pager.pack(fill="x", pady=(6, 0))
        ttk.Button(pager, text="< Prev", width=8, command=lambda: self.change_page(-1)).pack(side="left")
        self.page_label = tk.StringVar()
        ttk.Label(pager, textvariable=self.page_label).pack(side="left", padx=12)
        ttk.Button(pager, text="Next >", width=8, command=lambda: self.change_page(1)).pack(side="left")
        ttk.Button(pager, text="Load 1000 Demo Employees", command=self.load_demo).pack(side="right")

    def current_dept_filter(self):
        return self._dept_by_name.get(self.filter_dept.get())

    def reset_and_load(self):
        self.page = 1
        self.load_employees()

    def change_page(self, step):
        self.page += step
        self.load_employees()

    def load_employees(self):
        kw = self.search_var.get().strip()
        dept = self.current_dept_filter()
        status = self.filter_status.get()
        total = self.db.count_employees(kw, dept, status)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        self.page = min(max(1, self.page), pages)

        self.etree.delete(*self.etree.get_children())
        for r in self.db.get_employees(kw, dept, status, PAGE_SIZE, (self.page - 1) * PAGE_SIZE):
            self.etree.insert("", "end", tags=("inactive",) if r["status"] == "Inactive" else (), values=(
                r["id"], r["emp_code"], r["name"], r["email"] or "", r["phone"] or "",
                r["dept_name"] or "", r["designation"] or "", f"{r['salary']:,.0f}",
                r["join_date"], r["status"]))
        self.page_label.set(f"Page {self.page} of {pages}   ({total} employees)")

    def load_departments(self):
        depts = self.db.get_departments()
        self._dept_by_name = {d["name"]: d["id"] for d in depts}
        names = list(self._dept_by_name)
        self.dept_cb["values"] = names
        self.dept_filter_cb["values"] = ["All Departments"] + names
        if self.filter_dept.get() not in names:
            self.filter_dept.set("All Departments")
        self.dept_tree.delete(*self.dept_tree.get_children())
        for d in depts:
            self.dept_tree.insert("", "end", values=(d["id"], d["name"], d["headcount"]))

    def form_data(self):
        d = {k: v.get().strip() for k, v in self.ev.items()}
        if not d["emp_code"] or not d["name"]:
            raise ValueError("Employee Code and Full Name are required.")
        if d["email"] and not re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", d["email"]):
            raise ValueError("Please enter a valid email address.")
        if d["phone"] and not re.match(r"^\d{10}$", d["phone"]):
            raise ValueError("Phone number must be exactly 10 digits.")
        try:
            d["salary"] = float(d["salary"].replace(",", ""))
            if d["salary"] < 0:
                raise ValueError
        except ValueError:
            raise ValueError("Salary must be a number of 0 or more.")
        d["dept_id"] = self._dept_by_name.get(d["dept"])
        return d

    def add_employee(self):
        try:
            d = self.form_data()
            self.db.add_employee(d["emp_code"], d["name"], d["email"], d["phone"], d["dept_id"],
                                 d["designation"], d["salary"], d["join_date"], d["status"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_form(); self.refresh_all()

    def update_employee(self):
        if self.emp_id is None:
            return messagebox.showwarning("Select Employee", "Select an employee from the table first.")
        try:
            d = self.form_data()
            self.db.update_employee(self.emp_id, d["emp_code"], d["name"], d["email"], d["phone"],
                                    d["dept_id"], d["designation"], d["salary"], d["join_date"], d["status"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_form(); self.refresh_all()

    def delete_employee(self):
        if self.emp_id is None:
            return messagebox.showwarning("Select Employee", "Select an employee from the table first.")
        if messagebox.askyesno("Confirm", "Delete this employee record permanently?"):
            self.db.delete_employee(self.emp_id)
            self.clear_form(); self.refresh_all()

    def clear_form(self):
        for v in self.ev.values():
            v.set("")
        self.ev["join_date"].set(date.today().strftime("%Y-%m-%d"))
        self.ev["status"].set("Active")
        self.emp_id = None
        self.etree.selection_remove(self.etree.selection())

    def on_select(self, _):
        sel = self.etree.selection()
        if not sel:
            return
        v = self.etree.item(sel[0], "values")
        self.emp_id = int(v[0])
        keys = ("emp_code", "name", "email", "phone", "dept", "designation", "salary", "join_date", "status")
        for key, val in zip(keys, v[1:]):
            self.ev[key].set(val.replace(",", "") if key == "salary" else val)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="employees.csv")
        if not path:
            return
        rows = self.db.get_employees(self.search_var.get().strip(), self.current_dept_filter(),
                                     self.filter_status.get())          # all matching rows, no paging
        self.db.export_csv(path, ["Code", "Name", "Email", "Phone", "Department", "Designation",
                                  "Salary", "Join Date", "Status"],
                           [(r["emp_code"], r["name"], r["email"], r["phone"], r["dept_name"],
                             r["designation"], r["salary"], r["join_date"], r["status"]) for r in rows])
        messagebox.showinfo("Exported", f"{len(rows)} employees exported.")

    def load_demo(self):
        if messagebox.askyesno("Demo Data", "Add 1000 sample employees to test performance?"):
            self.db.seed_demo_data(1000)
            self.refresh_all()

    # ================================================================
    #                        DEPARTMENTS TAB
    # ================================================================
    def build_department_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Departments  ")
        self.dept_id = None
        self.dept_name = tk.StringVar()

        form = ttk.LabelFrame(tab, text="Department", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(form, text="Name *").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.dept_name, width=24).grid(row=0, column=1, padx=8, pady=6)
        b = ttk.Frame(form)
        b.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(b, text="Add", width=10, command=self.add_dept).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(b, text="Rename", width=10, command=self.rename_dept).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(b, text="Delete", width=10, command=self.delete_dept).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(b, text="Clear", width=10, command=self.clear_dept).grid(row=1, column=1, padx=3, pady=3)

        frame, self.dept_tree = make_table(tab, [("id", "ID"), ("name", "Department"), ("count", "Employees")],
                                           [50, 250, 100], height=16)
        frame.pack(side="left", fill="both", expand=True)
        self.dept_tree.bind("<<TreeviewSelect>>", self.on_dept_select)

    def add_dept(self):
        name = self.dept_name.get().strip()
        if not name:
            return messagebox.showerror("Error", "Department name is required.")
        try:
            self.db.add_department(name)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_dept(); self.refresh_all()

    def rename_dept(self):
        name = self.dept_name.get().strip()
        if self.dept_id is None or not name:
            return messagebox.showwarning("Select", "Select a department and enter the new name.")
        try:
            self.db.rename_department(self.dept_id, name)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_dept(); self.refresh_all()

    def delete_dept(self):
        if self.dept_id is None:
            return messagebox.showwarning("Select", "Select a department first.")
        if not messagebox.askyesno("Confirm", "Delete this department?"):
            return
        try:
            self.db.delete_department(self.dept_id)
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_dept(); self.refresh_all()

    def clear_dept(self):
        self.dept_name.set("")
        self.dept_id = None

    def on_dept_select(self, _):
        sel = self.dept_tree.selection()
        if sel:
            v = self.dept_tree.item(sel[0], "values")
            self.dept_id = int(v[0])
            self.dept_name.set(v[1])

    # ================================================================
    #                          REPORTS TAB
    # ================================================================
    def build_report_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Reports  ")

        cards = tk.Frame(tab)
        cards.pack(fill="x")
        self.card_vars = {}
        specs = [("total", "Total Employees", "#2d6a9f"), ("active", "Active", "#2d8f6f"),
                 ("departments", "Departments", "#7a4fa3"), ("payroll", "Yearly Payroll", "#d08a00"),
                 ("avg_salary", "Avg Salary", "#c0392b")]
        for i, (key, title, color) in enumerate(specs):
            card = tk.Frame(cards, bg=color, padx=14, pady=10)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            cards.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=color, fg="white", font=("Segoe UI", 10)).pack()
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, bg=color, fg="white", font=("Segoe UI", 16, "bold")).pack()
            self.card_vars[key] = var

        lower = ttk.Frame(tab)
        lower.pack(fill="both", expand=True, pady=(15, 0))
        left = ttk.LabelFrame(lower, text="Active Employees by Department", padding=6)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        frame, self.rep_dept = make_table(
            left, [("dept", "Department"), ("count", "Headcount"), ("avg", "Avg Salary"), ("total", "Total Salary")],
            [130, 80, 100, 110])
        frame.pack(fill="both", expand=True)

        right = ttk.LabelFrame(lower, text="Recent Joiners", padding=6)
        right.pack(side="left", fill="both", expand=True)
        frame, self.rep_join = make_table(
            right, [("code", "Code"), ("name", "Name"), ("dept", "Department"), ("date", "Joined")],
            [80, 130, 110, 90])
        frame.pack(fill="both", expand=True)

    def load_reports(self):
        s = self.db.get_summary()
        self.card_vars["total"].set(s["total"])
        self.card_vars["active"].set(s["active"])
        self.card_vars["departments"].set(s["departments"])
        self.card_vars["payroll"].set(f"{s['payroll']:,.0f}")
        self.card_vars["avg_salary"].set(f"{s['avg_salary']:,.0f}")

        self.rep_dept.delete(*self.rep_dept.get_children())
        for r in self.db.department_report():
            self.rep_dept.insert("", "end", values=(r["dept"], r["headcount"], f"{r['avg_salary']:,.0f}",
                                                    f"{r['total_salary']:,.0f}"))
        self.rep_join.delete(*self.rep_join.get_children())
        for r in self.db.recent_joiners():
            self.rep_join.insert("", "end", values=(r["emp_code"], r["name"], r["dept_name"] or "", r["join_date"]))


if __name__ == "__main__":
    root = tk.Tk()
    EmployeeApp(root)
    root.mainloop()
