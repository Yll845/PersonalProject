# Smart Personal Finance Tracker (Python)

A reconstructed, modular personal finance tracker with CLI + API support.

## Architecture (Reconstructed)
- `tracker/models.py` → dataclasses and validation (`Transaction`, `RecurringRule`)
- `tracker/core.py` → business logic (transactions, budgets, insights, CSV, JSON, scraping)
- `tracker/db.py` → SQLite persistence (`DatabaseManager`)
- `tracker/api.py` → built-in HTTP API + optional FastAPI app factory
- `tracker/cli.py` → command routing and user interaction
- `finance_tracker.py` → thin compatibility facade + executable entrypoint

## Features
- Income/expense tracking, monthly summaries, insights, and reports
- Category budgeting and budget status checks
- Recurring rule generation (idempotent)
- CSV import/export
- JSON + SQLite persistence
- Built-in HTTP API and optional FastAPI mode with bearer token auth

## Quick Start
```bash
python finance_tracker.py --file my_finance.json add income 5000 salary --description "Monthly salary"
python finance_tracker.py --file my_finance.json add expense 1200 rent --date 2026-01-03
python finance_tracker.py --file my_finance.json summary --month 2026-01
python finance_tracker.py --file my_finance.json insights --month 2026-01
python finance_tracker.py --file my_finance.json chart --month 2026-01
```

## API
```bash
# Built-in HTTP API
python finance_tracker.py --file my_finance.json serve-api --host 127.0.0.1 --port 8000 --token my-secret

# Optional FastAPI mode
python finance_tracker.py --file my_finance.json serve-fastapi --host 127.0.0.1 --port 8000 --token my-secret
```

If using FastAPI mode:
```bash
pip install fastapi uvicorn
```

## Tests
```bash
python -m pytest -q
```


## Web UI (HTML/CSS)
A standalone polished web interface is available in `web/` and works fully in-browser with LocalStorage.

```bash
python -m http.server 4173
# then open http://localhost:4173/web/
```
