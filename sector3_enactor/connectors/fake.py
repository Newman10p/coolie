"""Fake connector wiring for deterministic tests (§14: no real services)."""
from __future__ import annotations

from typing import Any

from .base import FakeConnector
from ..tools.gateway import ConnectorAccount


def build_fake_connectors() -> dict[str, FakeConnector]:
    return {name: FakeConnector(name=name) for name in (
        "brain", "orchestrator", "research_room", "email", "messaging", "store", "inventory",
        "supplier", "repository", "hosting", "design", "social", "advertising", "analytics", "seo")}


def triage_response(body: str) -> dict[str, Any]:
    lowered = body.lower()
    if "refund" in lowered or "money back" in lowered: intent = "returns_request"
    elif "charge" in lowered or "dispute" in lowered or "unauthorized payment" in lowered: intent = "payment_dispute"
    elif "lawyer" in lowered or "legal" in lowered: intent = "legal_message"
    elif "where is my order" in lowered or "order status" in lowered or "tracking" in lowered: intent = "order_status"
    elif "wholesale" in lowered: intent = "wholesale_inquiry"
    elif "broken" in lowered or "not working" in lowered: intent = "technical_issue"
    else: intent = "customer_feedback"
    reply_type = {"returns_request": "escalate", "payment_dispute": "escalate", "legal_message": "escalate",
                  "order_status": "informational", "wholesale_inquiry": "draft_reply",
                  "technical_issue": "draft_reply"}.get(intent, "informational")
    return {"status": "success", "intent": intent, "replyType": reply_type}


TOOL_CONNECTOR = {
    "email": "email", "messaging": "messaging", "supplier": "supplier", "tickets": "store",
    "triage": "brain", "internal": "orchestrator", "design": "design", "assets": "repository",
    "repo": "repository", "sandbox": "repository", "ci": "repository", "hosting": "hosting",
    "code": "repository", "campaigns": "advertising", "social": "social", "ads": "advertising",
    "claims": "brain", "seo": "seo", "analytics": "analytics", "research": "research_room",
    "catalog": "store", "store": "store", "inventory": "inventory", "fulfillment": "store",
    "returns": "store", "qa": "brain", "brain": "brain",
}


def wire_gateway(gateway, registry_names: tuple[str, ...], connectors: dict[str, FakeConnector]) -> None:
    """One fake platform account serves every registered tool; per-tool routing
    sends calls to the matching named connector so call logs stay meaningful."""
    def handler(tool: str, arguments: dict) -> dict:
        if tool == "triage.classify_request":
            return triage_response(str(arguments.get("body", "")))
        if tool == "brain.complete":
            return {"status": "success", "text": f"fake-brain: {str(arguments.get('prompt',''))[:80]}"}
        if tool == "catalog.validate_listing":
            return {"status": "success", "valid": True}
        if tool == "campaigns.validate_policy" or tool == "claims.check_marketing_claims":
            return {"status": "success", "violations": list(arguments.get("violations", ()))}
        connector = connectors[TOOL_CONNECTOR.get(tool.split(".", 1)[0], "orchestrator")]
        return connector.handle(tool, arguments)
    account = ConnectorAccount(name="fake-platform", allowed_tools=frozenset(registry_names),
                               scopes=frozenset({"all"}))
    gateway.register_connector(account, tuple(registry_names), handler)
