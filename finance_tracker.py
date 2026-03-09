from tracker import (
    DatabaseManager,
    FinanceAPIHandler,
    FinanceTracker,
    RecurringRule,
    Transaction,
    create_fastapi_app,
    is_authorized_bearer,
    scrape_exchange_rate,
    start_api_server,
)
from tracker.cli import build_cli, main

__all__ = [
    "Transaction",
    "RecurringRule",
    "FinanceTracker",
    "DatabaseManager",
    "FinanceAPIHandler",
    "start_api_server",
    "create_fastapi_app",
    "is_authorized_bearer",
    "scrape_exchange_rate",
    "build_cli",
    "main",
]

if __name__ == "__main__":
    main()
