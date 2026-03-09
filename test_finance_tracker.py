import csv

import pytest

from finance_tracker import DatabaseManager, FinanceTracker, create_fastapi_app, is_authorized_bearer


def test_summary_and_breakdown() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(4000, "salary", "income", tx_date="2026-01-01")
    tracker.add_transaction(1200, "rent", "expense", tx_date="2026-01-02")
    tracker.add_transaction(300, "food", "expense", tx_date="2026-01-03")

    assert tracker.summary() == {
        "total_income": 4000,
        "total_expense": 1500,
        "net_savings": 2500,
    }
    assert tracker.category_breakdown("expense") == {"rent": 1200.0, "food": 300.0}


def test_month_filtering_for_summary_and_list() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(1000, "salary", "income", tx_date="2026-01-01")
    tracker.add_transaction(200, "food", "expense", tx_date="2026-01-07")
    tracker.add_transaction(700, "salary", "income", tx_date="2026-02-01")

    jan = tracker.summary(month="2026-01")
    feb = tracker.summary(month="2026-02")

    assert jan == {"total_income": 1000, "total_expense": 200, "net_savings": 800}
    assert feb == {"total_income": 700, "total_expense": 0, "net_savings": 700}
    assert len(tracker.list_transactions(month="2026-01")) == 2


def test_budget_status_and_insights() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(2000, "salary", "income", tx_date="2026-01-01")
    tracker.add_transaction(700, "food", "expense", tx_date="2026-01-02")
    tracker.set_budget("food", 500)

    status = tracker.budget_status()
    assert status["food"]["over_budget"] is True
    assert status["food"]["remaining"] == -200.0

    insights = tracker.smart_insights()
    assert any("Highest spending category" in line for line in insights)
    assert any("Budget alert" in line for line in insights)


def test_monthly_report_and_trend_insight() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(3000, "salary", "income", tx_date="2026-01-01")
    tracker.add_transaction(500, "rent", "expense", tx_date="2026-01-02")
    tracker.add_transaction(3000, "salary", "income", tx_date="2026-02-01")
    tracker.add_transaction(800, "rent", "expense", tx_date="2026-02-02")

    report = tracker.monthly_report()
    assert report["2026-01"]["total_expense"] == 500
    assert report["2026-02"]["total_expense"] == 800

    insights = tracker.smart_insights()
    assert any("Monthly trend" in line for line in insights)


def test_invalid_month_raises_error() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(100, "misc", "expense", tx_date="2026-01-01")

    with pytest.raises(ValueError, match="YYYY-MM"):
        tracker.summary(month="2026-13")


def test_recurring_rule_generation_idempotent() -> None:
    tracker = FinanceTracker()
    tracker.add_recurring_rule(
        amount=1500,
        category="rent",
        kind="expense",
        day_of_month=5,
        description="monthly rent",
        start_date="2026-01-01",
    )

    first = tracker.apply_recurring_for_month("2026-02")
    second = tracker.apply_recurring_for_month("2026-02")

    assert first == 1
    assert second == 0
    assert tracker.summary(month="2026-02")["total_expense"] == 1500


def test_csv_export_import_roundtrip(tmp_path) -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(1200, "salary", "income", tx_date="2026-01-01", description="job")
    tracker.add_transaction(100, "food", "expense", tx_date="2026-01-03", description="groceries")

    csv_path = tmp_path / "transactions.csv"
    exported = tracker.export_csv(csv_path)
    assert exported == 2

    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 2

    imported_tracker = FinanceTracker()
    imported = imported_tracker.import_csv(csv_path)
    assert imported == 2
    assert imported_tracker.summary() == tracker.summary()


def test_save_and_load_includes_recurring_rules(tmp_path) -> None:
    file_path = tmp_path / "data.json"

    tracker = FinanceTracker()
    tracker.add_transaction(100, "gift", "income", tx_date="2026-01-01")
    tracker.set_budget("food", 250)
    tracker.add_recurring_rule(20, "subscription", "expense", 10, start_date="2026-01-01")
    tracker.save(file_path)

    loaded = FinanceTracker.load(file_path)
    assert loaded.summary()["total_income"] == 100
    assert loaded.monthly_budgets["food"] == 250
    assert len(loaded.recurring_rules) == 1


def test_spending_bar_chart() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(400, "food", "expense", tx_date="2026-03-01")
    tracker.add_transaction(100, "transport", "expense", tx_date="2026-03-02")
    chart = tracker.spending_bar_chart(month="2026-03")

    assert "Expense Chart" in chart
    assert "food" in chart
    assert "transport" in chart


def test_database_roundtrip(tmp_path) -> None:
    db_path = tmp_path / "finance.db"
    tracker = FinanceTracker()
    tracker.add_transaction(900, "salary", "income", tx_date="2026-04-01")
    tracker.set_budget("food", 300)
    tracker.add_recurring_rule(100, "subscription", "expense", 10, start_date="2026-01-01")

    db = DatabaseManager(db_path)
    db.save_tracker(tracker)

    loaded = db.load_tracker()
    assert loaded.summary()["total_income"] == 900
    assert loaded.monthly_budgets["food"] == 300
    assert len(loaded.recurring_rules) == 1


def test_bearer_token_validation_helper() -> None:
    assert is_authorized_bearer("Bearer abc", "abc") is True
    assert is_authorized_bearer("Bearer wrong", "abc") is False
    assert is_authorized_bearer("", "") is True


def test_fastapi_app_factory() -> None:
    tracker = FinanceTracker()
    tracker.add_transaction(100, "salary", "income", tx_date="2026-01-01")
    try:
        app = create_fastapi_app(tracker, token="secret")
    except ValueError as exc:
        assert "FastAPI is not installed" in str(exc)
    else:
        paths = {route.path for route in app.router.routes}
        assert "/health" in paths
        assert "/summary" in paths
        assert "/transactions" in paths
