"""Message models — document §5.1 (Messenger division)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .shared import now_utc, _non_empty


class MessageDirection(str, Enum):
    INBOUND = "inbound"; OUTBOUND = "outbound"


class MessageChannel(str, Enum):
    EMAIL = "email"; WHATSAPP = "whatsapp"; INSTAGRAM_DM = "instagram_dm"; INTERNAL = "internal"


class MessageIntent(str, Enum):
    """The 11 documented triage intents (§5.1A)."""
    ORDER_STATUS = "order_status"; RETURNS_REQUEST = "returns_request"; COMPLAINT = "complaint"
    TECHNICAL_ISSUE = "technical_issue"; WHOLESALE_INQUIRY = "wholesale_inquiry"
    SUPPLY_FOLLOW_UP = "supply_follow_up"; PAYMENT_DISPUTE = "payment_dispute"
    LEGAL_MESSAGE = "legal_message"; SPAM = "spam"; CUSTOMER_FEEDBACK = "customer_feedback"
    PARTNER_PROPOSAL = "partner_proposal"


# Intents that may NEVER be answered autonomously — always escalate (§5.1B restricted list).
RESTRICTED_INTENTS = frozenset({
    MessageIntent.RETURNS_REQUEST, MessageIntent.PAYMENT_DISPUTE, MessageIntent.LEGAL_MESSAGE,
})


class ConversationParty(str, Enum):
    CUSTOMER = "customer"; SUPPLIER = "supplier"; INTERNAL = "internal"; PARTNER = "partner"


@dataclass(frozen=True)
class InboundMessage:
    message_id: str
    business_id: str
    channel: MessageChannel
    direction: MessageDirection
    party: ConversationParty
    sender_reference: str
    subject: str | None
    body: str
    received_at: datetime = field(default_factory=now_utc)
    external_context: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("message_id", "business_id", "sender_reference", "body"): _non_empty(getattr(self, name), name)
        if not isinstance(self.channel, MessageChannel): raise ValueError("channel must be a MessageChannel.")
        if self.direction is not MessageDirection.INBOUND: raise ValueError("InboundMessage requires direction=inbound.")
        if self.received_at.tzinfo is None: raise ValueError("received_at must be timezone-aware.")


@dataclass(frozen=True)
class OutboundDraft:
    draft_id: str
    business_id: str
    execution_id: str
    channel: MessageChannel
    recipient: str
    party: ConversationParty
    subject: str | None
    body: str
    intent: MessageIntent
    linked_inbound_message_id: str | None = None
    created_by_agent: str = ""

    def __post_init__(self) -> None:
        for name in ("draft_id", "business_id", "execution_id", "recipient", "body", "created_by_agent"):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.intent, MessageIntent): raise ValueError("intent must be a MessageIntent.")
        if self.channel is MessageChannel.INTERNAL and self.party is not ConversationParty.INTERNAL:
            raise ValueError("Internal drafts must target internal parties.")


@dataclass(frozen=True)
class SupportTicket:
    ticket_id: str
    business_id: str
    message_id: str
    intent: MessageIntent
    severity: str  # low | medium | high | critical
    status: str = "open"
    escalation_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("ticket_id", "business_id", "message_id"): _non_empty(getattr(self, name), name)
        if self.severity not in {"low", "medium", "high", "critical"}: raise ValueError("Ticket severity is invalid.")
