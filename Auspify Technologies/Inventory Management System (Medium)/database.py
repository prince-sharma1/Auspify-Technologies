"""Database layer for the Inventory Management System (SQLite)."""
import csv
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")


class InventoryDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sku           TEXT NOT NULL UNIQUE,
                name          TEXT NOT NULL,
                category      TEXT,
                supplier      TEXT,
                price         REAL NOT NULL CHECK (price >= 0),
                quantity      INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
                reorder_level INTEGER NOT NULL DEFAULT 5
            );
            CREATE TABLE IF NOT EXISTS stock_movements (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                move_type  TEXT NOT NULL CHECK (move_type IN ('IN', 'OUT')),
                quantity   INTEGER NOT NULL CHECK (quantity > 0),
                note       TEXT,
                moved_at   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
            CREATE INDEX IF NOT EXISTS idx_moves_product ON stock_movements(product_id);
            """
        )
        self.conn.commit()

    @staticmethod
    def _now():
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    # ========================== PRODUCTS ==========================
    def add_product(self, sku, name, category, supplier, price, quantity, reorder_level):
        try:
            cur = self.conn.execute(
                "INSERT INTO products (sku, name, category, supplier, price, quantity, reorder_level) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sku, name, category, supplier, price, quantity, reorder_level))
        except sqlite3.IntegrityError:
            raise ValueError(f"SKU '{sku}' already exists.")
        if quantity > 0:
            self.conn.execute(
                "INSERT INTO stock_movements (product_id, move_type, quantity, note, moved_at) "
                "VALUES (?, 'IN', ?, 'Opening stock', ?)", (cur.lastrowid, quantity, self._now()))
        self.conn.commit()

    def update_product(self, product_id, sku, name, category, supplier, price, reorder_level):
        """Quantity is changed only through stock updates so history stays accurate."""
        try:
            self.conn.execute(
                "UPDATE products SET sku=?, name=?, category=?, supplier=?, price=?, reorder_level=? "
                "WHERE id=?", (sku, name, category, supplier, price, reorder_level, product_id))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"SKU '{sku}' already exists.")

    def delete_product(self, product_id):
        self.conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        self.conn.commit()

    def get_products(self, keyword="", category="", low_only=False):
        like = f"%{keyword}%"
        sql = "SELECT * FROM products WHERE (sku LIKE ? OR name LIKE ? OR supplier LIKE ?)"
        params = [like, like, like]
        if category and category != "All":
            sql += " AND category = ?"
            params.append(category)
        if low_only:
            sql += " AND quantity <= reorder_level"
        return self.conn.execute(sql + " ORDER BY name", params).fetchall()

    def get_categories(self):
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category").fetchall()
        return [r[0] for r in rows]

    # ========================== STOCK ==========================
    def update_stock(self, product_id, move_type, quantity, note=""):
        if move_type not in ("IN", "OUT"):
            raise ValueError("Movement type must be IN or OUT.")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        p = self.conn.execute("SELECT quantity FROM products WHERE id=?", (product_id,)).fetchone()
        if p is None:
            raise ValueError("Product not found.")
        if move_type == "OUT" and quantity > p["quantity"]:
            raise ValueError(f"Not enough stock. Only {p['quantity']} units available.")
        delta = quantity if move_type == "IN" else -quantity
        self.conn.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (delta, product_id))
        self.conn.execute(
            "INSERT INTO stock_movements (product_id, move_type, quantity, note, moved_at) "
            "VALUES (?, ?, ?, ?, ?)", (product_id, move_type, quantity, note, self._now()))
        self.conn.commit()
        return p["quantity"] + delta

    def get_movements(self, limit=200):
        return self.conn.execute(
            "SELECT m.id, m.moved_at, p.sku, p.name, m.move_type, m.quantity, m.note "
            "FROM stock_movements m JOIN products p ON p.id = m.product_id "
            "ORDER BY m.id DESC LIMIT ?", (limit,)).fetchall()

    # ========================== REPORTS ==========================
    def get_summary(self):
        r = self.conn.execute(
            "SELECT COUNT(*) AS products, COALESCE(SUM(quantity),0) AS units, "
            "COALESCE(SUM(quantity*price),0) AS value, "
            "COALESCE(SUM(quantity <= reorder_level AND quantity > 0),0) AS low, "
            "COALESCE(SUM(quantity = 0),0) AS out FROM products").fetchone()
        return dict(r)

    def category_report(self):
        return self.conn.execute(
            "SELECT COALESCE(NULLIF(category,''),'Uncategorized') AS category, COUNT(*) AS products, "
            "SUM(quantity) AS units, SUM(quantity*price) AS value FROM products "
            "GROUP BY 1 ORDER BY value DESC").fetchall()

    def low_stock(self):
        return self.conn.execute(
            "SELECT * FROM products WHERE quantity <= reorder_level ORDER BY quantity").fetchall()

    # ========================== EXPORT ==========================
    @staticmethod
    def export_csv(path, headers, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)

    def close(self):
        self.conn.close()
