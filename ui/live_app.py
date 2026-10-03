"""Compose the authenticated Coolie API with the built owner-workroom UI."""

from __future__ import annotations

from typing import Callable

from ui.demo_server import PreviewApp


class LiveCoolieApplication:
    """Route authenticated API requests and static UI through one same-origin app."""

    def __init__(self, owner_api: Callable, static_app: Callable | None = None) -> None:
        self.owner_api = owner_api
        self.static_app = static_app or PreviewApp()

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        if str(environ.get("PATH_INFO", "")).startswith("/api/"):
            return self.owner_api(environ, start_response)
        return self.static_app(environ, start_response)
