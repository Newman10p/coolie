"""Serve the built React workroom without pretending to provide live data."""

from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
import sys
from typing import Callable
from wsgiref.simple_server import make_server


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _DIST_DIRECTORY = Path(getattr(sys, "_MEIPASS")) / "dist"
else:
    _DIST_DIRECTORY = Path(__file__).resolve().parent.parent / "dist"


class PreviewApp:
    """Static frontend preview; real API access requires the authenticated adapter."""

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))
        if method not in {"GET", "HEAD"}:
            return self._json_response(start_response, "405 Method Not Allowed", {"error": "method not allowed"})
        if path.startswith("/api/"):
            return self._json_response(start_response, "503 Service Unavailable", {
                "dataMode": "preview",
                "error": "The static preview does not connect to Coolie services. Configure ui.owner_api.OwnerWorkspaceApi for authenticated backend access.",
            })

        relative_path = "index.html" if path in {"", "/"} else path.lstrip("/")
        asset_path = (_DIST_DIRECTORY / relative_path).resolve()
        try:
            asset_path.relative_to(_DIST_DIRECTORY.resolve())
        except ValueError:
            return self._response(start_response, "404 Not Found", b"not found\n", "text/plain; charset=utf-8")
        if not asset_path.is_file():
            if relative_path != "index.html":
                return self._response(start_response, "404 Not Found", b"not found\n", "text/plain; charset=utf-8")
            return self._response(
                start_response,
                "503 Service Unavailable",
                b"Built UI is unavailable. Run `npm run build` first.\n",
                "text/plain; charset=utf-8",
            )
        content = asset_path.read_bytes()
        content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript"}:
            content_type += "; charset=utf-8"
        if method == "HEAD":
            content = b""
        return self._response(start_response, "200 OK", content, content_type)

    @staticmethod
    def _json_response(start_response: Callable, status: str, payload: dict[str, object]) -> list[bytes]:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return PreviewApp._response(start_response, status, body, "application/json; charset=utf-8")

    @staticmethod
    def _response(start_response: Callable, status: str, body: bytes, content_type: str) -> list[bytes]:
        start_response(status, [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [body]


application = PreviewApp()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Coolie React workroom preview.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: localhost only)")
    parser.add_argument("--port", type=int, default=4173, help="Port (default: 4173)")
    args = parser.parse_args()
    with make_server(args.host, args.port, application) as server:
        print(f"Coolie workroom preview: http://{args.host}:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
