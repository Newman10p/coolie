"""Policy guardrails for customer and supplier messaging."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommunicationPolicy:
    customer_messages_per_hour: int = 50
    supplier_messages_per_mission: int = 20
    bulk_email_batch_max: int = 100
    social_posts_per_day: int = 5
    outbound_requires_template: bool = True
    restricted_intents: frozenset[str] = frozenset({"returns_request", "payment_dispute", "legal_message"})

    @classmethod
    def from_config(cls, config) -> "CommunicationPolicy":
        comm = getattr(config, "communication", None)
        if comm is None:
            return cls()
        return cls(
            customer_messages_per_hour=getattr(comm, "customer_messages_per_hour", 50),
            supplier_messages_per_mission=getattr(comm, "supplier_messages_per_mission", 20),
            bulk_email_batch_max=getattr(comm, "bulk_email_batch_max", 100),
            social_posts_per_day=getattr(comm, "social_posts_per_day", 5),
            outbound_requires_template=getattr(comm, "outbound_requires_template", True),
            restricted_intents=getattr(comm, "restricted_intents", cls.restricted_intents),
        )

    def validate_outbound(self, *, intent: str | None = None, body: str | None = None, recipient: str | None = None) -> None:
        if intent is not None and str(intent) in self.restricted_intents:
            raise PermissionError(f"Restricted outbound intent {intent} requires escalation.")
        if self.outbound_requires_template and (body is not None and "{{" in body and recipient is None):
            raise ValueError("Outbound message requires a template or recipient for template-bound sends.")

    def validate_inbound(self, *, intent: str | None = None, sender: str | None = None) -> None:
        if intent is not None and str(intent) in self.restricted_intents:
            raise PermissionError(f"Inbounds with intent {intent} cannot be auto-replied.")
        if sender is not None and not sender.strip():
            raise ValueError("Sender must be non-empty.")


__all__ = ["CommunicationPolicy"]
