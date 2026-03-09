from __future__ import annotations

import argparse
import json

from .api import create_fastapi_app, start_api_server
from .core import FinanceTracker, scrape_exchange_rate
from .db import DatabaseManager


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smart Personal Finance Tracker")
    parser.add_argument("--file", default="finance_data.json", help="Path to data file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_tx = subparsers.add_parser("add", help="Add a transaction")
    add_tx.add_argument("kind", choices=["income", "expense"])
    add_tx.add_argument("amount", type=float)
    add_tx.add_argument("category")
    add_tx.add_argument("--description", default="")
    add_tx.add_argument("--date", default=None)

    budget = subparsers.add_parser("budget", help="Set monthly budget by category")
    budget.add_argument("category")
    budget.add_argument("amount", type=float)

    summary = subparsers.add_parser("summary", help="Show income/expense summary")
    summary.add_argument("--month", default=None)

    insights = subparsers.add_parser("insights", help="Show smart insights")
    insights.add_argument("--month", default=None)

    list_cmd = subparsers.add_parser("list", help="List transactions")
    list_cmd.add_argument("--month", default=None)

    subparsers.add_parser("report", help="Show month-over-month summary report")

    chart = subparsers.add_parser("chart", help="Show ASCII expense chart")
    chart.add_argument("--month", default=None)

    recur_add = subparsers.add_parser("recur-add", help="Add recurring transaction rule")
    recur_add.add_argument("kind", choices=["income", "expense"])
    recur_add.add_argument("amount", type=float)
    recur_add.add_argument("category")
    recur_add.add_argument("day", type=int)
    recur_add.add_argument("--description", default="")
    recur_add.add_argument("--start-date", default=None)
    recur_add.add_argument("--end-date", default=None)

    recur_apply = subparsers.add_parser("recur-apply", help="Generate recurring transactions")
    recur_apply.add_argument("month")

    export_csv = subparsers.add_parser("export-csv", help="Export transactions to CSV")
    export_csv.add_argument("path")
    export_csv.add_argument("--month", default=None)

    import_csv = subparsers.add_parser("import-csv", help="Import transactions from CSV")
    import_csv.add_argument("path")

    db_init = subparsers.add_parser("db-init", help="Initialize SQLite database")
    db_init.add_argument("db_path")
    db_save = subparsers.add_parser("db-save", help="Save state to SQLite")
    db_save.add_argument("db_path")
    db_load = subparsers.add_parser("db-load", help="Load state from SQLite")
    db_load.add_argument("db_path")

    api = subparsers.add_parser("serve-api", help="Start built-in HTTP API server")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)
    api.add_argument("--token", default="")

    fastapi_cmd = subparsers.add_parser("serve-fastapi", help="Start FastAPI server")
    fastapi_cmd.add_argument("--host", default="127.0.0.1")
    fastapi_cmd.add_argument("--port", type=int, default=8000)
    fastapi_cmd.add_argument("--token", default="")

    fx = subparsers.add_parser("fx-rate", help="Scrape live exchange rate")
    fx.add_argument("from_currency")
    fx.add_argument("to_currency")

    return parser


def main() -> None:
    parser = build_cli()
    args = parser.parse_args()
    try:
        tracker = FinanceTracker.load(args.file)

        if args.command == "add":
            tx = tracker.add_transaction(args.amount, args.category, args.kind, args.description, args.date)
            tracker.save(args.file)
            print(f"Added {tx.kind}: ${tx.amount:.2f} [{tx.category}] on {tx.tx_date}")
        elif args.command == "budget":
            tracker.set_budget(args.category, args.amount)
            tracker.save(args.file)
            print(f"Set budget for '{args.category.lower()}' to ${args.amount:.2f}")
        elif args.command == "summary":
            print(json.dumps(tracker.summary(month=args.month), indent=2))
            print(json.dumps(tracker.budget_status(month=args.month), indent=2))
        elif args.command == "insights":
            for insight in tracker.smart_insights(month=args.month):
                print(f"- {insight}")
        elif args.command == "list":
            txs = tracker.list_transactions(month=args.month)
            if not txs:
                print("No transactions found.")
            for tx in txs:
                description = f" | {tx.description}" if tx.description else ""
                print(f"{tx.tx_date} | {tx.kind:7} | ${tx.amount:8.2f} | {tx.category}{description}")
        elif args.command == "report":
            print(json.dumps(tracker.monthly_report(), indent=2))
        elif args.command == "chart":
            print(tracker.spending_bar_chart(month=args.month))
        elif args.command == "recur-add":
            rule = tracker.add_recurring_rule(args.amount, args.category, args.kind, args.day, args.description, args.start_date, args.end_date)
            tracker.save(args.file)
            print(f"Recurring rule added: {rule.kind} ${rule.amount:.2f} {rule.category} on day {rule.day_of_month}")
        elif args.command == "recur-apply":
            count = tracker.apply_recurring_for_month(args.month)
            tracker.save(args.file)
            print(f"Generated {count} recurring transactions for {args.month}.")
        elif args.command == "export-csv":
            print(f"Exported {tracker.export_csv(args.path, month=args.month)} transactions to {args.path}.")
        elif args.command == "import-csv":
            count = tracker.import_csv(args.path)
            tracker.save(args.file)
            print(f"Imported {count} transactions from {args.path}.")
        elif args.command == "db-init":
            DatabaseManager(args.db_path).initialize()
            print(f"Initialized DB at {args.db_path}")
        elif args.command == "db-save":
            DatabaseManager(args.db_path).save_tracker(tracker)
            print(f"Saved tracker state to DB at {args.db_path}")
        elif args.command == "db-load":
            loaded = DatabaseManager(args.db_path).load_tracker()
            loaded.save(args.file)
            print(f"Loaded DB at {args.db_path} into {args.file}")
        elif args.command == "serve-api":
            server = start_api_server(tracker, host=args.host, port=args.port, token=args.token)
            print(f"Serving API on http://{args.host}:{args.port}")
            print("Endpoints: /health, /summary, /transactions")
            print("Press Ctrl+C to stop")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == "serve-fastapi":
            try:
                import uvicorn
            except ImportError as exc:
                raise ValueError("Uvicorn is not installed. Install with: pip install uvicorn") from exc
            app = create_fastapi_app(tracker, token=args.token)
            print(f"Serving FastAPI on http://{args.host}:{args.port}")
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.command == "fx-rate":
            rate = scrape_exchange_rate(args.from_currency, args.to_currency)
            print(f"1 {args.from_currency.upper()} = {rate:.6f} {args.to_currency.upper()}")

    except ValueError as exc:
        raise SystemExit(f"Error: {exc}") from exc
