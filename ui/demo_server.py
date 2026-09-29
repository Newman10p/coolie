"""Local-only HTTP server for the owner-workroom UI and sample read models."""

from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
from typing import Callable
from wsgiref.simple_server import make_server


_UI_DIRECTORY = Path(__file__).resolve().parent
_SAMPLE = "sample"
_BRIEFING: dict[str, object] = {
    "dataMode": _SAMPLE,
    "source": "Local fabricated preview",
    "freshness": "Sample data · generated for preview",
    "reportingPeriod": "Sample period · 28 Sep",
    "greeting": {"name": "Amina", "text": "A steady start to the day."},
    "companyPulse": [
        {"label": "Recorded revenue", "value": 426, "detail": "Sample amount", "tone": "neutral", "basis": "SAMPLE"},
        {"label": "Active businesses", "value": 3, "detail": "Sample count", "tone": "neutral", "basis": "SAMPLE"},
        {"label": "Available wallet", "value": 8240, "detail": "Sample amount", "tone": "neutral", "basis": "SAMPLE"},
        {"label": "Realized profit", "value": 184, "detail": "Sample amount", "tone": "neutral", "basis": "SAMPLE"},
    ],
    "criticalAlerts": [{
        "title": "Preview decision",
        "detail": "This fabricated example demonstrates how a review item is displayed. It is not a real request.",
        "target": "decisions",
        "action": "Inspect sample",
    }],
    "activeBusinesses": [
        {"name": "Nuru Goods", "category": "Sample commerce business", "revenue": 268, "detail": "Sample amount", "status": "Sample active", "tone": "warning", "mark": "N"},
        {"name": "Kawa Studio", "category": "Sample digital business", "revenue": 112, "detail": "Sample amount", "status": "Sample testing", "tone": "warning", "mark": "K"},
        {"name": "Safi Home", "category": "Sample home business", "revenue": 46, "detail": "Sample amount", "status": "Sample research", "tone": "warning", "mark": "S"},
    ],
    "pendingDecisions": [{
        "title": "Sample growth test",
        "detail": "Fabricated request · no action is pending",
        "target": "Sample business",
        "budget": "Sample amount · $350",
        "risk": "Sample risk",
        "complianceStatus": "Not evaluated",
        "time": "Sample expiry",
        "evidenceRefs": ["SAMPLE-ONLY"],
    }],
    "sectorHealth": [],
    "recentChanges": [],
}

_OFFICE: dict[str, object] = {
    "dataMode": _SAMPLE,
    "reconciliationStatus": "Sample only · no ledger connected",
    "moneyMatrix": [
        {"label": "Wallet available", "value": 8240, "kind": "SAMPLE"},
        {"label": "Reserved funds", "value": 1760, "kind": "SAMPLE"},
        {"label": "Committed funds", "value": 920, "kind": "SAMPLE"},
        {"label": "Recorded revenue", "value": 426, "kind": "SAMPLE"},
        {"label": "Recorded expenses", "value": 242, "kind": "SAMPLE"},
        {"label": "Realized P/L", "value": 184, "kind": "SAMPLE"},
        {"label": "Current exposure", "value": 2110, "kind": "SAMPLE"},
        {"label": "Forecast result", "value": 1240, "kind": "SAMPLE"},
    ],
    "portfolio": _BRIEFING["activeBusinesses"],
    "decisions": _BRIEFING["pendingDecisions"],
    "activeWork": [],
    "researchProgress": {"active": 0, "gaps": "Sample only"},
    "evolverProgress": {"proposals": 0, "releaseState": "Sample only"},
}

_REPORTS: dict[str, object] = {
    "dataMode": _SAMPLE,
    "reports": [
        {"name": "Sample weekly business pulse", "type": "Sample executive report", "period": "Sample period", "freshness": "Sample", "summary": "Fabricated preview record; no source report is connected."},
        {"name": "Sample market scan", "type": "Sample research report", "period": "Sample period", "freshness": "Sample", "summary": "Fabricated preview record; no evidence source is connected."},
    ],
}

_SAMPLE_HEALTH: dict[str, object] = {
    "dataMode": _SAMPLE,
    "ready": False,
    "status": "sample",
    "paused": False,
    "reason": "The local preview server does not connect to or measure Coolie services.",
    "services": [
        {"service": service, "status": "sample", "activeWorkCount": 0, "pendingAttentionCount": 0}
        for service in (
            "brain",
            "research_room",
            "sector3_enactor",
            "money_calculator",
            "evolver",
            "report_collector",
        )
    ],
}

_READ_MODELS: dict[str, dict[str, object]] = {
    "/api/ui/briefing": _BRIEFING,
    "/api/ui/office-table": _OFFICE,
    "/api/ui/reports": _REPORTS,
}
_STATIC_ASSETS = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
}


class DemoWorkroomApp:
    """Serve the static UI and read-only, conspicuously sample-marked fixtures."""

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))

        if method == "POST" and path in {
            "/api/orchestrator/transcribe",
            "/api/orchestrator/messages",
        }:
            return self._json_response(start_response, "503 Service Unavailable", {
                "dataMode": _SAMPLE,
                "error": "Orchestrator voice and message services are not connected in the local sample server.",
            })
        if method not in {"GET", "HEAD"}:
            return self._json_response(start_response, "405 Method Not Allowed", {"error": "method not allowed"})
        if path == "/api/health/ready":
            return self._json_response(start_response, "503 Service Unavailable", _SAMPLE_HEALTH)
        if path in _READ_MODELS:
            return self._json_response(start_response, "200 OK", _READ_MODELS[path])
        if path in {"/api/system/emergency-pause", "/api/system/resume"}:
            return self._json_response(start_response, "503 Service Unavailable", {
                "dataMode": _SAMPLE,
                "error": "Owner controls are disabled in the local sample server.",
            })
        if path.startswith("/api/"):
            return self._json_response(start_response, "404 Not Found", {"error": "not found"})
        if path not in _STATIC_ASSETS:
            return self._response(start_response, "404 Not Found", b"not found\n", "text/plain; charset=utf-8")

        asset_path = _UI_DIRECTORY / _STATIC_ASSETS[path]
        content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript"}:
            content_type += "; charset=utf-8"
        try:
            content = asset_path.read_bytes()
        except OSError:
            return self._response(start_response, "500 Internal Server Error", b"UI asset unavailable\n", "text/plain; charset=utf-8")
        if method == "HEAD":
            content = b""
        return self._response(start_response, "200 OK", content, content_type)

    @staticmethod
    def _json_response(start_response: Callable, status: str, payload: dict[str, object]) -> list[bytes]:
        content = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return DemoWorkroomApp._response(start_response, status, content, "application/json; charset=utf-8")

    @staticmethod
    def _response(start_response: Callable, status: str, content: bytes, content_type: str) -> list[bytes]:
        start_response(status, [
            ("Content-Type", content_type),
            ("Content-Length", str(len(content))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [content]


application = DemoWorkroomApp()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Coolie owner-workroom sample preview.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: localhost only)")
    parser.add_argument("--port", type=int, default=4173, help="Port (default: 4173)")
    args = parser.parse_args()
    with make_server(args.host, args.port, application) as server:
        print(f"Coolie sample workroom: http://{args.host}:{args.port}/")
        print("All API values are fabricated samples; owner controls are disabled.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping local sample workroom.")


if __name__ == "__main__":
    main()
