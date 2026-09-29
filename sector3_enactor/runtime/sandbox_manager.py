"""Simple sandbox policy for internal code execution and staging work."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SandboxManager:
    work_root: Path = field(default_factory=lambda: Path("/tmp/coolie-sandbox"))
    allowed_commands: frozenset[str] = frozenset({"pytest", "python -m unittest", "git status", "git diff"})
    deny_network: bool = True

    def create_workspace(self, name: str) -> Path:
        root = self.work_root / name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def assert_safe_command(self, command: str) -> None:
        normalized = command.strip()
        if not normalized:
            raise ValueError("Empty sandbox command is not allowed.")
        if any(token in normalized for token in ("rm -rf /", "curl http://", "wget http://", "ssh ", "scp ", "sudo ", "--network")):
            raise PermissionError("Command exceeds sandbox policy.")
        if normalized.split()[0] not in self.allowed_commands and normalized not in self.allowed_commands:
            raise PermissionError(f"Command {normalized!r} is not permitted in the sandbox.")

    def assert_safe_dependency(self, package: str) -> None:
        if package.startswith(".") or package.startswith("/"):
            raise PermissionError("Local filesystem packages are not allowed in the sandbox.")


__all__ = ["SandboxManager"]
