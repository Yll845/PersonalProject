from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

KIND_OPTIONS = {"income", "expense"}


@dataclass
class Transaction:
    amount: float
    category: str
    kind: str
    description: str
    tx_date: str

    def __post_init__(self) -> None:
        if self.kind not in KIND_OPTIONS:
            raise ValueError("kind must be 'income' or 'expense'")
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        datetime.strptime(self.tx_date, "%Y-%m-%d")


@dataclass
class RecurringRule:
    amount: float
    category: str
    kind: str
    description: str
    day_of_month: int
    start_date: str
    end_date: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in KIND_OPTIONS:
            raise ValueError("kind must be 'income' or 'expense'")
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if self.day_of_month < 1 or self.day_of_month > 28:
            raise ValueError("day_of_month must be between 1 and 28")
        datetime.strptime(self.start_date, "%Y-%m-%d")
        if self.end_date is not None:
            datetime.strptime(self.end_date, "%Y-%m-%d")
