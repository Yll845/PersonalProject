from __future__ import annotations

import sqlite3
from pathlib import Path

from .core import FinanceTracker
from .models import RecurringRule, Transaction


class DatabaseManager:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL, category TEXT NOT NULL, kind TEXT NOT NULL, description TEXT NOT NULL, tx_date TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, amount REAL NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS recurring_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL, category TEXT NOT NULL, kind TEXT NOT NULL, description TEXT NOT NULL, day_of_month INTEGER NOT NULL, start_date TEXT NOT NULL, end_date TEXT)")

    def save_tracker(self, tracker: FinanceTracker) -> None:
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM transactions")
            conn.execute("DELETE FROM budgets")
            conn.execute("DELETE FROM recurring_rules")
            conn.executemany("INSERT INTO transactions(amount, category, kind, description, tx_date) VALUES(?,?,?,?,?)", [(tx.amount, tx.category, tx.kind, tx.description, tx.tx_date) for tx in tracker.transactions])
            conn.executemany("INSERT INTO budgets(category, amount) VALUES(?,?)", [(k, v) for k, v in tracker.monthly_budgets.items()])
            conn.executemany("INSERT INTO recurring_rules(amount, category, kind, description, day_of_month, start_date, end_date) VALUES(?,?,?,?,?,?,?)", [(r.amount, r.category, r.kind, r.description, r.day_of_month, r.start_date, r.end_date) for r in tracker.recurring_rules])

    def load_tracker(self) -> FinanceTracker:
        tracker = FinanceTracker()
        self.initialize()
        with sqlite3.connect(self.db_path) as conn:
            for row in conn.execute("SELECT amount, category, kind, description, tx_date FROM transactions"):
                tracker.transactions.append(Transaction(*row))
            for row in conn.execute("SELECT category, amount FROM budgets"):
                tracker.monthly_budgets[row[0]] = float(row[1])
            for row in conn.execute("SELECT amount, category, kind, description, day_of_month, start_date, end_date FROM recurring_rules"):
                tracker.recurring_rules.append(RecurringRule(*row))
        return tracker
