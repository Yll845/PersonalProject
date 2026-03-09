from __future__ import annotations

import json
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List

from .core import FinanceTracker


def is_authorized_bearer(auth_header: str, token: str) -> bool:
    if not token:
        return True
    return auth_header == f"Bearer {token}"


class FinanceAPIHandler(BaseHTTPRequestHandler):
    tracker = FinanceTracker()
    api_token = ""

    def _authorized(self) -> bool:
        return is_authorized_bearer(self.headers.get("Authorization", ""), self.api_token)

    def _write_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            self._write_json({"error": "unauthorized"}, status=401)
            return
        if self.path == "/health":
            self._write_json({"ok": True})
        elif self.path == "/summary":
            self._write_json(self.tracker.summary())
        elif self.path == "/transactions":
            self._write_json({"transactions": [asdict(t) for t in self.tracker.list_transactions()]})
        else:
            self._write_json({"error": "not found"}, status=404)


def start_api_server(tracker: FinanceTracker, host: str, port: int, token: str = "") -> HTTPServer:
    FinanceAPIHandler.tracker = tracker
    FinanceAPIHandler.api_token = token
    server = HTTPServer((host, port), FinanceAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def create_fastapi_app(tracker: FinanceTracker, token: str = "") -> Any:
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException
    except ImportError as exc:
        raise ValueError("FastAPI is not installed. Install with: pip install fastapi uvicorn") from exc

    app = FastAPI(title="Smart Personal Finance Tracker API")

    def require_auth(authorization: str = Header(default="")) -> None:
        if not is_authorized_bearer(authorization, token):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health(_: None = Depends(require_auth)) -> Dict[str, bool]:
        return {"ok": True}

    @app.get("/summary")
    def summary(_: None = Depends(require_auth)) -> Dict[str, float]:
        return tracker.summary()

    @app.get("/transactions")
    def transactions(_: None = Depends(require_auth)) -> Dict[str, List[Dict[str, Any]]]:
        return {"transactions": [asdict(t) for t in tracker.list_transactions()]}

    return app
