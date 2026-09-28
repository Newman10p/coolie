"""Connector boundary — document §8.2: only the gateway talks to connectors;
agents never hold credentials."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeConnector:
    """Deterministic in-memory connector with call log + idempotency dedupe."""
    name: str
    calls: list = field(default_factory=list)
    _responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    _seen_keys: set = field(default_factory=set)

    def stub(self, tool: str, response: dict[str, Any]) -> None:
        self._responses[tool] = dict(response)

    def handle(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        key = arguments.get("__idempotencyKey__")
        if key:
            composite = f"{tool}:{key}"
            if composite in self._seen_keys:
                for call in self.calls:
                    if call["tool"] == tool and call["arguments"].get("__idempotencyKey__") == key:
                        return {**call["response"], "deduplicated": True}
            self._seen_keys.add(composite)
        if arguments.get("__dryRun__"):
            response = {"status": "success", "dryRun": True, "preview": f"would-execute:{tool}",
                        "externalOperationId": None}
        else:
            base = self._responses.get(tool)
            if base is not None:
                response = dict(base)
            else:
                response = {"status": "success", "connector": self.name, "tool": tool,
                            "externalOperationId": f"OP-{self.name}-{len(self.calls) + 1:04d}"}
        self.calls.append({"tool": tool, "arguments": {k: v for k, v in arguments.items() if not k.startswith("__")},
                           "response": dict(response)})
        return response
