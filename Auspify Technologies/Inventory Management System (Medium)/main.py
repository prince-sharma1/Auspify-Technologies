"""
Inventory Management System  -  Auspify Internship Task 3
Run:  python main.py
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from database import InventoryDB


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


class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.db = InventoryDB()
        root.title("Inventory Management System")
        root.geometry("1100x650")
        root.minsize(1000, 600)

        tk.Label(root, text="Inventory Management System", font=("Segoe UI", 18, "bold"),
                 bg="#5a3e1b", fg="white", pady=10).pack(fill="x")
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.build_products_tab()
        self.build_stock_tab()
        self.build_dashboard_tab()

        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()

    def refresh_all(self):
        self.load_products()
        self.load_stock_tab()
        self.load_dashboard()

    # ================================================================
    #                         PRODUCTS TAB
    # ================================================================
    def build_products_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Products  ")

        self.product_id = None
        self.pv = {k: tk.StringVar() for k in
                   ("sku", "name", "category", "supplier", "price", "quantity", "reorder")}
        self.pv["reorder"].set("5")

        form = ttk.LabelFrame(tab, text="Product Details", padding=10)
        form.pack(side="left", fill="y", padx=(0, 10))
        labels = [("SKU / Code *", "sku"), ("Product Name *", "name"), ("Category", "category"),
                  ("Supplier", "supplier"), ("Unit Price *", "price"),
                  ("Opening Qty", "quantity"), ("Reorder Level", "reorder")]
        for i, (label, key) in enumerate(labels):
            ttk.Label(form, text=label).grid(row=i, column=0, sticky="w", pady=5)
            if key == "category":
                self.cat_entry = ttk.Combobox(form, textvariable=self.pv[key], width=23)
                self.cat_entry.grid(row=i, column=1, padx=(8, 0))
            else:
                ttk.Entry(form, textvariable=self.pv[key], width=26).grid(row=i, column=1, padx=(8, 0))
        ttk.Label(form, text="Quantity changes later are made\nin the Stock Update tab.",
                  foreground="#666").grid(row=len(labels), column=0, columnspan=2, pady=(6, 0))
        b = ttk.Frame(form)
        b.grid(row=len(labels) + 1, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(b, text="Add", width=10, command=self.add_product).grid(row=0, column=0, padx=3, pady=3)
        ttk.Button(b, text="Update", width=10, command=self.update_product).grid(row=0, column=1, padx=3, pady=3)
        ttk.Button(b, text="Delete", width=10, command=self.delete_product).grid(row=1, column=0, padx=3, pady=3)
        ttk.Button(b, text="Clear", width=10, command=self.clear_product).grid(row=1, column=1, padx=3, pady=3)

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)

        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(0, 8))
        self.search_var = tk.StringVar()
        self.filter_cat = tk.StringVar(value="All")
        self.low_only = tk.BooleanVar()
        ttk.Label(bar, text="Search:").pack(side="left")
        e = ttk.Entry(bar, textvariable=self.search_var, width=22)
        e.pack(side="left", padx=5)
        e.bind("<KeyRelease>", lambda ev: self.load_products())
        ttk.Label(bar, text="Category:").pack(side="left", padx=(10, 0))
        self.cat_filter_cb = ttk.Combobox(bar, textvariable=self.filter_cat, width=16, state="readonly")
        self.cat_filter_cb.pack(side="left", padx=5)
        self.cat_filter_cb.bind("<<ComboboxSelected>>", lambda ev: self.load_products())
        ttk.Checkbutton(bar, text="Low stock only", variable=self.low_only,
                        command=self.load_products).pack(side="left", padx=8)
        ttk.Button(bar, text="Export CSV", command=self.export_products).pack(side="right")

        cols = [("id", "ID"), ("sku", "SKU"), ("name", "Name"), ("category", "Category"),
                ("supplier", "Supplier"), ("price", "Price"), ("qty", "Qty"), ("reorder", "Reorder")]
        frame, self.ptree = make_table(right, cols, [40, 80, 180, 100, 120, 70, 55, 60], height=16)
        frame.pack(fill="both", expand=True)
        self.ptree.tag_configure("low", background="#fff3cd")
        self.ptree.tag_configure("out", background="#f8d7da")
        self.ptree.bind("<<TreeviewSelect>>", self.on_product_select)
        tk.Label(right, text="Yellow = low stock    Red = out of stock", anchor="w",
                 fg="#555").pack(fill="x", pady=(4, 0))

    def product_form(self, editing=False):
        d = {k: v.get().strip() for k, v in self.pv.items()}
        if not d["sku"] or not d["name"]:
            raise ValueError("SKU and Product Name are required.")
        try:
            d["price"] = float(d["price"])
            if d["price"] < 0:
                raise ValueError
        except ValueError:
            raise ValueError("Unit price must be a number of 0 or more.")
        if not d["reorder"].isdigit():
            raise ValueError("Reorder level must be a whole number.")
        d["reorder"] = int(d["reorder"])
        if not editing:
            if d["quantity"] == "":
                d["quantity"] = "0"
            if not d["quantity"].isdigit():
                raise ValueError("Opening quantity must be a whole number.")
            d["quantity"] = int(d["quantity"])
        return d

    def add_product(self):
        try:
            d = self.product_form()
            self.db.add_product(d["sku"], d["name"], d["category"], d["supplier"],
                                d["price"], d["quantity"], d["reorder"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_product(); self.refresh_all()

    def update_product(self):
        if self.product_id is None:
            return messagebox.showwarning("Select Product", "Select a product from the table first.")
        try:
            d = self.product_form(editing=True)
            self.db.update_product(self.product_id, d["sku"], d["name"], d["category"],
                                   d["supplier"], d["price"], d["reorder"])
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        self.clear_product(); self.refresh_all()

    def delete_product(self):
        if self.product_id is None:
            return messagebox.showwarning("Select Product", "Select a product from the table first.")
        if messagebox.askyesno("Confirm", "Delete this product and its stock history?"):
            self.db.delete_product(self.product_id)
            self.clear_product(); self.refresh_all()

    def clear_product(self):
        for k, v in self.pv.items():
            v.set("5" if k == "reorder" else "")
        self.product_id = None
        self.ptree.selection_remove(self.ptree.selection())

    def load_products(self):
        cats = self.db.get_categories()
        self.cat_entry["values"] = cats
        self.cat_filter_cb["values"] = ["All"] + cats
        self.ptree.delete(*self.ptree.get_children())
        rows = self.db.get_products(self.search_var.get().strip(), self.filter_cat.get(), self.low_only.get())
        for p in rows:
            tag = "out" if p["quantity"] == 0 else ("low" if p["quantity"] <= p["reorder_level"] else "")
            self.ptree.insert("", "end", tags=(tag,), values=(
                p["id"], p["sku"], p["name"], p["category"] or "", p["supplier"] or "",
                f"{p['price']:.2f}", p["quantity"], p["reorder_level"]))

    def on_product_select(self, _):
        sel = self.ptree.selection()
        if not sel:
            return
        v = self.ptree.item(sel[0], "values")
        self.product_id = int(v[0])
        for key, val in zip(("sku", "name", "category", "supplier", "price", "quantity", "reorder"), v[1:]):
            self.pv[key].set(val)

    def export_products(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="products.csv")
        if not path:
            return
        rows = self.db.get_products(self.search_var.get().strip(), self.filter_cat.get(), self.low_only.get())
        self.db.export_csv(path, ["SKU", "Name", "Category", "Supplier", "Price", "Quantity", "Reorder Level"],
                           [(p["sku"], p["name"], p["category"], p["supplier"], p["price"],
                             p["quantity"], p["reorder_level"]) for p in rows])
        messagebox.showinfo("Exported", f"{len(rows)} products exported.")

    # ================================================================
    #                        STOCK UPDATE TAB
    # ================================================================
    def build_stock_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Stock Update  ")

        box = ttk.LabelFrame(tab, text="Record Stock Movement", padding=10)
        box.pack(fill="x")
        self.stock_product = ttk.Combobox(box, width=48, state="readonly")
        self.move_type = tk.StringVar(value="IN")
        self.move_qty = tk.StringVar()
        self.move_note = tk.StringVar()

        ttk.Label(box, text="Product:").grid(row=0, column=0, sticky="w")
        self.stock_product.grid(row=0, column=1, columnspan=3, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(box, text="Stock IN (purchase / return)", variable=self.move_type,
                        value="IN").grid(row=1, column=1, sticky="w", padx=8)
        ttk.Radiobutton(box, text="Stock OUT (sale / usage)", variable=self.move_type,
                        value="OUT").grid(row=1, column=2, sticky="w")
        ttk.Label(box, text="Quantity:").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(box, textvariable=self.move_qty, width=12).grid(row=2, column=1, sticky="w", padx=8)
        ttk.Label(box, text="Note:").grid(row=2, column=2, sticky="e")
        ttk.Entry(box, textvariable=self.move_note, width=30).grid(row=2, column=3, padx=8)
        ttk.Button(box, text="Apply", command=self.apply_stock).grid(row=2, column=4, padx=8)

        ttk.Label(tab, text="Recent Stock Movements", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 5))
        cols = [("id", "ID"), ("date", "Date"), ("sku", "SKU"), ("name", "Product"),
                ("type", "Type"), ("qty", "Qty"), ("note", "Note")]
        frame, self.mtree = make_table(tab, cols, [50, 130, 90, 220, 60, 60, 250], height=14)
        frame.pack(fill="both", expand=True)
        self.mtree.tag_configure("IN", foreground="#1b7a1b")
        self.mtree.tag_configure("OUT", foreground="#b02020")

    def load_stock_tab(self):
        self._stock_map = {f"{p['sku']} - {p['name']} (in stock: {p['quantity']})": p["id"]
                           for p in self.db.get_products()}
        self.stock_product["values"] = list(self._stock_map)
        self.stock_product.set("")
        self.mtree.delete(*self.mtree.get_children())
        for m in self.db.get_movements():
            self.mtree.insert("", "end", tags=(m["move_type"],), values=(
                m["id"], m["moved_at"], m["sku"], m["name"], m["move_type"], m["quantity"], m["note"] or ""))

    def apply_stock(self):
        label = self.stock_product.get()
        if not label:
            return messagebox.showwarning("Missing", "Select a product.")
        qty = self.move_qty.get().strip()
        if not qty.isdigit() or int(qty) <= 0:
            return messagebox.showerror("Error", "Quantity must be a whole number greater than 0.")
        try:
            new_qty = self.db.update_stock(self._stock_map[label], self.move_type.get(),
                                           int(qty), self.move_note.get().strip())
        except ValueError as e:
            return messagebox.showerror("Error", str(e))
        messagebox.showinfo("Done", f"Stock updated. New quantity: {new_qty}")
        self.move_qty.set(""); self.move_note.set("")
        self.refresh_all()

    # ================================================================
    #                        DASHBOARD TAB
    # ================================================================
    def build_dashboard_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Reports Dashboard  ")

        self.cards = tk.Frame(tab)
        self.cards.pack(fill="x")
        self.card_vars = {}
        specs = [("products", "Products", "#2d6a9f"), ("units", "Total Units", "#2d8f6f"),
                 ("value", "Stock Value", "#7a4fa3"), ("low", "Low Stock", "#d08a00"),
                 ("out", "Out of Stock", "#c0392b")]
        for i, (key, title, color) in enumerate(specs):
            card = tk.Frame(self.cards, bg=color, padx=14, pady=10)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            self.cards.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=color, fg="white", font=("Segoe UI", 10)).pack()
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, bg=color, fg="white", font=("Segoe UI", 18, "bold")).pack()
            self.card_vars[key] = var

        lower = ttk.Frame(tab)
        lower.pack(fill="both", expand=True, pady=(15, 0))
        left = ttk.LabelFrame(lower, text="Stock by Category", padding=6)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        frame, self.cat_tree = make_table(
            left, [("cat", "Category"), ("products", "Products"), ("units", "Units"), ("value", "Value")],
            [140, 70, 70, 100])
        frame.pack(fill="both", expand=True)

        right = ttk.LabelFrame(lower, text="Low / Out of Stock (needs reorder)", padding=6)
        right.pack(side="left", fill="both", expand=True)
        frame, self.low_tree = make_table(
            right, [("sku", "SKU"), ("name", "Product"), ("qty", "Qty"), ("reorder", "Reorder At")],
            [80, 170, 50, 80])
        frame.pack(fill="both", expand=True)
        self.low_tree.tag_configure("out", background="#f8d7da")
        self.low_tree.tag_configure("low", background="#fff3cd")

    def load_dashboard(self):
        s = self.db.get_summary()
        self.card_vars["products"].set(s["products"])
        self.card_vars["units"].set(s["units"])
        self.card_vars["value"].set(f"{s['value']:,.2f}")
        self.card_vars["low"].set(s["low"])
        self.card_vars["out"].set(s["out"])

        self.cat_tree.delete(*self.cat_tree.get_children())
        for r in self.db.category_report():
            self.cat_tree.insert("", "end", values=(r["category"], r["products"], r["units"], f"{r['value']:,.2f}"))
        self.low_tree.delete(*self.low_tree.get_children())
        for p in self.db.low_stock():
            self.low_tree.insert("", "end", tags=("out" if p["quantity"] == 0 else "low",),
                                 values=(p["sku"], p["name"], p["quantity"], p["reorder_level"]))


if __name__ == "__main__":
    root = tk.Tk()
    InventoryApp(root)
    root.mainloop()
