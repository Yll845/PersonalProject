from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List
from urllib.request import Request, urlopen

from .models import KIND_OPTIONS, RecurringRule, Transaction


class FinanceTracker:
    def __init__(self) -> None:
        self.transactions: List[Transaction] = []
        self.monthly_budgets: Dict[str, float] = {}
        self.recurring_rules: List[RecurringRule] = []

    @staticmethod
    def _normalize_category(category: str) -> str:
        return category.strip().lower()

    @staticmethod
    def _parse_month(month: str | None) -> tuple[int, int] | None:
        if month is None:
            return None
        try:
            year, month_value = month.split("-")
            parsed = (int(year), int(month_value))
        except (ValueError, AttributeError):
            raise ValueError("month must be in YYYY-MM format") from None
        if parsed[1] < 1 or parsed[1] > 12:
            raise ValueError("month must be in YYYY-MM format")
        return parsed

    @classmethod
    def _is_in_month(cls, tx_date: str, month: str | None) -> bool:
        parsed_month = cls._parse_month(month)
        if parsed_month is None:
            return True
        tx_datetime = datetime.strptime(tx_date, "%Y-%m-%d")
        return tx_datetime.year == parsed_month[0] and tx_datetime.month == parsed_month[1]

    @staticmethod
    def _date_in_range(tx_date: str, start_date: str, end_date: str | None) -> bool:
        current = datetime.strptime(tx_date, "%Y-%m-%d").date()
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if current < start:
            return False
        if end_date is None:
            return True
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return current <= end

    def add_transaction(self, amount: float, category: str, kind: str, description: str = "", tx_date: str | None = None) -> Transaction:
        tx = Transaction(
            amount=amount,
            category=self._normalize_category(category),
            kind=kind,
            description=description.strip(),
            tx_date=tx_date or date.today().isoformat(),
        )
        self.transactions.append(tx)
        return tx

    def add_recurring_rule(
        self,
        amount: float,
        category: str,
        kind: str,
        day_of_month: int,
        description: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> RecurringRule:
        rule = RecurringRule(
            amount=amount,
            category=self._normalize_category(category),
            kind=kind,
            description=description.strip(),
            day_of_month=day_of_month,
            start_date=start_date or date.today().isoformat(),
            end_date=end_date,
        )
        self.recurring_rules.append(rule)
        return rule

    def apply_recurring_for_month(self, month: str) -> int:
        parsed = self._parse_month(month)
        assert parsed is not None
        year, month_value = parsed
        created = 0
        for rule in self.recurring_rules:
            tx_date = date(year, month_value, rule.day_of_month).isoformat()
            if not self._date_in_range(tx_date, rule.start_date, rule.end_date):
                continue
            exists = any(
                tx.tx_date == tx_date and tx.kind == rule.kind and tx.category == rule.category
                and tx.description == rule.description and tx.amount == rule.amount
                for tx in self.transactions
            )
            if not exists:
                self.transactions.append(Transaction(rule.amount, rule.category, rule.kind, rule.description, tx_date))
                created += 1
        return created

    def list_transactions(self, month: str | None = None) -> List[Transaction]:
        return sorted([tx for tx in self.transactions if self._is_in_month(tx.tx_date, month)], key=lambda tx: tx.tx_date)

    def set_budget(self, category: str, amount: float) -> None:
        if amount <= 0:
            raise ValueError("budget must be positive")
        self.monthly_budgets[self._normalize_category(category)] = amount

    def summary(self, month: str | None = None) -> Dict[str, float]:
        filtered = [tx for tx in self.transactions if self._is_in_month(tx.tx_date, month)]
        income = sum(t.amount for t in filtered if t.kind == "income")
        expense = sum(t.amount for t in filtered if t.kind == "expense")
        return {"total_income": round(income, 2), "total_expense": round(expense, 2), "net_savings": round(income - expense, 2)}

    def category_breakdown(self, kind: str = "expense", month: str | None = None) -> Dict[str, float]:
        if kind not in KIND_OPTIONS:
            raise ValueError("kind must be 'income' or 'expense'")
        breakdown: Dict[str, float] = {}
        for tx in self.transactions:
            if tx.kind == kind and self._is_in_month(tx.tx_date, month):
                breakdown[tx.category] = round(breakdown.get(tx.category, 0.0) + tx.amount, 2)
        return breakdown

    def budget_status(self, month: str | None = None) -> Dict[str, Dict[str, float | bool]]:
        expenses = self.category_breakdown(kind="expense", month=month)
        status: Dict[str, Dict[str, float | bool]] = {}
        for category, budget in self.monthly_budgets.items():
            spent = expenses.get(category, 0.0)
            remaining = round(budget - spent, 2)
            status[category] = {"budget": round(budget, 2), "spent": round(spent, 2), "remaining": remaining, "over_budget": spent > budget}
        return status

    def monthly_report(self) -> Dict[str, Dict[str, float]]:
        return {month: self.summary(month=month) for month in sorted({tx.tx_date[:7] for tx in self.transactions})}

    def smart_insights(self, month: str | None = None) -> List[str]:
        insights: List[str] = []
        data = self.summary(month=month)
        if data["total_income"] == 0 and data["total_expense"] > 0:
            insights.append("You have expenses but no recorded income. Add income streams to improve tracking.")
        elif data["total_income"] > 0:
            savings_rate = (data["net_savings"] / data["total_income"]) * 100
            insights.append(f"Great! Your savings rate is {savings_rate:.1f}%." if savings_rate >= 20 else f"Your savings rate is {savings_rate:.1f}%. Consider targeting at least 20%.")

        expense_breakdown = self.category_breakdown("expense", month=month)
        if expense_breakdown:
            top_category = max(expense_breakdown, key=expense_breakdown.get)
            insights.append(f"Highest spending category is '{top_category}' at ${expense_breakdown[top_category]:.2f}.")

        for category, details in self.budget_status(month=month).items():
            if details["over_budget"]:
                insights.append(f"Budget alert: '{category}' exceeded by ${abs(details['remaining']):.2f}.")

        report = self.monthly_report()
        if len(report) >= 2:
            previous, current = sorted(report.keys())[-2:]
            prev_expense = report[previous]["total_expense"]
            curr_expense = report[current]["total_expense"]
            if prev_expense > 0:
                change_pct = ((curr_expense - prev_expense) / prev_expense) * 100
                insights.append(f"Monthly trend: expenses are {'up' if change_pct > 0 else 'down'} {abs(change_pct):.1f}% ({previous} -> {current}).")

        return insights or ["No insights yet. Add transactions to get personalized recommendations."]

    def spending_bar_chart(self, month: str | None = None, width: int = 30) -> str:
        breakdown = self.category_breakdown(kind="expense", month=month)
        if not breakdown:
            return "No expense data available for chart."
        top = max(breakdown.values())
        lines = ["Expense Chart"]
        for category, value in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{category:15} | {'#' * max(1, int((value / top) * width))} {value:.2f}")
        return "\n".join(lines)

    def export_csv(self, filepath: str | Path, month: str | None = None) -> int:
        rows = self.list_transactions(month=month)
        with Path(filepath).open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["date", "kind", "amount", "category", "description"])
            writer.writeheader()
            for tx in rows:
                writer.writerow({"date": tx.tx_date, "kind": tx.kind, "amount": f"{tx.amount:.2f}", "category": tx.category, "description": tx.description})
        return len(rows)

    def import_csv(self, filepath: str | Path) -> int:
        path = Path(filepath)
        if not path.exists():
            raise ValueError(f"CSV file not found: {filepath}")
        required = {"date", "kind", "amount", "category", "description"}
        imported = 0
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
                raise ValueError("CSV must include headers: date, kind, amount, category, description")
            for row in reader:
                self.add_transaction(float(row["amount"]), row["category"], row["kind"], row.get("description", ""), row["date"])
                imported += 1
        return imported

    def save(self, filepath: str | Path) -> None:
        payload = {
            "transactions": [asdict(tx) for tx in self.transactions],
            "monthly_budgets": self.monthly_budgets,
            "recurring_rules": [asdict(rule) for rule in self.recurring_rules],
        }
        Path(filepath).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, filepath: str | Path) -> "FinanceTracker":
        tracker = cls()
        path = Path(filepath)
        if not path.exists():
            return tracker
        payload = json.loads(path.read_text(encoding="utf-8"))
        for tx_data in payload.get("transactions", []):
            tracker.transactions.append(Transaction(**tx_data))
        tracker.monthly_budgets = {k.lower(): float(v) for k, v in payload.get("monthly_budgets", {}).items()}
        for rule in payload.get("recurring_rules", []):
            tracker.recurring_rules.append(RecurringRule(**rule))
        return tracker


def scrape_exchange_rate(from_currency: str, to_currency: str) -> float:
    from_code = from_currency.upper()
    to_code = to_currency.upper()
    url = f"https://www.x-rates.com/calculator/?from={from_code}&to={to_code}&amount=1"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as exc:  # network/runtime error wrapping
        raise ValueError(f"Unable to fetch exchange rate: {exc}") from exc

    match = re.search(r'ccOutputRslt">\s*([0-9.]+)', html)
    if not match:
        raise ValueError("Unable to parse exchange rate from source")
    return float(match.group(1))
