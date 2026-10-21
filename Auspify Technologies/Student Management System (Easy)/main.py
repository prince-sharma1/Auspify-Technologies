"""
Student Management System  -  Auspify Internship Task 1
Run:  python main.py
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox

from database import StudentDB


class StudentApp:
    COLUMNS = ("id", "roll_no", "name", "email", "phone", "course", "age")

    def __init__(self, root):
        self.root = root
        self.db = StudentDB()
        self.selected_id = None

        root.title("Student Management System")
        root.geometry("1000x580")
        root.minsize(900, 520)

        self.vars = {k: tk.StringVar() for k in
                     ("roll_no", "name", "email", "phone", "course", "age")}
        self.search_var = tk.StringVar()

        self.build_ui()
        self.load_students()

    # ------------------------------------------------------------ UI
    def build_ui(self):
        tk.Label(self.root, text="Student Management System",
                 font=("Segoe UI", 18, "bold"), bg="#1f3a5f", fg="white",
                 pady=10).pack(fill="x")

        body = ttk.Frame(self.root, padding=10)
        body.pack(fill="both", expand=True)

        # ---- Left: form
        form = ttk.LabelFrame(body, text="Student Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))

        fields = [("Roll No *", "roll_no"), ("Full Name *", "name"),
                  ("Email", "email"), ("Phone", "phone"),
                  ("Course", "course"), ("Age", "age")]
        for i, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=6)
            ttk.Entry(form, textvariable=self.vars[key], width=26).grid(
                row=i, column=1, pady=6, padx=(8, 0))

        btns = ttk.Frame(form)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btns, text="Add", width=10, command=self.add_student).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(btns, text="Update", width=10, command=self.update_student).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(btns, text="Delete", width=10, command=self.delete_student).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(btns, text="Clear", width=10, command=self.clear_form).grid(row=1, column=1, padx=3, pady=3)

        # ---- Right: search + table
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        search_bar = ttk.Frame(right)
        search_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(search_bar, text="Search:").pack(side="left")
        entry = ttk.Entry(search_bar, textvariable=self.search_var, width=30)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda e: self.search())
        ttk.Button(search_bar, text="Show All", command=self.show_all).pack(side="left")

        table_frame = ttk.Frame(right)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=self.COLUMNS,
                                 show="headings", selectmode="browse")
        headings = {"id": ("ID", 40), "roll_no": ("Roll No", 80),
                    "name": ("Name", 150), "email": ("Email", 170),
                    "phone": ("Phone", 100), "course": ("Course", 110),
                    "age": ("Age", 50)}
        for col, (text, width) in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.status = tk.StringVar()
        tk.Label(self.root, textvariable=self.status, anchor="w", relief="sunken",
                 padx=8).pack(fill="x", side="bottom")

    # ------------------------------------------------------ Helpers
    def get_form_data(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}

        if not data["roll_no"] or not data["name"]:
            raise ValueError("Roll No and Full Name are required.")
        if data["email"] and not re.match(r"^[\w.+-]+@[\w-]+\.[\w.-]+$", data["email"]):
            raise ValueError("Please enter a valid email address.")
        if data["phone"] and not re.match(r"^\d{10}$", data["phone"]):
            raise ValueError("Phone number must be exactly 10 digits.")
        if data["age"]:
            if not data["age"].isdigit() or not (5 <= int(data["age"]) <= 100):
                raise ValueError("Age must be a number between 5 and 100.")
            data["age"] = int(data["age"])
        else:
            data["age"] = None
        return data

    def fill_table(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=tuple(r[c] if r[c] is not None else "" for c in self.COLUMNS))
        self.status.set(f"Total records shown: {len(rows)}")

    def load_students(self):
        self.fill_table(self.db.get_all())

    def clear_form(self):
        for v in self.vars.values():
            v.set("")
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())

    # ---------------------------------------------------- Actions
    def add_student(self):
        try:
            d = self.get_form_data()
            self.db.add_student(d["roll_no"], d["name"], d["email"],
                                d["phone"], d["course"], d["age"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        messagebox.showinfo("Success", "Student added successfully.")
        self.clear_form()
        self.load_students()

    def update_student(self):
        if self.selected_id is None:
            return messagebox.showwarning("Select Student", "Select a student from the table first.")
        try:
            d = self.get_form_data()
            self.db.update_student(self.selected_id, d["roll_no"], d["name"],
                                   d["email"], d["phone"], d["course"], d["age"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        messagebox.showinfo("Success", "Student updated successfully.")
        self.clear_form()
        self.load_students()

    def delete_student(self):
        if self.selected_id is None:
            return messagebox.showwarning("Select Student", "Select a student from the table first.")
        if messagebox.askyesno("Confirm Delete", "Delete this student record permanently?"):
            self.db.delete_student(self.selected_id)
            self.clear_form()
            self.load_students()

    def search(self):
        keyword = self.search_var.get().strip()
        self.fill_table(self.db.search(keyword) if keyword else self.db.get_all())

    def show_all(self):
        self.search_var.set("")
        self.load_students()

    def on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self.selected_id = int(values[0])
        for key, val in zip(("roll_no", "name", "email", "phone", "course", "age"), values[1:]):
            self.vars[key].set(val)


if __name__ == "__main__":
    root = tk.Tk()
    StudentApp(root)
    root.mainloop()
